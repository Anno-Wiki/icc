from app import db
from app.models import Book, Line, Kind
import sys
import codecs

fin = codecs.getreader('utf_8_sig')(sys.stdin.buffer, errors='replace')

kinds = Kind.query.all()
kind = {}
for k in kinds:
    kind[k.kind] = k.id


for line in fin:

    fields = line.split('@')

    l = Line(book_id=fields[0], l_num=fields[1], kind_id=kind[fields[2]],
            bk_num=fields[3], pt_num=fields[4], ch_num=fields[5],
            em_status_id=kind[fields[6]], line=fields[7])

    db.session.add(l)

db.session.commit()
