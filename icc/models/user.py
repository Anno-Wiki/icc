import jwt
import sys
import inspect

from datetime import datetime
from time import time
from hashlib import md5
from math import log10

from flask import abort, current_app as app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from icc import db, login
from icc.models.mixins import Base, EnumMixin
from icc.models.tables import user_flrs
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
    return User.query.get(int(id))


class User(UserMixin, Base):
    id = db.Column(db.Integer, primary_key=True)
    displayname = db.Column(db.String(64), index=True)
    email = db.Column(db.String(128), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    reputation = db.Column(db.Integer, default=0)
    locked = db.Column(db.Boolean, default=False)
    about_me = db.Column(db.Text)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    # user meta information relationships
    rights = db.relationship('Right', secondary='rights', backref='admins')

    # annotations voted on
    votes = db.relationship('Annotation', secondary='vote',
                            primaryjoin='User.id==Vote.voter_id',
                            secondaryjoin='Annotation.id==Vote.annotation_id',
                            backref='voters', lazy='dynamic')
    # edits voted on
    edit_votes = db.relationship('Edit', secondary='edit_vote',
                                 primaryjoin='User.id==EditVote.voter_id',
                                 secondaryjoin='Edit.id==EditVote.edit_id',
                                 backref='edit_voters', lazy='dynamic')
    # wiki edits voted on
    wiki_edit_votes = db.relationship(
        'WikiEdit', secondary='wiki_edit_vote',
        primaryjoin='User.id==WikiEditVote.voter_id',
        secondaryjoin='WikiEdit.id==WikiEditVote.edit_id', backref='voters',
        lazy='dynamic')
    # text requests voted on
    text_request_votes = db.relationship(
        'TextRequest', secondary='text_request_vote',
        primaryjoin='TextRequestVote.voter_id==User.id',
        secondaryjoin='TextRequestVote.text_request_id==TextRequest.id',
        backref='voters', lazy='dynamic', passive_deletes=True)
    # tag requests voted on
    tag_request_votes = db.relationship(
        'TagRequest', secondary='tag_request_vote',
        primaryjoin='TagRequestVote.voter_id==User.id',
        secondaryjoin='TagRequestVote.tag_request_id==TagRequest.id',
        backref='voters', lazy='dynamic')

    # flag relationships
    flags = db.relationship(
        'UserFlagEnum', secondary='user_flag',
        primaryjoin='and_(UserFlag.user_id==User.id,'
        'UserFlag.resolver_id==None)',
        secondaryjoin='UserFlag.user_flag_id==UserFlagEnum.id', backref='users')
    flag_history = db.relationship(
        'UserFlag', primaryjoin='UserFlag.user_id==User.id', lazy='dynamic')
    active_flags = db.relationship(
        'UserFlag', primaryjoin='and_(UserFlag.user_id==User.id,'
        'UserFlag.resolver_id==None)')

    followed_users = db.relationship(
        'User', secondary=user_flrs,
        primaryjoin=(user_flrs.c.follower_id == id),
        secondaryjoin=(user_flrs.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')
    followed_texts = db.relationship(
        'Text', secondary='text_flrs',
        primaryjoin='text_flrs.c.user_id==User.id',
        secondaryjoin='text_flrs.c.text_id==Text.id',
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')
    followed_writers = db.relationship(
        'Writer', secondary='writer_flrs',
        primaryjoin='writer_flrs.c.user_id==User.id',
        secondaryjoin='writer_flrs.c.writer_id==Writer.id',
        backref=db.backref('writer_flrs', lazy='dynamic'), lazy='dynamic')
    followed_tags = db.relationship(
        'Tag', secondary='tag_flrs',
        primaryjoin='tag_flrs.c.user_id==User.id',
        secondaryjoin='tag_flrs.c.tag_id==Tag.id',
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')
    followed_annotations = db.relationship(
        'Annotation', secondary='annotation_flrs',
        primaryjoin='annotation_flrs.c.user_id==User.id',
        secondaryjoin='annotation_flrs.c.annotation_id==Annotation.id',
        backref=db.backref('followers', lazy='dynamic', passive_deletes=True),
        lazy='dynamic')
    followed_tag_requests = db.relationship(
        'TagRequest', secondary='tag_request_flrs',
        primaryjoin='tag_request_flrs.c.user_id==User.id',
        secondaryjoin='tag_request_flrs.c.tag_request_id==TagRequest.id',
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')
    followed_text_requests = db.relationship(
        'TextRequest', secondary='text_request_flrs',
        primaryjoin='text_request_flrs.c.user_id==User.id',
        secondaryjoin='text_request_flrs.c.text_request_id==TextRequest.id',
        backref=db.backref('followers', lazy='dynamic'),
        lazy='dynamic')

    def __repr__(self):
        return f"<User {self.displayname}>"

    # Utilities
    def update_last_seen(self):
        self.last_seen = datetime.utcnow()

    def flag(self, flag, thrower):
        event = UserFlag(flag=flag, user=self, thrower=thrower)
        db.session.add(event)

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

    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}'

    def authorize(self, right):
        r = Right.query.filter_by(enum=right).first()
        if r in self.rights:
            pass
        elif r.min_rep and self.reputation >= r.min_rep:
            pass
        else:
            abort(403)

    def is_authorized(self, right):
        r = Right.query.filter_by(enum=right).first()
        return r in self.rights or (r.min_rep and self.reputation >= r.min_rep)

    def up_power(self):
        if self.reputation <= 1:
            return 1
        else:
            return int(10*log10(self.reputation))

    def down_power(self):
        if self.up_power() / 2 <= 1:
            return -1
        else:
            return -int(self.up_power()/2)

    def readable_reputation(self):
        if self.reputation >= 1000000:
            return f'{round(self.reputation/1000000)}m'
        elif self.reputation >= 1000:
            return f'{round(self.reputation/1000)}k'
        else:
            return f'{self.reputation}'

    def already_voted(self, annotation):
        return annotation in self.votes

    def get_vote(self, annotation):
        return self.voteballots.filter_by(annotation=annotation).first()

    # text request vote utilities
    def get_text_request_vote_dict(self):
        v = {}
        for vote in self.text_request_ballots:
            v[vote.text_request.id] = vote.is_up()
        return v

    def already_voted_text_request(self, text_request):
        return text_request in self.text_request_votes

    def get_text_request_vote(self, text_request):
        return self.text_request_ballots.filter(
            TextRequestVote.text_request == text_request).first()

    # tag request vote utilities
    def get_tag_request_vote_dict(self):
        v = {}
        for vote in self.tag_request_ballots:
            v[vote.tag_request.id] = vote.is_up()
        return v

    def already_voted_tag_request(self, tag_request):
        return tag_request in self.tag_request_votes

    def get_tag_request_vote(self, tag_request):
        return self.tag_request_ballots.filter(
            TagRequestVote.tag_request == tag_request).first()

    # edit vote utilities
    def get_edit_vote(self, edit):
        return self.edit_ballots.filter(annotation.EditVote.edit == edit).first()

    def get_wiki_edit_vote(self, edit):
        return self.wiki_edit_ballots.filter(WikiEditVote.edit == edit).first()


class Right(Base, EnumMixin):
    __tablename__ = 'user_right'
    id = db.Column(db.Integer, primary_key=True)
    min_rep = db.Column(db.Integer)

    def __repr__(self):
        return f'<Right to {self.enum}>'


class ReputationEnum(Base, EnumMixin):
    id = db.Column(db.Integer, primary_key=True)
    default_delta = db.Column(db.Integer, nullable=False)


class ReputationChange(Base):
    id = db.Column(db.Integer, primary_key=True)
    delta = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    enum_id = db.Column(db.Integer, db.ForeignKey('reputation_enum.id'),
                        nullable=False)

    user = db.relationship('User', backref='changes')
    type = db.relationship('ReputationEnum')

    def __repr__(self):
        return f'<rep change {self.type} on {self.user.displayname}>'


class UserFlagEnum(Base, EnumMixin):
    id = db.Column(db.Integer, primary_key=True)


class UserFlag(Base):
    id = db.Column(db.Integer, primary_key=True)
    user_flag_id = db.Column(db.Integer, db.ForeignKey('user_flag_enum.id'),
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
