import sys
import codecs
import argparse
import yaml
import json

from icc import db, create_app
from icc.models import Text, Edition, Line, LineEnum, WriterEditionConnection,\
        ConnectionEnum, Writer

parser = argparse.ArgumentParser("Insert lines into icc database")
parser.add_argument(
    '-c', '--config', action='store', type=str, required=True,
    help="The location of the yaml configuration file for the text"
)
parser.add_argument('-i', '--initial', action='store_true',
        help="This is an initial text.")
parser.add_argument('-d', '--dryrun', action='store_true',
        help="Flag for a dry run test.")

args = parser.parse_args()
fin = codecs.getreader('utf_8_sig')(sys.stdin.buffer, errors='replace')
config = yaml.load(open(args.config, 'rt'))
lines = json.load(fin)

app = create_app()
ctx = app.app_context()
ctx.push()

# if this is the first version of the text, we have to create it and add all the
# authors. If it isn't, we don't.
if args.initial:
    text = Text(title=config['title'], sort_title=config['sort_title'],
            published=config['publication_date'],
            description=config['description'])
    for author in config['authors']:
        writer = Writer.query.filter(Writer.name==author['name']).first()
        if writer:
            text.authors.append(writer)
            print(f"Found {writer.name} in the database.")
        else:
            text.authors.append(
                    Writer(name=author['name'], last_name=author['last_name'],
                        birth_date=author['birthdate'],
                        death_date=author['deathdate'],
                        description=author['description'])
                    )
            print(f"Created author {text.authors[-1].name}.")
    db.session.add(text)
    print(f"Created text {text.title} by {text.authors}.")
else:
    text = Text.query.filter_by(title=config.title).first()
    print(f"Found {text.title} in the database.")

# if this isn't the initial text creation, we obviously have a previous
# primary. If this new edition _is_ a primary, then we have to deactivate
# that previous primary.
if not args.initial and config['edition']['primary']:
    print(f"Deactivated primary designation on edition #{text.primary.num} of"
            f"{text.title}.")
    text.primary.primary = False

# create the edition
edition = Edition(num=config['edition']['number'], text=text,
        primary=config['edition']['primary'],
        description=config['edition']['description'],
        published=config['edition']['publication_date'])
db.session.add(edition)
print(f"Created edition number {edition.num} for {text.title}.")

# For all the connection types we have, we go look in the edition dictionary for
# those connection types, and then loop through the writers in those ditionaries
# to create those connections. Simple, really. (I'm actually kind of proud of
# this one; I won't have to rewrite it as I add connections; which, are there
# any?)
conns = ConnectionEnum.query.all()
for enum in conns:
    for writer in config['edition'][enum.enum]:
        writer_obj = Writer.query.filter_by(name=writer['name']).first()
        if not writer_obj:
            writer_obj = Writer(
                    name=writer['name'], last_name=writer['last_name'],
                    birth_date=writer['birthdate'],
                    death_date=writer['deathdate'],
                    description=writer['description'])
            db.session.add(writer_obj)
            print(f"Writer {writer_obj.name} created.")

        conn = WriterEditionConnection(writer=writer_obj, edition=edition,
                enum=enum)
        db.session.add(conn)
        print(f"Writer {writer_obj.name} added as a {enum.enum}.")

labels = LineEnum.query.all()
label = {}
for l in labels:
    label[f'{l.enum}>{l.display}'] = l

i = 1
for line in lines:
    l = Line(edition=edition, num=line['num'],
            label=label[line['label']], em_status=label[line['em_status']],
            lvl1=line['l1'], lvl2=line['l2'], lvl3=line['l3'], lvl4=line['l4'],
            line=line['line'])
    db.session.add(l)

    if i % 1000 == 0:
        print(i)
    i+=1

print(f"After an arduous {i} lines, we are done.")
if  args.dryrun:
    db.session.rollback()
    print(f"Nothing committed.")
else:
    print(f"Now committing...")
    db.session.commit()
    print(f"Done.")
    print(f"Reindexing...")
    Line.reindex(edition=edition)
    print(f"Done.")

ctx.pop()
