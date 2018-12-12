#!/home/malan/projects/icc/icc/venv/bin/python
from app import db
from app.models import Text, Edition, Line, LineEnum, WriterEditionConnection,\
        ConnectionEnum, Writer
import sys
import codecs
import argparse

parser = argparse.ArgumentParser("Insert lines into icc database")
parser.add_argument("-t", "--text_id", action="store", type=int,
        help="The text id as it is in the database.")
parser.add_argument("-b", "--book_title", action="store", type=str,
        help="The title as it is exactly entered in the database. Either this "
        "or the text_id is required.")
parser.add_argument("-w", "--writers", action="store", type=str,
        help="A comma separated list of writers and their connection type"
        " involved in the production of the edition. For example, 'Constance C."
        " Garnett(Translator),Leo Tolstoy(Editor)'. Please be careful in typing"
        " this string. If the writer does not exist in the database, we will"
        " create it. If it is one letter of an actual writer in the database it"
        " will be created, which will cause all kinds of headaches. Check the"
        " database first. Please note: if the author is created, you will have"
        " to edit the writer to add details.")
parser.add_argument("-p", "--primary", action="store_true",
        help="Make this edition the primary")
parser.add_argument("-d", "--dryrun", action="store_true",
        help="Flag for a dry run test.")

args = parser.parse_args()
fin = codecs.getreader('utf_8_sig')(sys.stdin.buffer, errors='replace')

if not args.text_id or args.book_title:
    parser.error("Need either the text_id or the book title from the database.")

if args.text_id:
    text = Text.query.get(args.text_id)
    if not text:
        parser.error("Your text_id is not in the database.")
else:
    text = Text.query.filter_by(title=args.book_title).first()
    if not text:
        parser.error("Your title is not in the database as it is presently"
                " spelled.")

if args.primary:
    if text.primary:
        text.primary.primary = False

edition = Edition(text_id=text.id, primary=args.primary)
db.session.add(edition)
if args.writers:
    for w in args.writers.split(","):
        data = w.split("(")
        conn_type = data[1].strip(")")
        writer = data[0]
        enum = ConnectionEnum.query.filter_by(type=conn_type).first()
        if not enum:
            db.session.rollbac()
            parser.error(f"Your connection type for {writer}, {conn_type}, does"
                    " not exist in the database.")
        writer_query = Writer.query.filter_by(name=writer).first()
        if writer_query:
            writer = writer_query
            print(f"Writer {writer.name} found in the database.")
        else:
            writer = Writer(name=writer)
            db.session.add(writer)
            print(f"Writer {writer.name} created and added to the database.")
            print(f"Please edit {writer.name}'s information in the database.")
        conn = WriterEditionConnection(writer=writer, edition=edition, enum=enum)
        db.session.add(conn)


labels = LineEnum.query.all()
label = {}
for l in labels:
    label[f"{l.label}>{l.display}"] = l.id
i = 1
for line in fin:

    fields = line.split("@")

    l = Line(edition=edition, num=fields[0],
            label_id=label[fields[1]], em_id=label[fields[2]],
            lvl1=fields[3], lvl2=fields[4], lvl3=fields[5], lvl4=fields[6],
            line=fields[7][:-1])

    if not args.dryrun:
        db.session.add(l)

    if i % 100 == 0:
        print(i)
    i+=1

print(f"After an arduous {i} lines, we are done.")
if not args.dryrun:
    print(f"Now committing...")
    db.session.commit()
    print(f"Done.")
