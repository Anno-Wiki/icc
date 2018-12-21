#!/bin/sh
if "true" : '''\'
then
exec "$VENV" "$0" "$@"
exit 127
fi
'''
from app import db
from app.models import Line, User, Annotation, Edit, Tag, Edition, Text
import sys, codecs, argparse

parser = argparse.ArgumentParser("Process icc .ano file into the database.")
parser.add_argument("-t", "--title", action="store", type=str, required=True,
        help="The title of the text for the annotations")
parser.add_argument("-e", "--edition_num", action="store", type=int,
        required=True, help="The edition number of the text for the annotations.")
parser.add_argument("-a", "--annotator", action="store", type=str, required=True,
        help="The name of the annotator in the form of a tag (i.e., no spaces)")
parser.add_argument("-d", "--dryrun", action="store_true",
        help="Flag for a dry run test.")

args = parser.parse_args()

community = User.query.filter_by(email="community@annopedia.org").first()
if not community:
    sys.exit("The Community user hasn't been created in the database yet.")

original_tag = Tag.query.filter_by(tag="original").first()
annotator_tag = Tag.query.filter_by(tag=args.annotator).first()

if annotator_tag == None:
    annotator_tag = Tag(tag=args.annotator,
            description=f"Original annotations from [[Writer:{args.annotator}]]",
            locked=True)
    if not args.dryrun:
        db.session.add(annotator_tag)
        db.session.commit()

fin = codecs.getreader('utf_8_sig')(sys.stdin.buffer, errors='replace')

tags = [original_tag, annotator_tag]

text = Text.query.filter_by(title=args.title).first()
if not text:
    parser.error(f"The text {args.title} was not found.")
edition = text.editions.filter_by(num=args.edition_num).first()
if not edition:
    parser.error(f"The edition number {args.edition_num} was not found for"
            f"{text.title}")

cnt = 0
for line in fin:
    fields = line.split("@")
    l = Line.query.filter_by(line=fields[1][:-1]).first()

    if not l:
        db.session.rollback()
        sys.exit(f"Fail on {cnt}: {fields}")

    # Create the annotation pointer with HEAD pointing to anno
    head = Annotation(edition=edition, annotator=community, locked=True)

    commit = Edit(
            annotation=head, approved=True, current=True, editor=community,
            edition=edition, first_line_num=l.num, last_line_num=l.num,
            first_char_idx=0, last_char_idx=-1, body=fields[0], tags=tags,
            num=0, reason="Initial version"
            )

    head.HEAD = commit # this is strictly for elasticsearch indexing

    db.session.add(head)
    db.session.add(commit)

    cnt += 1
    if cnt % 25 == 0:
        print(cnt)

if not args.dryrun:
    print(f"{cnt} annotations added.")
    print("Now committing...")
    db.session.commit()
    print("Committed.")
    # I don't want to import SearchableMixin to test this, but I don't want to
    # eliminate the method in case I change my mind.
    if "SearchableMixin" in str(Annotation.__bases__):
        Annotation.reindex(edition_id=args.edition_id)
        print("Now reindexing...")
    print("Done.")
else:
    db.session.rollback()
    print(f"{cnt} annotations created.")
