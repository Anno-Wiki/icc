import argparse
import yaml

from icc import db, create_app
from icc.models.models import User, Right

parser = argparse.ArgumentParser("Insert users into icc database for testing.")
parser.add_argument(
    '-c', '--config', action='store', type=str, required=True,
    help="The location of the yaml configuration file for the tags")
parser.add_argument(
    '-p', '--password', action='store', type=str, required=True,
    help="The default password for all the users.")
parser.add_argument(
    '-d', '--dryrun', action='store_true', help="Flag for a dry run test.")

args = parser.parse_args()
config = yaml.load(open(args.config, 'rt'))
app = create_app()
ctx = app.app_context()
ctx.push()

rights = Right.query.all()
i = 0
for user in config['users']:
    u = User(displayname=user['displayname'], email=user['email'],
             locked=user['locked'], about_me=user['about_me'])
    if user['rights'] == 'all':
        u.rights = rights

    if not user['locked']:
        u.set_password(args.password)
    else:
        u.password_hash = '***'

    db.session.add(u)
    i += 1

if args.dryrun:
    db.session.rollback()
    print(f"{i} user(s) created.")
else:
    db.session.commit()
    print(f"{i} user(s) added to the database.")

ctx.pop()
