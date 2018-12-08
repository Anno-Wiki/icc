#!/home/malan/projects/icc/icc/venv/bin/python
from app import db
from app.models import User, Right
import argparse

parser = argparse.ArgumentParser("Process icc .anno file into the database.")
parser.add_argument("-d", "--dryrun", action="store_true",
        help="Flag for a dry run test.")
parser.add_argument("-m", "--malanonly", action="store_true",
        help="Flag for a dry run test.")
parser.add_argument("-p", "--password", action="store", type=str, required=True,
        help="Set the password for all the users.")

args = parser.parse_args()
rights = Right.query.all()
malan = User.query.filter_by(displayname="malan").first()
if not malan:
    malan = User(displayname="malan", email="malan@glendalepainting.com",
            rights=rights, about_me=
            """
I created all of this.

This entire site.

I am the puppetmaster.

I also really like wine.
            """)
    malan.set_password(args.password)
    db.session.add(malan)

########################
if not args.malanonly:

    ###################
    community = User.query.filter_by(displayname="Community").first()
    if not community:
        community = User(displayname="Community",
                email="community@annopedia.org", about_me=
                """
Hi, 

I’m not a real person. I’m an account used to author annotations by non-members,
such as the authors of the books hosted on Annopedia.  An example would be the
annotations provided by [[Writer:Constance Garnett]] in her translations of
classic Russian literature like War and Peace.

The original author of the annotations will always be tagged with a special tag
that will be locked to users.

I hope you enjoy their annotations!

Sincerely,

The Annopedia Team
                """)

        community.set_password(args.password)
        db.session.add(community)

    ################
    chris = User.query.filter_by(displayname="chris").first()
    if not chris:
        chris = User(displayname="chris", email="chriss@glendalepainting.com",
                about_me=
                """
I'm a fake user created by malan to be used like a puppet.

I also like beer.
                """)
        chris.set_password(args.password)
        db.session.add(chris)

    ################
    nick = User.query.filter_by(displayname="nick").first()
    if not nick:
        nick = User(displayname="nick", email="nsendker@gmail.com",
                about_me=
                """
I'm a fake user created by malan to be used like a puppet.

I also like cocktails.
                """)
        nick.set_password(args.password)
        db.session.add(nick)



if args.dryrun:
    db.session.rollback()
else:
    db.session.commit()
