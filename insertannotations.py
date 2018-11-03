from app import db
from app.models import Book, Line, User, Annotation, AnnotationVersion, Tag
import sys
import codecs

book_id = None
user = User.query.filter_by(displayname="Community").first()
if user == None:
    user = User(displayname="Community", email="community@annopedia.org",
            password_hash="***", locked=True,
            reputation=0, cumulative_negative=0, cumulative_positive=0,
            about_me=
            "Hi, "
            " "
            "I’m not a real person. I’m an account used to author annotations by "
            "non-members, such as the authors of the books hosted on Annopedia. "
            "An example would be the annotations provided by [Constance "
            "Garnett](https://en.wikipedia.org/wiki/War_and_Peace) in "
            "her translations of classic Russian literature like War and Peace.  "
            "The original author of the annotations will always be tagged with a "
            "special tag that will be locked to users. "
            " "
            "I hope you enjoy their annotations! "
            )
    db.session.add(user)
    db.session.commit()
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
        author_tag = Tag(tag=author,
            description=f"Original annotations from {author}.", admin=True)
        db.session.add(author_tag)
        db.session.commit()

fin = codecs.getreader('utf_8_sig')(sys.stdin.buffer, errors='replace')

tags = [original_tag, author_tag]

cnt = 0
for line in fin:
    fields = line.split("@")
    l = Line.query.filter_by(line=fields[1][:-1]).first()

    commit = AnnotationVersion(book_id=book_id, approved=True, editor=user,
            first_line_num=l.l_num, last_line_num=l.l_num,
            first_char_idx=0, last_char_idx=-1,
            annotation=fields[0], tags=tags, current=True)

    # Create the annotation pointer with HEAD pointing to anno
    head = Annotation(book_id=book_id, HEAD=commit, author=user, locked=True)

    # add commit and head, commit both
    db.session.add(commit)
    db.session.add(head)
    db.session.commit()

    # point the commit to head (This prevents the circular reference)
    commit.pointer = head
    db.session.commit()

    cnt += 1
    if cnt % 25 == 0:
        print(cnt)

print(f"{cnt} annotations added.")
