"""This module contains all the Mixins that I use throughout the models."""
from datetime import datetime

from sqlalchemy.orm import backref
from sqlalchemy.ext.declarative import declared_attr

from flask import flash
from flask_login import current_user

from icc import db
from icc.search import add_to_index, remove_from_index, query_index


class Base(db.Model):
    """This Base class does nothing. It is here in case I need to expand
    implement something later. I feel like it's a good early practice.
    """
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True)


class EnumMixin:
    """Any enumerated class that has more than 4 types should be use this
    EnumMixin. LineEnum and Right seem to be the biggest examples.

    Attributes
    ----------
    enum : str
        A string for holding an enumerated type.
    """
    enum = db.Column(db.String(128), index=True)

    def __repr__(self):
        return f"<{type(self)} {self.enum}>"


class VoteMixin:
    """A Mixin for votes. This is useful because users can vote on more than
    just Annotations.

    Attributes
    ----------
    delta : int
        The difference the vote applies to the weight of the object.
    timestamp : DateTime
        The timestamp of when the vote was created.
    is_up : bool
        A boolean that indicates whether the vote is up or down.
    """
    delta = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow())

    @property
    def is_up(self):
        """A boolean representing the vector of the vote (i.e., True for up,
        False for down).
        """
        return self.delta > 0

    @declared_attr
    def voter_id(cls):
        """The id of the voter."""
        return db.Column(db.Integer, db.ForeignKey('user.id'))

    @declared_attr
    def voter(cls):
        """The voter."""
        # the backref is the name of the class lowercased with the word
        # `ballots` appended
        return db.relationship(
            'User', backref=backref(f'{cls.__name__.lower()}ballots',
                                    lazy='dynamic'))

    def __repr__(self):
        return f"<{self.voter.displayname} {self.delta} on "


class EditMixin:
    """A mixin to store edits. This is to be used for anything that can be
    edited so that we can have an edit history.

    Notes
    -----
    Currently, the only methods I have implemented here are rollback and reject
    because of the different naming strategies of the votes. THIS CAN BE
    CORRECTED. I believe I have to investigate Meta classes or something like
    that to make sure that something is implemented or something. But this
    EditMixin can be tied in in such a way that those methods can be collapsed.
    I need to do this.

    Attributes
    ----------
    num : int
        The number of the edit in the edit history.
    current : bool
        A boolean indicating withether this is the current state of the parent
        object or not. There should only ever be one per object. There should
        always be at least one. If there are more than or less than one for an
        object THAT IS A PROBLEM.
    weight : int
        The weight of the object (basically the difference between upvotes and
        downvotes, but a bit more complicated than that.
    approved : bool
        Whether the edit has been approved or not.
    rejected : bool
        Whether the edit has been rejected or not. `approved` and `rejected`
        should not both be True, but they can both be False (namely, immediately
        after being created, before it is reviewed).
    reason : str
        A string explaining the reason for the edit. Will probably be abused and
        ignored. But good practice.
    timestamp : DateTime
        When the edit was made.
    body : str
        The actual body of the Edit.
    """
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
        """The id of the editor."""
        return db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False,
                         default=1)

    @declared_attr
    def editor(cls):
        """The actual user object of the editor. The backref is the class name
        lowercased with an `s` appended
        """
        return db.relationship(
            'User', backref=backref(f'{cls.__name__.lower()}s', lazy='dynamic'))

    @declared_attr
    def previous(cls):
        """The previous edit."""
        return db.relationship(
            f'{cls.__name__}',
            primaryjoin=f'and_(remote({cls.__name__}.entity_id)'
            f'==foreign({cls.__name__}.entity_id),'
            f'remote({cls.__name__}.num)==foreign({cls.__name__}.num-1),'
            f'remote({cls.__name__}.rejected)==False)')

    @declared_attr
    def priors(cls):
        """A list of all prior edits"""
        return db.relationship(
            f'{cls.__name__}',
            primaryjoin=f'and_(remote({cls.__name__}.entity_id)=='
            f'foreign({cls.__name__}.entity_id),'
            f'remote({cls.__name__}.num)<=foreign({cls.__name__}.num-1))',
            uselist=True)

    def __repr__(self):
        return f"<Edit {self.num} on "

    def rollback(self, vote):
        """Roll back a user's vote on the edit because he wants to change it."""
        self.weight -= vote.delta
        db.session.delete(vote)

    def reject(self):
        """Reject the edit."""
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
    """The Mixin for a searchable class. This might need to be expanded with a
    classmethod for searching across indexes (i.e., an omni search).
    """
    @classmethod
    def search(cls, expression, page, per_page):
        """Search with a given string."""
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
        """A method called before any commit."""
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
        """A method called after any commit."""
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
        """This reindexes all the objects in a searchable class."""
        qry = cls.query if not kwargs else cls.query.filter_by(**kwargs)
        for obj in qry:
            add_to_index(cls.__tablename__, obj)


# register before and after commits.
db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)
