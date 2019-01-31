import sys
import codecs
import argparse
import yaml
import json

from icc import db, create_app
from icc.models.content import (Text, Edition, Line, LineEnum, LineAttribute,
                                WriterEditionConnection, ConnectionEnum, Writer,
                                EMPHASIS_REVERSE)
"""Populate the text, authors, edition, writer connections, and lines for a
text. Requires a `config.yml` file.
"""


def get_text(config):
    """Create the text, add the authors, and return the text object added the
    database.
    """
    if args.initial:
        text = Text(title=config['title'], sort_title=config['sort_title'],
                    published=config['publication_date'],
                    description=config['description'])
        for author in config['authors']:
            writer = Writer.query.filter(Writer.name == author['name']).first()
            if writer:
                text.authors.append(writer)
                print(f"Found {writer.name} in the database.")
            else:
                text.authors.append(
                        Writer(name=author['name'],
                               last_name=author['last_name'],
                               birth_date=author['birthdate'],
                               death_date=author['deathdate'],
                               description=author['description']))
                print(f"Created author {text.authors[-1].name}.")
        db.session.add(text)
        print(f"Created text {text.title} by {text.authors}.")
    else:
        text = Text.query.filter_by(title=config.title).first()
        print(f"Found {text.title} in the database.")
    return text


def deactivate_previous_primary(text):
    """If this isn't the initial text creation and we're changing the primary
    edition, call this method to deactivate the previous primary.
    """
    print(f"Deactivated primary designation on edition #{text.primary.num} of "
          f"{text.title}.")
    text.primary.primary = False


def get_edition(config, text):
    """Create the new edition, add it to the databsae, and return it."""
    edition = Edition(num=config['edition']['number'], text=text,
                      primary=config['edition']['primary'],
                      description=config['edition']['description'],
                      published=config['edition']['publication_date'])
    db.session.add(edition)
    print(f"Created edition number {edition.num} for {text.title}.")
    return edition


def add_writer_connections(config, edition):
    """Add all of the writer connections to the edition."""
    # For all the connection types we have, we go look in the edition dictionary
    # for those connection types, and then loop through the writers in those
    # dictionaries to create those connections.
    conns = ConnectionEnum.query.all()
    for enum in conns:
        for writer in config['edition'][enum.enum]:
            writer_obj = Writer.query.filter_by(name=writer['name']).first()
            if not writer_obj:
                writer_obj = Writer(name=writer['name'],
                                    last_name=writer['last_name'],
                                    birth_date=writer['birthdate'],
                                    death_date=writer['deathdate'],
                                    description=writer['description'])
                db.session.add(writer_obj)
                print(f"Writer {writer_obj.name} created.")

            conn = WriterEditionConnection(writer=writer_obj, edition=edition,
                                           enum=enum)
            db.session.add(conn)
            print(f"Writer {writer_obj.name} added as a {enum.enum}.")


def get_enums_dict():
    enums_list = LineEnum.query.all()
    enums_dict = {f'{e.enum}>{e.display}': e for e in enums_list}
    return enums_dict


def process_attributes(attrs_dict, enums_dict):
    """Process the attribute dictionary from the a line, creating LineEnums as
    we need them, and return both a list of attrs to be applied to the line and
    the updated enums dictionary with the newly created enums.
    """
    attrs = []
    for attr in attrs_dict:
        enum = enums_dict.get(f"{attr['enum']}>{attr['display']}")
        if not enum:
            enum = LineEnum(enum=attr['enum'], display=attr['display'])
            enums_dict[f'{enum.enum}>{enum.display}'] = enum
        a = LineAttribute(enum_obj=enum, num=attr['num'],
                          precedence=attr['precedence'],
                          primary=attr['primary'])
        attrs.append(a)
    return attrs, enums_dict


def populate_lines(lines, edition):
    """Populate the database with the lines and their attributes. Return the
    count of lines added to the database.
    """

    enums = get_enums_dict()
    i = 0
    for line in lines:
        attrs, enums = process_attributes(line['attributes'], enums)
        line_obj = Line(edition=edition, num=line['num'],
                        em_id=EMPHASIS_REVERSE[line['emphasis']],
                        line=line['line'], attrs=attrs)
        db.session.add(line_obj)

        if i % 1000 == 0:
            print(i)
        i+=1

    return i


if __name__ == '__main__':
    parser = argparse.ArgumentParser("Insert lines into icc database")
    parser.add_argument('-c', '--config', action='store', type=str,
                        required=True, help="A yaml configuration file "
                        "adhering to a specific template. See Text Processing "
                        "in the documentation for details.")
    parser.add_argument('-i', '--initial', action='store_true',
                        help="This is an initial text.")
    parser.add_argument('-d', '--dryrun', action='store_true',
                        help="Flag for a dry run test.")

    args = parser.parse_args()
    fin = codecs.getreader('utf_8_sig')(sys.stdin.buffer, errors='replace')
    config = yaml.load(open(args.config, 'rt'))
    lines = json.load(fin)

    app = create_app()

    with app.app_context():
        text = get_text(config)

        if not args.initial and config['edition']['primary']:
            deactivate_previous_primary(text)

        edition = get_edition(config, text)

        add_writer_connections(config, edition)

        i = populate_lines(lines, edition)

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
