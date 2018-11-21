from app import db
from app.models import Book, Line, Kind
import sys
import codecs
import argparse

parser = argparse.ArgumentParser("Insert lines into icc database")
parser.add_argument("-b", "--book", action="store", type=int, required=True)

args = parser.parse_args()

fin = codecs.getreader('utf_8_sig')(sys.stdin.buffer, errors='replace')

kinds = Kind.query.all()
kind = {}
for k in kinds:
    kind[k.kind] = k.id

i = 1
for line in fin:

    fields = line.split('@')

    l = Line(book_id=args.book, line_num=fields[0],
            kind_id=kind[fields[1]], em_status_id=kind[fields[2]],
            lvl_1=fields[3], lvl_2=fields[4], lvl_3=fields[5], lvl_4=fields[6],
            line=fields[7][:-1])

    db.session.add(l)

    if i % 100 == 0:
        print(i)
    i+=1

print(f"After an arduous {i} lines, we are done.")
print(f"Now committing...")
db.session.commit()
print(f"And now committed.")
