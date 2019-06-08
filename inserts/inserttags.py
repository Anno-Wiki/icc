import argparse
import yaml
import sys
import os

iccvenv = os.environ['ICCVENV']
idx = iccvenv.rfind('/')
sys.path.append(os.environ['ICCVENV'][:idx])

from icc import db, create_app
from icc.models.annotation import Tag

parser = argparse.ArgumentParser("Insert tags into icc database")
parser.add_argument('file', action='store', type=str,
                    help="The location of the yaml configuration file for the "
                    "tags")
parser.add_argument(
    '-d', '--dryrun', action='store_true',
    help="Flag for a dry run test.")

args = parser.parse_args()
config = yaml.load(open(args.file, 'rt'), Loader=yaml.FullLoader)
app = create_app()
ctx = app.app_context()
ctx.push()

i = 0
for tag in config['tags']:
    if not Tag.query.filter_by(tag=tag['tag']).first():
        db.session.add(Tag(tag=tag['tag'], locked=tag['locked'],
                           description=tag['description']))
        i += 1

if not args.dryrun:
    db.session.commit()
    print(f"{i} tags added to the database.")
else:
    db.session.rollback()
    print(f"{i} tags created but rolled back.")

ctx.pop()
