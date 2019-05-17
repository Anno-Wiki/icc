import sys
import argparse
import json
import os

iccvenv = os.environ['ICCVENV']
idx = iccvenv.rfind('/')
sys.path.append(os.environ['ICCVENV'][:idx])

from icc import db, create_app
from icc.models.annotation import Annotation, Tag
from icc.models.content import Edition
from icc.models.user import User


TAG_DESCRIPTION = "This tag's description is still blank. Please expand it."

def get_annotations():
    annotations = []
    for annotation in Annotation.query.all():
        exp = {
            'edition': annotation.edition.id,
            'fl': annotation.HEAD.first_line_num,
            'll': annotation.HEAD.last_line_num,
            'fc': annotation.HEAD.first_char_idx,
            'lc': annotation.HEAD.last_char_idx,
            'body': annotation.HEAD.body,
            'tags': [(tag.tag, tag.locked) for tag in annotation.HEAD.tags],
            'locked': annotation.locked
        }
        annotations.append(exp)
    return annotations


def export(file_name):
    annotations = get_annotations()
    fout = open(file_name, 'wt')
    json.dump(annotations, fout)


def recreate(annotation):
    annotation['edition'] = Edition.query.get(annotation['edition'])
    tags = []
    for tag in annotation['tags']:
        tag_obj = Tag.query.filter_by(tag=tag[0]).first()
        if not tag:
            tag = Tag(tag=tag_str, locked=tag[1], description=TAG_DESCRIPTION)
        tags.append(tag)
    annotation['tags'] = tags
    return annotation


def _import(file_name):
    fin = open(file_name, 'rt')
    annotations = json.load(fin)
    community = User.query.get(1)
    for i, annotation in enumerate(annotations):
        db.session.add(Annotation(annotator=community, **recreate(annotation)))
        if not i % 25:
            print(f"{i} annotations added.")
    db.session.commit()


def main(args):
    app = create_app()
    with app.app_context():
        if args.output:
            export(args.output)
        elif args.input:
            _import(args.input)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        "Export or import files from and to the icc database.")
    parser.add_argument('-i', '--input', action='store', type=str,
                        help="The input json file to populate the database with "
                        "pre-formatted annotations.")
    parser.add_argument('-o', '--output', action='store', type=str,
                        help="The output file to write the jsonified "
                        "annotations")
    args = parser.parse_args()
    main(args)
