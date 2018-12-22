#!/bin/sh
if 'true' : '''\'
then
exec '$VENV' '$0' '$@'
exit 127
fi
'''
from app import db
from app.models import Tag
import argparse, sys, yaml

parser = argparse.ArgumentParser("Insert tags into icc database")
parser.add_argument('-c', '--config', action='store', type=str, required=True,
        help="The location of the yaml configuration file for the tags")
parser.add_argument('-d', '--dryrun', action='store_true',
        help="Flag for a dry run test.")

args = parser.parse_args()
config = yaml.load(open(args.config, 'rt'))

i = 0
for tag in config['tags']:
    if not Tag.query.filter_by(tag=tag['tag']).first():
        db.session.add(
                Tag(tag=tag['tag'], locked=tag['locked'],
                    description=tag['description'])
                )
        i += 1

if not args.dryrun:
    db.session.commit()
    print(f"{i} tags added to the database.")
else:
    db.session.rollback()
    print(f"{i} tags created but rolled back.")
