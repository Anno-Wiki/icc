from icc import db


tags = db.Table(
    'tags',
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id')),
    db.Column('edit_id', db.Integer, db.ForeignKey('edit.id',
                                                   ondelete='CASCADE')))
rights = db.Table(
    'rights',
    db.Column('right_id', db.Integer, db.ForeignKey('adminright.id')),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')))
