from app.models import Book, Position
import sys

if '-b' not in sys.argv:
    sys.exit('Set book url with -b')

bpos = sys.argv.index('-b')

book = Book.query.filter_by(url = sys.argv[bpos+1]).first()
posses = Position.query.filter_by(book_id = book.id).all()

for pos in posses:
    print(f'<span id="{pos.id}">{pos.word.word}</span>')

