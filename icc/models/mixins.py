"""This module contains all the Mixins that I use throughout the models."""
from datetime import datetime

from sqlalchemy.orm import backref
from sqlalchemy.ext.declarative import declared_attr

from flask import flash, current_app
from flask_login import current_user

from icc import db
from icc.search import add_to_index, remove_from_index, query_index


class Base(db.Model):
    """This Base class does nothing. It is here in case I need to expand
    implement something later. I feel like it's a good early practice.

    Attributes
    ----------
    id : int
        The basic primary key id number of any class.

    Notes
    -----
    The __tablename__ is automatically set to the class name lower-cased.
    There's no need to mess around with underscores, that just confuses the
    issue and makes programmatically referencing the table more difficult.
    """
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True)

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()


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
        return f"<{type(self).__name__} {self.enum}>"


class FlagMixin:
    """FlagMixin is a complex mixin. It defines a new class for enums for flags.
    I *like* it.
    """

    @declared_attr
    def enum_cls(cls):
        """Literally a class. It is the enum class for the flags. Generally,
        after defining a Flag class, (which may end up becoming `FlaggableMixin`
        composable if I'm crazy enough) you should hoist the enum_cls value up
        into the namespace by declaring (after declaring the class that inherits
        FlagMixin) `<cls>Enum = <cls>.enum_cls`. That solves a lot of problems.
        """
        return type(
            f'{cls.__name__}Enum', (Base, EnumMixin),
            {'__repr__': lambda self: f'<{type(self).__name__} {self.enum}'}
        )

    @declared_attr
    def enum_id(cls):
        """The id of the enum that this particular flag is typed."""
        return db.Column(db.Integer,
                         db.ForeignKey(f'{cls.__name__.lower()}enum.id'),
                         index=True)

    @declared_attr
    def enum(cls):
        """The actual enum object that this relationship is typed to."""
        return db.relationship(f'{cls.__name__}Enum')

    @declared_attr
    def thrower_id(cls):
        """The id of the user who threw the flag."""
        return db.Column(db.Integer, db.ForeignKey('user.id'), index=True)

    @declared_attr
    def thrower(cls):
        """The user who threw the flag."""
        return db.relationship('User', foreign_keys=[cls.thrower_id])

    @declared_attr
    def resolver_id(cls):
        """The id of the user who resolved the flag."""
        return db.Column(db.Integer, db.ForeignKey('user.id'), index=True)

    @declared_attr
    def resolver(cls):
        """The user who resolved the flag."""
        return db.relationship('User', foreign_keys=[cls.resolver_id])

    @declared_attr
    def time_thrown(cls):
        """The time the flag was thrown."""
        return db.Column(db.DateTime, default=datetime.utcnow())

    @declared_attr
    def time_resolved(cls):
        """The time the flag was resolved."""
        return db.Column(db.DateTime)

    @classmethod
    def flag(cls, obj, enum, thrower):
        """A class method to flag the object (or jerk)."""
        db.session.add(cls(entity=obj, enum=enum, thrower=thrower))

    def __repr__(self):
        """Branches representations based on resolution status."""
        if self.resolved:
            return (f"<X {type(self).__name__}: "
                    f"{self.flag} at {self.time_thrown}>")
        else:
            return (f"<{type(self).__name__} thrown: "
                    f"{self.flag} at {self.time_thrown}>")

    def resolve(self, resolver):
        """Resolve the flag.

        Parameters
        ----------
        resolver : :class:`User`
            The user that is resolving the flag.
        """
        self.time_resolved = datetime.utcnow()
        self.resolver = resolver

    def unresolve(self):
        """Unresolves the flag (i.e., puts it back into play)."""
        self.time_resolved = None
        self.resolver = None


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
            'User', backref=backref(f'{cls.__name__.lower()}_ballots',
                                    lazy='dynamic'))

    def __repr__(self):
        return f"<{self.voter.displayname} {self.delta} on "


class VotableMixin:
    """An easy application to make an object votable. There already needs to be
    a VoteMixin application. Also, define the following attributes on the child
    class:

    __vote__ = <the class of the vote>
    __reputable__ = <string corresponding to the attribute of what user to apply
                     the reputation change to, if there is one.>
    """

    def upvote(self, voter):
        if hasattr(self, 'approved') and (self.approved or self.rejected):
            flash("Voting is closed.")
            return
        if getattr(self, self.__reputable__) == voter:
            flash("You cannot vote on your own submissions.")
            return
        ov = voter.get_vote(self)
        if ov:
            self.rollback(ov)
            if ov.is_up:
                return
        if self.__reputable__:
            repchange = getattr(self, self.__reputable__)\
                .repchange(f'{self.__class__.__name__}_upvote')
        else:
            repchange = None
        weight = self.up_power(voter) if hasattr(self, 'up_power') else 1
        vote = self.__vote__(voter=voter, entity=self, delta=weight,
                             repchange=repchange)
        self.weight += vote.delta
        db.session.add(vote)
        if (hasattr(self, 'approved') and
                (self.weight >= current_app.config['VOTES_FOR_APPROVAL']
                 or voter.is_authorized('immediate_edits'))):
            self.approve()

    def downvote(self, voter):
        if hasattr(self, 'approved') and (self.approved or self.rejected):
            flash("Voting is closed.")
            return
        if getattr(self, self.__reputable__) == voter:
            flash("You cannot vote on your own submissions.")
            return
        ov = voter.get_vote(self)
        if ov:
            self.rollback(ov)
            if ov.is_down:
                return
        if self.__reputable__:
            repchange = getattr(self, self.__reputable__)\
                .repchange(f'{self.__class__.__name__}_downvote')
        else:
            repchange = None
        weight = self.down_power(voter) if hasattr(self, 'down_power') else -1
        vote = self.__vote__(voter=voter, entity=self, delta=weight,
                             repchange=repchange)
        self.weight += vote.delta
        db.session.add(vote)
        if (hasattr(self, 'rejected') and
                (self.weight >= current_app.config['VOTES_FOR_REJECTION']
                 or voter.is_authorized('immediate_edits'))):
            self.reject()

    def rollback(self, vote):
        self.weight -= vote.delta
        if vote.repchange:
            vote.repchange.user.rollback_repchange(vote.repchange)
        db.session.delete(vote)

    def approve(self):
        """Approve the edit."""
        getattr(self, self.__reputable__)\
            .repchange(f'{self.__class__.__name__}_approval')
        self.approved = True
        self.previous.current = False
        self.current = True
        flash("Edit approved.")

    def reject(self):
        """Reject the edit."""
        self.rejected = True
        flash("Edit rejected.")


class LinkableMixin:
    """A mixin to be able to process double-bracket style links (e.g.,
    [[Writer:Constance Garnett]] and produce an href or the object.
    """
    @classmethod
    def get_object_by_link(cls, name):
        """Get the object by the name."""
        if not cls.__linkable__:
            raise AttributeError("Class does not have a __linkable__ "
                                 "attribute.")
        obj = cls.query.filter(getattr(cls, cls.__linkable__)==name).first()
        return obj

    @classmethod
    def link(cls, name):
        """Produce the href given the name."""
        try:
            obj = cls.get_object_by_link(name)
        except AttributeError:
            return name

        if not obj:
            return name
        else:
            if not hasattr(obj, 'url'):
                raise AttributeError("Object does not have a url.")
            return f'<a href="{obj.url}">{name}</a>'


class FollowableMixin:
    """A mixin to automagically make an object followable. Unfotunately, it
    doesn't create the follow/unfollow routes automagically. That would be nice.
    """

    @declared_attr
    def table(cls):
        """Produces a followers table for the many-to-many relationship."""
        return db.Table(
            f'{cls.__name__.lower()}_followers',
            db.Column(f'{cls.__name__.lower()}_id', db.Integer,
                      db.ForeignKey(f'{cls.__name__.lower()}.id')),
            db.Column('user_id', db.Integer, db.ForeignKey('user.id')))

    @declared_attr
    def followers(cls):
        """Produces the relationship and backreference for followers."""
        return db.relationship('User',
                               secondary=f'{cls.__name__.lower()}_followers',
                               backref=backref(
                                   f'followed_{cls.__name__.lower()}s',
                                   lazy='dynamic'),
                               lazy='dynamic')


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
