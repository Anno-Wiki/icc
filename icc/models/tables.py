from icc import db


authors = db.Table(
    'authors',
    db.Column('writer_id', db.Integer, db.ForeignKey('writer.id')),
    db.Column('text_id', db.Integer, db.ForeignKey('text.id')))
tags = db.Table(
    'tags',
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id')),
    db.Column('edit_id', db.Integer, db.ForeignKey('edit.id',
                                                   ondelete='CASCADE')))
rights = db.Table(
    'rights',
    db.Column('right_id', db.Integer, db.ForeignKey('user_right.id')),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')))


# flrs
text_flrs = db.Table(
    'text_flrs',
    db.Column('text_id', db.Integer, db.ForeignKey('text.id')),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')))
writer_flrs = db.Table(
    'writer_flrs',
    db.Column('writer_id', db.Integer, db.ForeignKey('writer.id')),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')))
user_flrs = db.Table(
    'user_flrs',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id')))
tag_flrs = db.Table(
    'tag_flrs',
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id')),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')))
annotation_flrs = db.Table(
    'annotation_flrs',
    db.Column('annotation_id', db.Integer,
              db.ForeignKey('annotation.id', ondelete='CASCADE')),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')))
tag_request_flrs = db.Table(
    'tag_request_flrs',
    db.Column('tag_request_id', db.Integer,
              db.ForeignKey('tag_request.id', ondelete='CASCADE')),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')))
text_request_flrs = db.Table(
    'text_request_flrs',
    db.Column('text_request_id', db.Integer,
              db.ForeignKey('text_request.id', ondelete='CASCADE')),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')))
