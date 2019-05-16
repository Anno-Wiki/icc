"""The user classes. This module is more complicated than I'd like."""
import jwt
import sys
import inspect

from datetime import datetime
from time import time
from hashlib import md5

from flask import abort, url_for, current_app as app
from flask_login import UserMixin, AnonymousUserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import orm
from sqlalchemy.orm import backref
from sqlalchemy.ext.associationproxy import association_proxy

from icc import db, login
from icc.models.mixins import Base, EnumMixin, FlagMixin


@login.user_loader
def _load_user(id):
    """Necessary method for flask_login. Do not call. """
    return User.query.get(int(id))


class MyAnonymousUserMixin(AnonymousUserMixin):
    """An override for the typical anonymous user class that provides methods to
    prevent AttributeError's.
    """

    def is_auth_any(self, rights):
        """Dummy auth method"""
        return False

    def is_auth_all(self, rights):
        """Dummy auth method"""
        return False

    def is_authorized(self, right):
        """Dummy auth method"""
        return False

    def authorize(self, right):
        """Dummy auth method"""
        abort(503)

    def get_vote(self, entity):
        """Dummy vote return method"""
        return None


# override the AnonymouseUserMixin
login.anonymous_user = MyAnonymousUserMixin


class User(UserMixin, Base):
    """The User class.

    Inherits
    --------
    UserMixin

    Attributes
    ----------
    displayname : str
        We follow StackExchange in using displaynames that are non-unique and
        can be changed. The user is primarily defined by his email.
    email : str
        The primary string-based identifier of the user. Must be unique. Have
        not worked on email validation yet, need to.
    password_hash : str
        The FlaskLogin defined password hashing structure. I want to investigate
        the security of this and make modifications before going live (e.g.,
        check algorithm, salt, etc.).
    reputation : int
        The user's reputation. This is affected by :class:`ReputationChange`
        objects.
    locked : int
        This is a boolean to lock the user's account from logging in for
        security purposes.
    about_me : str
        A text of seemingly any length that allows the user to describe
        themselves. I might convert this to a wiki. Not sure if it's worth it or
        not. Probably not. About me history? Extreme. On the other hand, it
        leverages the existing wiki system just like Wikipedia does.
    last_seen : DateTime
        A timestamp for when the user last made a database-modification.
    rights : list
        A list of all of the :class:`AdminRight` objects the user has.
    annotations : BaseQuery
        An SQLA BaseQuery of all the annotations the user has authored.
    followed_<class>s : BaseQuery
        A BaseQuery of all of the <class>'s that the user is currently
        following. The <class> is the class's name lowercased (same as the table
        name).
    followers : BaseQuery
        A BaseQuery of all of the User's that follow this User.
    """
    displayname = db.Column(db.String(64), index=True)
    email = db.Column(db.String(128), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    reputation = db.Column(db.Integer, default=0)
    locked = db.Column(db.Boolean, default=False)
    about_me = db.Column(db.Text)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    reputation_changes = db.relationship('ReputationChange', lazy='dynamic')
    rights = db.relationship('AdminRight', secondary='rights')
    annotations = db.relationship('Annotation', lazy='dynamic')
    active_flags = db.relationship('UserFlag',
                                   primaryjoin='and_(User.id==UserFlag.user_id,'
                                   'UserFlag.resolver_id==None)',
                                   passive_deletes=True)

    # Because this is a self-referential many-to-many it is defined explicitly
    # as opposed to using my FollowableMixin
    followed_users = db.relationship(
        'User',
        secondary=db.Table(
            'user_flrs',
            db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
            db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))),
        primaryjoin='user_flrs.c.follower_id==User.id',
        secondaryjoin='user_flrs.c.followed_id==User.id',
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')

    @property
    def url(self):
        """A string that represents the url for this user object (i.e., the
        user's profile page.
        """
        return url_for("user.profile", user_id=self.id)

    @property
    def readable_reputation(self):
        """A string that represents a nicely formatted reputation of this user.
        """
        if self.reputation >= 1000000:
            return f'{round(self.reputation/1000000)}m'
        elif self.reputation >= 1000:
            return f'{round(self.reputation/1000)}k'
        else:
            return f'{self.reputation}'

    def avatar(self, size):
        """A link to the gravatar for this user. I will probably eventually want
        to simply eliminate avatars. Especially gravatars as they are a security
        vulnerability.
        """
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}'

    def __repr__(self):
        return f"<User {self.displayname}>"

    def __str__(self):
        return self.displayname

    def update_last_seen(self):
        """A method that will update the user's last seen timestamp."""
        self.last_seen = datetime.utcnow()

    def repchange(self, enumstring):
        """Change a user's reputation given the enumstring."""
        enum = ReputationEnum.query.filter_by(enum=enumstring).first()
        if not enum:
            return
        repchange = ReputationChange(enum=enum, user=self,
                                     delta=enum.default_delta)
        if self.reputation + repchange.delta <= 0:
            repchange.delta = -self.reputation
        self.reputation += repchange.delta
        return repchange

    def rollback_repchange(self, repchange):
        """Rollback a user's reputation given a reputationchange."""
        if not repchange:
            return
        if self.reputation - repchange.delta < 0:
            delta = -self.reputation
        else:
            delta = repchange.delta
        self.reputation -= delta
        db.session.delete(repchange)

    # Password routes
    def set_password(self, password):
        """Set the password for the user."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check that the password provided is the user's current password."""
        return check_password_hash(self.password_hash, password)

    def get_reset_password_token(self, expires_in=600):
        """Generate a reset_password token for the user's emailed link to reset
        the password.
        """
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            app.config['SECRET_KEY'], algorithm='HS256').decode('utf-8')

    @staticmethod
    def verify_reset_password_token(token):
        """A static method to verify a reset password token's validity."""
        try:
            id = jwt.decode(token, app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)

    # admin authorization methods
    def is_authorized(self, right):
        """Check if a user is authorized with a particular right."""
        r = AdminRight.query.filter_by(enum=right).first()
        if not r:
            return False
        return r in self.rights or (r.min_rep and self.reputation >= r.min_rep)

    def is_auth_all(self, rights):
        """This is like is_authorized but takes a list and only returns true if
        the user is authorized for all the rights in the list.
        """
        for right in rights:
            if not self.is_authorized(right):
                return False
        return True

    def is_auth_any(self, rights):
        """Tests if user is authorized for *any* of the rights in the list."""
        for right in rights:
            if self.is_authorized(right):
                return True
        return False

    def authorize(self, right):
        """Authorize a user with a right.

        Notes
        -----
        This is different from is_authorized (in fact, it uses is_authorized):
        this method will throw a 403 abort if the user is not authorized. It
        simplifies some logic.
        """
        if self.is_authorized(right):
            pass
        else:
            abort(403)

    def get_vote(self, obj):
        """Get the vote on the object. If the object does not have a __vote__
        attribute, it's not going to work and a TypeError will be raised.

        This method works for every votable class and can be tested as a Falsey
        for whether or whether not the user has voted on the object.
        """
        if not obj.__vote__:
            raise TypeError("The requested object is missing an `__vote__` "
                            "attribute.")
        vote_cls = obj.__vote__
        return vote_cls.query.filter(vote_cls.voter==self,
                                     vote_cls.entity==obj).first()


class AdminRight(Base, EnumMixin):
    """The class used to represent a user's rights.

    Inherits
    --------
    EnumMixin

    Attributes
    ----------
    min_rep : int
        An integer representing the minimum reputation to authorize a user for
        the right (so we grant certain rights based on the user's reputation).
        If the min_rep is None, the user has to posses the right in their
        `rights`.
    """
    min_rep = db.Column(db.Integer)

    def __repr__(self):
        return f'<Right to {self.enum}>'


class ReputationEnum(Base, EnumMixin):
    """An enum for a ReputationChange.

    Inherits
    --------
    EnumMixin

    Attributes
    ----------
    default_delta : int
        An integer representing the default reputation change value. That is to
        say, the amount by which the event will change the user's reputation.
    """
    default_delta = db.Column(db.Integer, nullable=False)
    entity = db.Column(db.String(128))
    display = db.Column(db.String(128))


class ReputationChange(Base):
    """An object representing a reputation change event. This thing exists to
    avoid mischanges to the reputation. It's a ledger so we can audit every rep
    change and the user can see the events.

    Attributes
    ----------
    delta : int
        A number representing the change to the user's reputation.
    user_id : int
        The id of the user.
    timestamp : datetime
        The time the reputation change happened
    enum_id : int
        the id of the reputation change enum
    user : :class:`User`
        The user whose reputation was changed.
    enum : :class:`ReputationEnum`
        The enum of the particular rep change.
    """
    delta = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    enum_id = db.Column(db.Integer, db.ForeignKey('reputationenum.id'),
                        nullable=False)

    user = db.relationship('User', backref='changes')
    enum = db.relationship('ReputationEnum')
    type = association_proxy('enum', 'enum')

    def __repr__(self):
        return (f'<rep change {self.type} on {self.user.displayname} '
                f'{self.timestamp}>')

    @orm.reconstructor
    def __init_on_load__(self):
        # this is cleaner than the entity population of the wiki system, but it
        # relies on the existence of the enum to call on. Since that is
        # necessary, wiki can't use the same method.
        self.entity = getattr(self, self.enum.entity.lower(), None)


class UserFlag(Base, FlagMixin):
    """A flag event on a user."""
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    entity = db.relationship('User', foreign_keys=[user_id],
                             backref=backref('flags', lazy='dynamic'))


classes = dict(inspect.getmembers(sys.modules[__name__], inspect.isclass))
classes['UserFlagEnum'] = UserFlag.enum_cls
