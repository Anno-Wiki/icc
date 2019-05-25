"""Parse enum yaml files into the database."""

import argparse
import yaml
import sys
import os

iccvenv = os.environ['ICCVENV']
idx = iccvenv.rfind('/')
sys.path.append(os.environ['ICCVENV'][:idx])

from icc import db, create_app
from icc import classes


parser = argparse.ArgumentParser("Parse yaml enum files into the database")
parser.add_argument(
    '-c', '--config', action='store', type=str, required=True,
    help="Path to the enum yaml file.")
args = parser.parse_args()

enums = yaml.load(open(args.config, 'rt'), Loader=yaml.FullLoader)

app = create_app()
ctx = app.app_context()
ctx.push()

for key, value in enums.items():
    for i, entry in enumerate(value):
        db.session.add(classes[key](**entry))
        i += 1
    print(f"Added {i} {key}s")

db.session.commit()
ctx.pop()
