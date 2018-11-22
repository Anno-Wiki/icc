#!/home/malan/projects/icc/icc/venv/bin/python
from app import db
from app.models import Book, Line, User, Annotation, AnnotationVersion, Tag
import sys
import codecs
import argparse

parser = argparse.ArgumentParser("Process icc .anno file into the database.")
parser.add_argument("-b", "--book", action="store", type=int, required=True,
        help="The book id")
parser.add_argument("-a", "--author", action="store", type=str, required=True,
        help="The name of the annotator in the form of a tag (i.e., no spaces)")
parser.add_argument("-d", "--dryrun", action="store_true",
        help="Flag for a dry run test.")

args = parser.parse_args()

user = User.query.filter_by(displayname="Community").first()
if user == None:
    user = User(displayname="Community", email="community@annopedia.org",
            password_hash="***", locked=True,
            reputation=0, cumulative_negative=0, cumulative_positive=0,
            about_me=
"""
Hi, 

I’m not a real person. I’m an account used to author annotations by non-members,
such as the authors of the books hosted on Annopedia.  An example would be the
annotations provided by [Constance Garnett](https://en.wikipedia.org/wiki/War_and_Peace)
in her translations of classic Russian literature like War and Peace.

The original author of the annotations will always be tagged with a special tag
that will be locked to users.

I hope you enjoy their annotations!

Sincerely,

The Annopedia Team
"""
            )

    if not args.dryrun:
        db.session.add(user)
        db.session.commit()

original_tag = Tag.query.filter_by(tag="original").first()
author_tag = Tag.query.filter_by(tag=args.author).first()

if author_tag == None:
    author_tag = Tag(tag=args.author,
        description=f"Original annotations from {args.author}.", admin=True)
    if not args.dryrun:
        db.session.add(author_tag)
        db.session.commit()

fin = codecs.getreader('utf_8_sig')(sys.stdin.buffer, errors='replace')

tags = [original_tag, author_tag]

cnt = 0
for line in fin:
    fields = line.split("@")
    l = Line.query.filter_by(line=fields[1][:-1]).first()

    if not l:
        db.session.rollback()
        sys.exit(f"Fail on {cnt}: {fields}")


    # Create the annotation pointer with HEAD pointing to anno
    head = Annotation(book_id=args.book, author=user, locked=True)

    commit = AnnotationVersion(
            pointer=head, approved=True, current=True, 
            book_id=args.book, editor=user,
            first_line_num=l.line_num, last_line_num=l.line_num,
            first_char_idx=0, last_char_idx=-1,
            annotation=fields[0], tags=tags,
            edit_num=0, edit_reason="Initial version")

    # add commit and head, commit both
    if not args.dryrun:
        db.session.add(head)
        db.session.add(commit)

    cnt += 1
    if cnt % 25 == 0:
        print(cnt)

if not args.dryrun:
    print(f"{cnt} annotations added.")
    print("Now committing...")
    db.session.commit()
    print("Done.")
else:
    print(f"{cnt} annotations created.")
