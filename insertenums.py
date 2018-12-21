#!/bin/sh
if "true" : '''\'
then
exec "$VENV" "$0" "$@"
exit 127
fi
'''
import yaml, argparse
from app import db
from app.models import classes

parser = argparse.ArgumentParser("Parse yaml enum files into the database")
parser.add_argument('-c', '--config', action='store', type=str, required=True,
        help="Path to the enum yaml file.")
args = parser.parse_args()

enums = yaml.load(open(args.config, 'rt'))

for key, value in enums.items():
    i = 0 
    for entry in value:
        db.session.add(classes[key](**entry))
        i += 1
    print(f"Added {i} {key}'s")

db.session.commit()
