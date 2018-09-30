from app import db
from app.models import Book, Line, User, Annotation, AnnotationVersion, Tag
import sys
import codecs

book_id = None
user = User.query.filter_by(username="Community").first()
author_tag = None
original_tag = Tag.query.filter_by(tag="original").first()

if "-b" not in sys.argv:
    sys.exit("-b required")
else:
    book_id = int(sys.argv[sys.argv.index("-b")+1])
if "-a" not in sys.argv:
    sys.exit("-a required")
else:
    author = sys.argv[sys.argv.index("-a")+1]
    author_tag = Tag.query.filter_by(tag=author).first()
    if author_tag == None:
        author_tag = Tag(tag=author, description=f"Original annotations from {author}.")
        db.session.add(author_tag)
        db.session.commit()

fin = codecs.getreader('utf_8_sig')(sys.stdin.buffer, errors='replace')

for line in fin:
    fields = line.split("@")
    l = Line.query.filter_by(line=fields[1]).first()

    commit = AnnotationVersion(book=book, approved=True,
            editor=user,
            first_line_num=l.l_num,
            last_line_num=l.l_num,
            first_char_idx=0,
            last_char_idx=-1,
            annotation=fields[0],
            tag_1=original_tag, tag_2=author_tag)

    # Create the annotation pointer with HEAD pointing to anno
    head = Annotation(book=book, HEAD=commit, author=user)

    # add anno, commit it
    db.session.add(commit)
    db.session.commit()

    # make anno's pointer point to the 
    commit.pointer = head
    db.session.commit()
