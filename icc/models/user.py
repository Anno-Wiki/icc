"""The user classes. This module is more complicated than I'd like."""
import jwt
import sys
import inspect

from datetime import datetime
from time import time
from hashlib import md5
from math import log10

from flask import abort, url_for, current_app as app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.ext.associationproxy import association_proxy

from icc import db, login
from icc.models.mixins import Base, EnumMixin
from icc.models.wiki import WikiEditVote
from icc.models.request import TextRequestVote, TagRequestVote

# We have to import the whole module in this file to avoid the circular import.
# I would love to find a simpler fix for this, but in this case we do this for
# access to only two classes, Vote, and EditVote. I tried to do it in the other
# file, instead, but for some reason I was getting the same error with the call
# to `from icc.models.annotation import Vote, EditVote` here: namely, that the
# system couldn't find icc.models.annotation. Rather strange, imo.
import icc.models.annotation


@login.user_loader
def load_user(id):
    """Necessary method for flask_login."""
    return User.query.get(int(id))


class User(UserMixin, Base):
    """The User class.

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
    voted_<class> : list
        A list of <class> objects that have been voted on by the user. I am
        going to work to make this more dynamic and less anti-DRY
    """
    displayname = db.Column(db.String(64), index=True)
    email = db.Column(db.String(128), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    reputation = db.Column(db.Integer, default=0)
    locked = db.Column(db.Boolean, default=False)
    about_me = db.Column(db.Text)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    rights = db.relationship('AdminRight', secondary='rights')
    annotations = db.relationship('Annotation', lazy='dynamic')

    voted_annotation = association_proxy('annotationvoteballots', 'annotation')
    voted_edit = association_proxy('editballots', 'edit')
    voted_wikiedit = association_proxy('wikieditballots', 'edit')
    voted_textrequest = association_proxy('textrequestballots', 'request')
    voted_tagrequest = association_proxy('tagrequestballots', 'request')

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
        return url_for("user.profile", user_id=self.id)

    @property
    def readable_reputation(self):
        if self.reputation >= 1000000:
            return f'{round(self.reputation/1000000)}m'
        elif self.reputation >= 1000:
            return f'{round(self.reputation/1000)}k'
        else:
            return f'{self.reputation}'

    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}'

    @property
    def up_power(self):
        if self.reputation <= 1:
            return 1
        else:
            return int(10*log10(self.reputation))

    @property
    def down_power(self):
        power = self.up_power
        if power / 2 <= 1:
            return -1
        else:
            return -int(power)

    def __repr__(self):
        return f"<User {self.displayname}>"

    def update_last_seen(self):
        self.last_seen = datetime.utcnow()

    def flag(self, flag, thrower):
        event = UserFlag(flag=flag, user=self, thrower=thrower)
        db.session.add(event)

    # Password routes
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            app.config['SECRET_KEY'], algorithm='HS256').decode('utf-8')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)

    # admin authorization methods
    def authorize(self, right):
        if self.is_authorized(right):
            pass
        else:
            abort(403)

    def is_authorized(self, right):
        r = AdminRight.query.filter_by(enum=right).first()
        print(r)
        print(r.min_rep)
        print(self.reputation)
        return r in self.rights or (r.min_rep and self.reputation >= r.min_rep)

    def get_vote(self, obj):
        """Get the vote on the object. If the object does not have a
        __vote__ attribute, it's not going to work and a TypeError will be
        raised.

        This method works for every votable class and can be tested as a bool
        for whether or whether not the user has voted on the object.
        """
        if not obj.__vote__:
            raise TypeError("The requested object is missing an `__vote__` "
                            "attribute.")
        vote_cls = obj.__vote__
        return vote_cls.query.filter_by(voter=self).first()


class AdminRight(Base, EnumMixin):
    min_rep = db.Column(db.Integer)

    def __repr__(self):
        return f'<Right to {self.enum}>'


class ReputationEnum(Base, EnumMixin):
    default_delta = db.Column(db.Integer, nullable=False)


class ReputationChange(Base):
    delta = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    enum_id = db.Column(db.Integer, db.ForeignKey('reputationenum.id'),
                        nullable=False)

    user = db.relationship('User', backref='changes')
    type = db.relationship('ReputationEnum')

    def __repr__(self):
        return f'<rep change {self.type} on {self.user.displayname}>'


class UserFlagEnum(Base, EnumMixin):
    ...


class UserFlag(Base):
    user_flag_id = db.Column(db.Integer, db.ForeignKey('userflagenum.id'),
                             index=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)

    thrower_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    time_thrown = db.Column(db.DateTime, default=datetime.utcnow())

    time_resolved = db.Column(db.DateTime)
    resolver_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)

    user = db.relationship('User', foreign_keys=[user_id])
    thrower = db.relationship('User', foreign_keys=[thrower_id])
    resolver = db.relationship('User', foreign_keys=[resolver_id])

    flag = db.relationship('UserFlagEnum')

    def __repr__(self):
        if self.resolved:
            return f'<X UserFlag: {self.flag.enum} at {self.time_thrown}>'
        else:
            return f'<UserFlag thrown: {self.flag.enum} at {self.time_thrown}>'

    def resolve(self, resolver):
        self.time_resolved = datetime.utcnow()
        self.resolver = resolver

    def unresolve(self):
        self.time_resolved = None
        self.resolver = None


classes = dict(inspect.getmembers(sys.modules[__name__], inspect.isclass))
