#!/home/malan/projects/icc/icc/venv/bin/python
from app import db
from app.models import Line, User, Annotation, Edit, Tag, Edition
import sys
import codecs
import argparse

parser = argparse.ArgumentParser("Process icc .anno file into the database.")
parser.add_argument("-e", "--edition_id", action="store", type=int, required=True,
        help="The edition id.")
parser.add_argument("-a", "--author", action="store", type=str, required=True,
        help="The name of the annotator in the form of a tag (i.e., no spaces)")
parser.add_argument("-d", "--dryrun", action="store_true",
        help="Flag for a dry run test.")

args = parser.parse_args()

user = User.query.filter_by(displayname="Community").first()
if user == None:
    user = User(displayname="Community", email="community@annopedia.org",
            password_hash="***", locked=True, about_me=
"""
Hi, 

I’m not a real person. I’m an account used to author annotations by non-members,
such as the authors of the books hosted on Annopedia.  An example would be the
annotations provided by [[Writer:Constance Garnett]] in her translations of
classic Russian literature like [[Text:War and Peace]].

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
            description=f"Original annotations from [[Writer:{args.author}]]",
            locked=True)
    if not args.dryrun:
        db.session.add(author_tag)
        db.session.commit()

fin = codecs.getreader('utf_8_sig')(sys.stdin.buffer, errors='replace')

tags = [original_tag, author_tag]

edition = Edition.query.get(args.edition_id)
if not edition:
    parser.error("edition_id not in database.")

cnt = 0
for line in fin:
    fields = line.split("@")
    l = Line.query.filter_by(line=fields[1][:-1]).first()

    if not l:
        db.session.rollback()
        sys.exit(f"Fail on {cnt}: {fields}")


    # Create the annotation pointer with HEAD pointing to anno
    head = Annotation(edition=edition, annotator=user, locked=True)

    commit = Edit(
            annotation=head, approved=True, current=True, editor=user,
            edition=edition, first_line_num=l.num, last_line_num=l.num,
            first_char_idx=0, last_char_idx=-1,
            body=fields[0], tags=tags,
            num=0, edit_reason="Initial version")

    head.HEAD = commit

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
    print("Committed, now reindexing.")
    Annotation.reindex(edition_id=args.edition_id)
    print("Done.")
else:
    print(f"{cnt} annotations created.")
