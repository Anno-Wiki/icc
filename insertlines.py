#!/home/malan/projects/icc/icc/venv/bin/python
from app import db
from app.models import Book, Line, LineLabel
import sys
import codecs
import argparse

parser = argparse.ArgumentParser("Insert lines into icc database")
parser.add_argument("-b", "--book", action="store", type=int, required=True)
parser.add_argument("-d", "--dryrun", action="store_true",
        help="Flag for a dry run test.")

args = parser.parse_args()

fin = codecs.getreader('utf_8_sig')(sys.stdin.buffer, errors='replace')

labels = LineLabel.query.all()
label = {}
for l in labels:
    label[f"{l.label}>{l.display}"] = l.id

i = 1
for line in fin:

    fields = line.split("@")

    l = Line(book_id=args.book, line_num=fields[0],
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
