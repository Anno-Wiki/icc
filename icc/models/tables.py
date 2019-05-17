"""Basic many-to-many tables."""
from icc import db


"""The tags table connects tags to edits."""
tags = db.Table(
    'tags',
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id')),
    db.Column('edit_id', db.Integer, db.ForeignKey('edit.id')))

"""The rights table connects AdminRight to a User."""
rights = db.Table(
    'rights',
    db.Column('right_id', db.Integer, db.ForeignKey('adminright.id')),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')))
