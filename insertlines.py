from app import db
from app.models import Book, Line, Kind
import sys
import codecs

fin = codecs.getreader('utf_8_sig')(sys.stdin.buffer, errors='replace')

for line in fin:
    fields = line.split('@')

    k = Kind.query.filter_by(kind = fields[2]).first()
    e = Kind.query.filter_by(kind = fields[6]).first()

    l = Line(book_id = fields[0], l_num = fields[1], kind_id = k.id, 
        bk_num = fields[3], pt_num = fields[4], ch_num = fields[5],
        em_status_id = e.id, line = fields[7])

    db.session.add(l)

db.session.commit()
