from datetime import datetime

from sqlalchemy.orm import backref
from sqlalchemy.ext.declarative import declared_attr

from flask import flash
from flask_login import current_user

from icc import db
from icc.search import add_to_index, remove_from_index, query_index


class Base(db.Model):
    __abstract__ = True


class EnumMixin:
    enum = db.Column(db.String(128), index=True)

    def __repr__(self):
        return f"<{type(self)} {self.enum}>"


class VoteMixin:
    delta = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow())

    @declared_attr
    def voter_id(cls):
        return db.Column(db.Integer, db.ForeignKey('user.id'))

    @declared_attr
    def voter(cls):
        # the backref is the name of the class lowercased with the word
        # `ballots` appended
        return db.relationship(
            'User', backref=backref(f'{cls.__name__.lower()}ballots',
                                    lazy='dynamic'))

    def __repr__(self):
        return f"<{self.voter.displayname} {self.delta} on "

    def is_up(self):
        return self.delta > 0


class EditMixin:
    num = db.Column(db.Integer, default=1)
    current = db.Column(db.Boolean, index=True, default=False)
    weight = db.Column(db.Integer, default=0)
    approved = db.Column(db.Boolean, index=True, default=False)
    rejected = db.Column(db.Boolean, index=True, default=False)
    reason = db.Column(db.String(191))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow(), index=True)
    body = db.Column(db.Text)

    @declared_attr
    def editor_id(cls):
        return db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False,
                         default=1)

    @declared_attr
    def editor(cls):
        # The backref is the class name lowercased with an `s` appended
        return db.relationship(
            'User', backref=backref(f'{cls.__name__.lower()}s', lazy='dynamic'))

    @declared_attr
    def previous(cls):
        # The previous edit (i.e., single instance)
        return db.relationship(
            f'{cls.__name__}',
            primaryjoin=f'and_(remote({cls.__name__}.entity_id)'
            f'==foreign({cls.__name__}.entity_id),'
            f'remote({cls.__name__}.num)==foreign({cls.__name__}.num-1),'
            f'remote({cls.__name__}.rejected)==False)')

    @declared_attr
    def priors(cls):
        # A list of all prior edits
        return db.relationship(
            f'{cls.__name__}',
            primaryjoin=f'and_(remote({cls.__name__}.entity_id)=='
            f'foreign({cls.__name__}.entity_id),'
            f'remote({cls.__name__}.num)<=foreign({cls.__name__}.num-1))',
            uselist=True)

    def __repr__(self):
        return f"<Edit {self.num} on "

    def rollback(self, vote):
        self.weight -= vote.delta
        db.session.delete(vote)

    def reject(self):
        self.rejected = True
        flash("The edit was rejected.")


# If you encounter an error while committing to the effect that `NoneType has no
# attribute <x>` what you have done is specify an id# instead of an object. Use
# the ORM. if that is not the case, it is because, for example, in the case of
# Annotation.HEAD, you have created a new Annotation and Edit for HEAD to point
# to, but because of the complex relationship to form HEAD, HEAD is still empty.
# Simply add the expression `<annotation>.HEAD = <edit>` and you'll be gold,
# even if it _is_ unecessary.
class SearchableMixin(object):
    @classmethod
    def search(cls, expression, page, per_page):
        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        if total == 0:
            return cls.query.filter_by(id=0), 0
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))
        return cls.query.filter(cls.id.in_(ids)).order_by(
            db.case(when, value=cls.id)).all(), total

    @classmethod
    def before_commit(cls, session):
        if current_user and current_user.is_authenticated:
            current_user.last_seen = datetime.utcnow()
        session._changes = {
                'add': list(session.new),
                'update': list(session.dirty),
                'delete': list(session.deleted)
                }
        # This accesses all the necessary fields in searchable so they are
        # loaded into memory from sqlalchemy before we commit
        for key, change in session._changes.items():
            for obj in change:
                if isinstance(obj, SearchableMixin):
                    for field in obj.__searchable__:
                        getattr(obj, field)

    @classmethod
    def after_commit(cls, session):
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        session._changes = None

    @classmethod
    def reindex(cls, **kwargs):
        qry = cls.query if not kwargs else cls.query.filter_by(**kwargs)
        for obj in qry:
            add_to_index(cls.__tablename__, obj)


db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)
