import jwt, inspect, sys, operator, string
from time import time
from hashlib import sha1, md5
from math import log10
from datetime import datetime

from flask import url_for, abort
from flask_login import UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from sqlalchemy.orm import backref
from sqlalchemy import or_, func, orm

from app.search import *

# please note, if this last import is not the last import you can get some weird
# errors; please keep that as last.
from app import app, db, login

# Please note, about the searchable mixin before and after commit methods, that
# if you run into a "session in committed state error" the reason is that you
# are indexing a searchable field relationship that requires the calling of sql
# to index. The answer is to make that relationship lazy="joined". I have had to
# solve this problem numerous times and I am making this comment to never
# forget.
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
                "add": list(session.new),
                "update": list(session.dirty),
                "delete": list(session.deleted)
                }

    @classmethod
    def after_commit(cls, session):
        for obj in session._changes["add"]:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes["update"]:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes["delete"]:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        session._changes = None

    @classmethod
    def reindex(cls, **kwargs):
        qry = cls.query if not kwargs else cls.query.filter_by(**kwargs)
        for obj in qry:
            add_to_index(cls.__tablename__, obj)

db.event.listen(db.session, "before_commit", SearchableMixin.before_commit)
db.event.listen(db.session, "after_commit", SearchableMixin.after_commit)

#########################
## Many-to-Many Tables ##
#########################

authors = db.Table("authors",
        db.Column("writer_id", db.Integer, db.ForeignKey("writer.id")),
        db.Column("text_id", db.Integer, db.ForeignKey("text.id")))
tags = db.Table("tags",
        db.Column("tag_id", db.Integer, db.ForeignKey("tag.id")),
        db.Column("edit_id", db.Integer, db.ForeignKey("edit.id",
            ondelete="CASCADE")))
conferred_right = db.Table("conferred_rights",
        db.Column("right_id", db.Integer, db.ForeignKey("right.id")),
        db.Column("user_id", db.Integer, db.ForeignKey("user.id")))

# followers
text_followers = db.Table("text_followers",
        db.Column("text_id", db.Integer, db.ForeignKey("text.id")),
        db.Column("user_id", db.Integer, db.ForeignKey("user.id")))
writer_followers = db.Table("writer_followers",
        db.Column("writer_id", db.Integer, db.ForeignKey("writer.id")),
        db.Column("user_id", db.Integer, db.ForeignKey("user.id")))
user_followers = db.Table("user_followers",
        db.Column("follower_id", db.Integer, db.ForeignKey("user.id")),
        db.Column("followed_id", db.Integer, db.ForeignKey("user.id")))
tag_followers = db.Table("tag_followers",
        db.Column("tag_id", db.Integer, db.ForeignKey("tag.id")),
        db.Column("user_id", db.Integer, db.ForeignKey("user.id")))
annotation_followers = db.Table("annotation_followers",
        db.Column("annotation_id", db.Integer, db.ForeignKey("annotation.id",
            ondelete="CASCADE")),
        db.Column("user_id", db.Integer, db.ForeignKey("user.id")))
tag_request_followers = db.Table("tag_request_followers",
        db.Column("tag_request_id", db.Integer, db.ForeignKey("tag_request.id",
            ondelete="CASCADE")),
        db.Column("user_id", db.Integer, db.ForeignKey("user.id")))
text_request_followers = db.Table("text_request_followers",
        db.Column("text_request_id", db.Integer,
            db.ForeignKey("text_request.id", ondelete="CASCADE")),
        db.Column("user_id", db.Integer, db.ForeignKey("user.id")))

#################
## User Models ##
#################

class Right(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    right = db.Column(db.String(128), index=True)

    def __repr__(self):
        return f"<Right to {self.right}>"

class ReputationEnum(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64))
    default_delta = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"<{self.code}>"

class ReputationChange(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    delta = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    enum_id = db.Column(db.Integer, db.ForeignKey("reputation_enum.id"),
            nullable=False)

    user = db.relationship("User", backref="changes")
    type = db.relationship("ReputationEnum")

    def __repr__(self):
        return f"<rep change {self.type} on {self.user.displayname}>"

# This is an implementation of the [notification system detailed
# here](https://stackoverflow.com/questions/9735578/building-a-notification-system)

# The type of notification is the `NotificationEnum.code`; the
# `NotificationEnum.entity_type` is a string that allows me to translate
# `NotificationObject.entity_id` into an actual query based on my `classes`
# dictionary
class NotificationEnum(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64))
    public_code = db.Column(db.String(64))
    entity_type = db.Column(db.String(64))
    notification = db.Column(db.String(255))
    vars = db.Column(db.String(255))

    def __repr__(self):
        return f"<{self.code} notification enum>"

# NotificationObject describes the actual event.
class NotificationObject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    enum_id = db.Column(db.Integer, db.ForeignKey("notification_enum.id"),
            nullable=False)
    entity_id = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow())
    actor_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    
    type = db.relationship("NotificationEnum")
    actor = db.relationship("User")

    @orm.reconstructor
    def init_on_load(self):
        self.entity = db.session.query(classes[self.type.entity_type])\
                .get(self.entity_id)

    def __repr__(self):
        return f"<Notification {self.type.code}>"

    def description(self):
        var_names = self.type.vars.split(",")
        vars = [operator.attrgetter(v)(self.entity) for v in var_names]
        return self.type.notification.format(*vars)

    @staticmethod
    def find(entity, code):
        enum = NotificationEnum.query.filter_by(code=code).first()
        return NotificationObject.query.filter(NotificationObject.type==enum,
                NotificationObject.entity_id==entity.id).first()

# The `Notification` class connects a `NotificationObject` with a user and
# whether he's seen it or not.
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    notification_object_id = db.Column(db.Integer,
            db.ForeignKey("notification_object.id", ondelete="CASCADE"),
            nullable=False)
    notifier_id = db.Column(db.Integer, db.ForeignKey("user.id"),
            nullable=False)
    seen = db.Column(db.Boolean, default=False)

    notifier = db.relationship("User",
            backref=backref("notifications", lazy="dynamic"))
    object = db.relationship("NotificationObject",
            backref=backref("notifications", lazy="dynamic",
            passive_deletes=True))

    def __repr__(self):
        return f"<{self.object.type.code} notification"\
                f" for {self.notifier.displayname}>"

    def mark_read(self):
        self.seen = True

    def mark_unread(self):
        self.seen = False

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    displayname = db.Column(db.String(64), index=True)
    email = db.Column(db.String(128), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    reputation = db.Column(db.Integer, default=0)
    locked = db.Column(db.Boolean, default=False)
    about_me = db.Column(db.Text)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    # user meta information relationships
    rights = db.relationship("Right", secondary=conferred_right,
            backref="admins")

    # annotation relationship
    annotations = db.relationship("Annotation",
            primaryjoin="and_(User.id==Annotation.annotator_id,"
            "Annotation.active==True)", lazy="dynamic")
    edits = db.relationship("Edit",
            primaryjoin="and_(User.id==Edit.editor_id,"
            "Edit.num>0)", lazy="dynamic")
    votes = db.relationship("Annotation", secondary="vote",
            primaryjoin="User.id==Vote.user_id",
            secondaryjoin="Annotation.id==Vote.annotation_id",
            backref="voters", lazy="dynamic")

    # edit relationships
    edit_ballots = db.relationship("EditVote",
            primaryjoin="User.id==EditVote.user_id", lazy="dynamic")
    edit_votes = db.relationship("Edit", secondary="edit_vote",
            primaryjoin="User.id==EditVote.user_id",
            secondaryjoin="Edit.id==EditVote.edit_id",
            backref="edit_voters", lazy="dynamic")

    # text request relationships
    text_request_ballots = db.relationship("TextRequestVote",
            primaryjoin="User.id==TextRequestVote.user_id", lazy="dynamic",
            passive_deletes=True)
    text_request_votes = db.relationship("TextRequest",
            secondary="text_request_vote",
            primaryjoin="TextRequestVote.user_id==User.id",
            secondaryjoin="TextRequestVote.text_request_id==TextRequest.id",
            backref="voters", lazy="dynamic", passive_deletes=True)

    # tag request relationships
    tag_request_ballots = db.relationship("TagRequestVote",
            primaryjoin="User.id==TagRequestVote.user_id", lazy="dynamic")
    tag_request_votes = db.relationship("TagRequest",
            secondary="tag_request_vote",
            primaryjoin="TagRequestVote.user_id==User.id",
            secondaryjoin="TagRequestVote.tag_request_id==TagRequest.id",
            backref="voters", lazy="dynamic")

    # flag relationships
    flags = db.relationship("UserFlagEnum",
            secondary="user_flag",
            primaryjoin="and_(UserFlag.user_id==User.id,"
            "UserFlag.resolver_id==None)",
            secondaryjoin="UserFlag.user_flag_id==UserFlagEnum.id",
            backref="users")
    flag_history = db.relationship("UserFlag",
            primaryjoin="UserFlag.user_id==User.id", lazy="dynamic")
    active_flags = db.relationship("UserFlag",
            primaryjoin="and_(UserFlag.user_id==User.id,"
                "UserFlag.resolver_id==None)")

    followed_users = db.relationship(
            "User", secondary=user_followers,
            primaryjoin=(user_followers.c.follower_id==id),
            secondaryjoin=(user_followers.c.followed_id==id),
            backref=db.backref("followers", lazy="dynamic"), lazy="dynamic")
    followed_texts = db.relationship("Text",
            secondary="text_followers",
            primaryjoin="text_followers.c.user_id==User.id",
            secondaryjoin="text_followers.c.text_id==Text.id",
            backref=db.backref("followers", lazy="dynamic"), lazy="dynamic")
    followed_writers = db.relationship("Writer",
            secondary="writer_followers",
            primaryjoin="writer_followers.c.user_id==User.id",
            secondaryjoin="writer_followers.c.writer_id==Writer.id",
            backref=db.backref("followers", lazy="dynamic"), lazy="dynamic")
    followed_tags = db.relationship("Tag",
            secondary="tag_followers",
            primaryjoin="tag_followers.c.user_id==User.id",
            secondaryjoin="tag_followers.c.tag_id==Tag.id",
            backref=db.backref("followers", lazy="dynamic"), lazy="dynamic")
    followed_annotations = db.relationship("Annotation",
            secondary="annotation_followers",
            primaryjoin="annotation_followers.c.user_id==User.id",
            secondaryjoin="annotation_followers.c.annotation_id==Annotation.id",
            backref=db.backref("followers", lazy="dynamic", passive_deletes=True),
            lazy="dynamic")
    followed_tag_requests = db.relationship("TagRequest",
            secondary="tag_request_followers",
            primaryjoin="tag_request_followers.c.user_id==User.id",
            secondaryjoin="tag_request_followers.c.tag_request_id==TagRequest.id",
            backref=db.backref("followers", lazy="dynamic"), lazy="dynamic")
    followed_text_requests = db.relationship("TextRequest",
            secondary="text_request_followers",
            primaryjoin="text_request_followers.c.user_id==User.id",
            secondaryjoin="text_request_followers.c.text_request_id==TextRequest.id",
            backref=db.backref("followers", lazy="dynamic"), lazy="dynamic")

    def __repr__(self):
        return "<User {}>".format(self.displayname)

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
                {"reset_password": self.id, "exp": time() + expires_in},
                app.config["SECRET_KEY"], algorithm="HS256").decode("utf-8")

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, app.config["SECRET_KEY"],
                    algorithms=["HS256"])["reset_password"]
        except:
            return
        return User.query.get(id)

    def avatar(self, size):
        digest = md5(self.email.lower().encode("utf-8")).hexdigest()
        return f"https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}"

    def authorize(self, right):
        r = Right.query.filter_by(right=right).first()
        if app.config["AUTHORIZATION"][right] == -1 and not r in self.rights:
            abort(403)
        elif self.reputation >= app.config["AUTHORIZATION"][right]:
            pass
        elif not r in self.rights:
            abort(403)

    def is_authorized(self, right):
        r = Right.query.filter_by(right=right).first()
        if app.config["AUTHORIZATION"][right] == -1:
            return r in self.rights
        else:
            return self.reputation >= app.config["AUTHORIZATION"][right]\
                    or r in self.rights

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
            return f"{round(user.reputation/1000000)}m"
        elif self.reputation >= 1000:
            return f"{round(user.reputation/1000)}k"
        else:
            return f"{self.reputation}"

    def already_voted(self, annotation):
        return annotation in self.votes

    def get_vote(self, annotation):
        return self.ballots.filter(Vote.annotation==annotation).first()
                
    def get_vote_dict(self):
        v = {}
        for vote in self.ballots:
            v[vote.annotation.id] = vote.is_up()
        return v

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
                TextRequestVote.text_request==text_request).first()

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
                TagRequestVote.tag_request==tag_request).first()

    # edit vote utilities
    def get_edit_vote(self, edit):
        return self.edit_ballots.filter(EditVote.edit==edit,
                EditVote.user==self).first()

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

##################
## Content Data ##
##################

class Writer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    last_name = db.Column(db.String(128), index=True)
    birth_date = db.Column(db.Date, index=True)
    death_date = db.Column(db.Date, index=True)
    bio = db.Column(db.Text, default="This writer has no biography yet.")
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    authored = db.relationship("Text", secondary=authors)
    edited = db.relationship("Edition",
            secondary="join(WriterEditionConnection, ConnectionEnum)",
            primaryjoin="and_(WriterEditionConnection.writer_id==Writer.id,"
            "ConnectionEnum.type=='Editor')",
            secondaryjoin="Edition.id==WriterEditionConnection.edition_id",
            backref="editors")
    translated = db.relationship("Edition",
            secondary="join(WriterEditionConnection, ConnectionEnum)",
            primaryjoin="and_(WriterEditionConnection.writer_id==Writer.id,"
            "ConnectionEnum.type=='Translator')",
            secondaryjoin="Edition.id==WriterEditionConnection.edition_id",
            backref="translators")
    annotations = db.relationship("Annotation",
            secondary="join(text,authors).join(Edition)",
            primaryjoin="Writer.id==authors.c.writer_id",
            secondaryjoin="and_(Text.id==Edition.text_id,Edition.primary==True,"
            "Annotation.edition_id==Edition.id)",
            lazy="dynamic")

    @orm.reconstructor
    def init_on_load(self):
        self.url = self.name\
                .replace(" ", "_")
        self.first_name = self.name.split(" ", 1)[0]

    def __repr__(self):
        return f"<Author: {self.name}>"

class Text(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), index=True)
    sort_title = db.Column(db.String(128), index=True)
    summary = db.Column(db.Text, default="This text has no summary yet.")
    published = db.Column(db.Date)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow())

    authors = db.relationship("Writer", secondary="authors", lazy="joined")
    editions = db.relationship("Edition", lazy="joined")
    annotations = db.relationship("Annotation", secondary="edition",
            primaryjoin="Text.id==Edition.text_id",
            secondaryjoin="and_(Annotation.edition_id==Edition.id,"
            "Annotation.active==True)", lazy="dynamic")
    primary = db.relationship("Edition",
            primaryjoin="and_(Edition.text_id==Text.id,Edition.primary==True)",
            lazy="joined", uselist=False)

    @orm.reconstructor
    def init_on_load(self):
        self.url = self.title\
                .translate(str.maketrans(dict.fromkeys(string.punctuation)))\
                .replace(" ", "_")

    def __repr__(self):
        return f"<Text {self.id}: {self.title}>"

#    def __getattr__(self, attr):
#        if attr.startswith("author_"):
#            return getattr(self.author, attr.replace("author_", "", 1))
#        else:
#            raise AttributeError(f"No such attribute {attr}")

class Edition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    num = db.Column(db.Integer, default=1)
    text_id = db.Column(db.Integer, db.ForeignKey("text.id"))
    primary = db.Column(db.Boolean, default=False)
    history = db.Column(db.Text, default="This edition has no history yet.")
    published = db.Column(db.DateTime)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow())

    text = db.relationship("Text")
    lines = db.relationship("Line", primaryjoin="Line.edition_id==Edition.id",
            lazy="dynamic")

    @orm.reconstructor
    def init_on_load(self):
        self.url = self.text.title\
                .replace(" ", "_") + f"_{self.num}"
        self.title = f"{self.text.title} Edition {self.num}*"\
                if self.primary\
                else f"{self.text.title} Edition {self.num}"

    def __repr__(self):
        return f"<Edition #{self.num} {self.text.title}>"

class WriterEditionConnection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    writer_id = db.Column(db.Integer, db.ForeignKey("writer.id"))
    edition_id = db.Column(db.Integer, db.ForeignKey("edition.id"))
    enum_id = db.Column(db.Integer, db.ForeignKey("connection_enum.id"))

    writer = db.relationship("Writer", backref="connections")
    edition = db.relationship("Edition")
    enum = db.relationship("ConnectionEnum")

    def __repr__(self):
        return f"<{self.writer.name} was {self.type.type} on {self.edition}>"

class ConnectionEnum(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(128))
    def __repr__(self):
        return f"<ConnEnum {self.type}>"

################
## Tag System ##
################

class Tag(SearchableMixin, db.Model):
    __searchable__ = ["tag", "description"]

    id = db.Column(db.Integer, primary_key=True)
    tag = db.Column(db.String(128), index=True, unique=True)
    locked = db.Column(db.Boolean, default=False)
    description = db.Column(db.Text)

    annotations = db.relationship("Annotation",
            secondary="join(tags, Edit, and_(tags.c.edit_id==Edit.id,"
            "Edit.current==True))",
            primaryjoin="Tag.id==tags.c.tag_id",
            secondaryjoin="and_(Edit.annotation_id==Annotation.id,"
            "Annotation.active==True)",
            lazy="dynamic", passive_deletes=True)

    def __repr__(self):
        return f"<Tag {self.id}: {self.tag}>"

####################
## Content Models ##
####################

class LineEnum(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(12), index=True)
    display = db.Column(db.String(64))

    def __repr__(self):
        return f"<{self.label}: {self.display}>"

class Line(SearchableMixin, db.Model):
    __searchable__ = ["line", "text_title"]
    id = db.Column(db.Integer, primary_key=True)
    edition_id = db.Column(db.Integer, db.ForeignKey("edition.id"), index=True)
    num = db.Column(db.Integer, index=True)
    label_id = db.Column(db.Integer, db.ForeignKey("line_enum.id"), index=True)
    lvl1 = db.Column(db.Integer, index=True)
    lvl2 = db.Column(db.Integer, index=True)
    lvl3 = db.Column(db.Integer, index=True)
    lvl4 = db.Column(db.Integer, index=True)
    em_id = db.Column(db.Integer, db.ForeignKey("line_enum.id"), index=True)
    line = db.Column(db.String(200))

    edition = db.relationship("Edition", lazy="joined")
    text = db.relationship("Text", secondary="edition", lazy="joined",
            uselist=False)
    label = db.relationship("LineEnum", foreign_keys=[label_id])
    em_status = db.relationship("LineEnum", foreign_keys=[em_id])
    context = db.relationship("Line",
            primaryjoin="and_(remote(Line.num)<=Line.num+1,"
            "remote(Line.num)>=Line.num-1,"
            "remote(Line.edition_id)==Line.edition_id)",
            foreign_keys=[num, edition_id], remote_side=[num, edition_id],
            uselist=True, viewonly=True)
    annotations = db.relationship("Annotation", secondary="edit",
            primaryjoin="and_(Edit.first_line_num<=foreign(Line.num),"
            "Edit.last_line_num>=foreign(Line.num),"
            "Edit.edition_id==foreign(Line.edition_id),Edit.current==True)",
            secondaryjoin="and_(foreign(Edit.annotation_id)==Annotation.id,"
            "Annotation.active==True)",
            uselist=True, foreign_keys=[num,edition_id])

    def __repr__(self):
        return f"<l{self.id}: l{self.num} {self.edition.text.title} [{self.label.display}]>"

    def __getattr__(self, attr):
        if attr.startswith("text_"):
            return getattr(self.edition.text, attr.replace("text_", "", 1))
        else:
            raise AttributeError(f"No such attribute {attr}")

    def get_prev_page(self):
        line = None
        if self.lvl4 > 1:
            line = Line.query.filter(
                    Line.edition_id==self.edition_id,
                    Line.lvl1==self.lvl1,
                    Line.lvl2==self.lvl2,
                    Line.lvl3==self.lvl3,
                    Line.lvl4==self.lvl4-1).first()
        elif self.lvl3 > 1:
            line = Line.query.filter(
                    Line.edition_id==self.edition_id,
                    Line.lvl1==self.lvl1,
                    Line.lvl2==self.lvl2,
                    Line.lvl3==self.lvl3-1)\
                        .order_by(Line.num.desc()).first()
        elif self.lvl2 > 1:
            line = Line.query.filter(
                    Line.edition_id==self.edition_id,
                    Line.lvl1==self.lvl1,
                    Line.lvl2==self.lvl2-1)\
                            .order_by(Line.num.desc()).first()
        elif self.lvl1 > 1:
            line = Line.query.filter(
                    Line.edition_id==self.edition_id,
                    Line.lvl1==self.lvl1-1)\
                            .order_by(Line.num.desc()).first()
        return line.get_url() if line else None

    def get_next_page(self):
        line = None
        lvl1 = 0
        lvl2 = 0
        lvl3 = 0
        lvl4 = 0
        if self.lvl4 != 0:
            line = Line.query.filter(
                    Line.edition_id==self.edition_id,
                    Line.lvl1==self.lvl1,
                    Line.lvl2==self.lvl2,
                    Line.lvl3==self.lvl3,
                    Line.lvl4==self.lvl4+1)\
                        .order_by(Line.num.desc()).first()
            lvl4 = 1
        if self.lvl3 != 0 and not line:
            line = Line.query.filter(
                    Line.edition_id==self.edition_id,
                    Line.lvl1==self.lvl1,
                    Line.lvl2==self.lvl2,
                    Line.lvl3==self.lvl3+1,
                    Line.lvl4==lvl4)\
                        .order_by(Line.num.desc()).first()
            lvl3 = 1
        if self.lvl2 != 0 and not line:
            line = Line.query.filter(
                    Line.edition_id==self.edition_id,
                    Line.lvl1==self.lvl1,
                    Line.lvl2==self.lvl2+1,
                    Line.lvl3==lvl3,
                    Line.lvl4==lvl4)\
                        .order_by(Line.num.desc()).first()
            lvl2 = 1
        if self.lvl1 != 0 and not line:
            line = Line.query.filter(
                    Line.edition_id==self.edition_id,
                    Line.lvl1==self.lvl1+1,
                    Line.lvl2==lvl2,
                    Line.lvl3==lvl3,
                    Line.lvl4==lvl4)\
                        .order_by(Line.num.desc()).first()
        return line.get_url() if line else None

    def get_url(self):
        lvl1 = self.lvl1 if self.lvl1 > 0 else None
        lvl2 = self.lvl2 if self.lvl2 > 0 else None
        lvl3 = self.lvl3 if self.lvl3 > 0 else None
        lvl4 = self.lvl4 if self.lvl4 > 0 else None
        return url_for("read", text_url=self.edition.text.url,
                edition_num=self.edition.num, l1=lvl1, l2=lvl2, l3=lvl3, l4=lvl4)


#################
## Annotations ##
#################

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    annotation_id = db.Column(db.Integer, 
            db.ForeignKey("annotation.id", ondelete="CASCADE"), index=True)
    reputation_change_id = db.Column(db.Integer,
            db.ForeignKey("reputation_change.id", ondelete="CASCADE"))
    delta = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow())

    user = db.relationship("User", backref=backref("ballots", lazy="dynamic"))
    annotation = db.relationship("Annotation",
            backref=backref("ballots", lazy="dynamic"))
    repchange = db.relationship("ReputationChange",
            backref=backref("vote", uselist=False))

    def __repr__(self):
        return f"<{self.user.displayname} {self.delta} on {self.annotation}>"

    def is_up(self):
        return self.delta > 0

class Annotation(SearchableMixin, db.Model):
    __searchable__ = ["text_title", "annotator_displayname", "body"]
    id = db.Column(db.Integer, primary_key=True)
    annotator_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    edition_id = db.Column(db.Integer, db.ForeignKey("edition.id"), index=True)
    weight = db.Column(db.Integer, default=0)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    locked = db.Column(db.Boolean, index=True, default=False)
    active = db.Column(db.Boolean, default=True)

    annotator = db.relationship("User", lazy="joined")
    edition = db.relationship("Edition")
    first_line = db.relationship("Line", secondary="edit",
            primaryjoin="Edit.annotation_id==Annotation.id",
            secondaryjoin="and_(Line.edition_id==Annotation.edition_id,"
            "Edit.first_line_num==Line.num)",
            uselist=False)

    text = db.relationship("Text", secondary="edition", lazy="joined",
            uselist=False)
    edition = db.relationship("Edition",
            backref=backref("annotations", lazy="dynamic"))

    # relationships to `Edit`
    HEAD = db.relationship("Edit",
            primaryjoin="and_(Edit.current==True,"
            "Edit.annotation_id==Annotation.id)", uselist=False,
            lazy="joined")

    edits = db.relationship("Edit",
            primaryjoin="and_(Edit.annotation_id==Annotation.id,"
            "Edit.approved==True)", lazy="joined", passive_deletes=True)
    history = db.relationship("Edit",
            primaryjoin="and_(Edit.annotation_id==Annotation.id,"
            "Edit.approved==True)", lazy="dynamic", passive_deletes=True)
    all_edits = db.relationship("Edit",
            primaryjoin="Edit.annotation_id==Annotation.id", lazy="dynamic",
            passive_deletes=True)
    edit_pending = db.relationship("Edit",
            primaryjoin="and_(Edit.annotation_id==Annotation.id,"
            "Edit.approved==False, Edit.rejected==False)", passive_deletes=True)

    # relationships to `Line`
    lines = db.relationship("Line", secondary="edit",
            primaryjoin="and_(Annotation.id==Edit.annotation_id,"
            "Edit.current==True)",
            secondaryjoin="and_(Line.num>=Edit.first_line_num,"
            "Line.num<=Edit.last_line_num,"
            "Line.edition_id==Annotation.edition_id)", viewonly=True,
            uselist=True)
    context = db.relationship("Line", secondary="edit",
            primaryjoin="and_(Annotation.id==Edit.annotation_id,"
            "Edit.current==True)",
            secondaryjoin="and_(Line.num>=Edit.first_line_num-5,"
            "Line.num<=Edit.last_line_num+5,"
            "Line.edition_id==Annotation.edition_id)", viewonly=True,
            uselist=True)

    # Relationships to `Flag`
    flag_history = db.relationship("AnnotationFlag",
            primaryjoin="Annotation.id==AnnotationFlag.annotation_id",
            lazy="dynamic")
    active_flags = db.relationship("AnnotationFlag",
            primaryjoin="and_(Annotation.id==AnnotationFlag.annotation_id,"
            "AnnotationFlag.resolver_id==None)", passive_deletes=True)

    def __getattr__(self, attr):
        if attr.startswith("annotator_"):
            return getattr(self.annotator, attr.replace("annotator_", "", 1))
        elif attr.startswith("text_"):
            return getattr(self.text, attr.replace("text_", "", 1))
        elif attr.startswith("body"):
            return self.HEAD.body
        else:
            raise AttributeError(f"No such attribute {attr}")

    def upvote(self, voter):
        reptype = ReputationEnum.query.filter_by(code="upvote").first()
        weight = voter.up_power()
        repchange = ReputationChange(user=self.annotator, type=reptype,
                delta=reptype.default_delta)
        vote = Vote(user=voter, annotation=self, delta=weight,
                repchange=repchange)
        self.annotator.reputation += repchange.delta
        self.weight += vote.delta
        db.session.add(vote)

    def downvote(self, voter):
        reptype = ReputationEnum.query.filter_by(code="downvote").first()
        weight = voter.down_power()
        if self.annotator.reputation + reptype.default_delta < 0:
            repdelta = -self.annotator.reputation
        else:
            repdelta = reptype.default_delta
        repchange = ReputationChange(user=self.annotator, type=reptype,
                delta=repdelta)
        vote = Vote(user=voter, annotation=self, delta=weight,
                repchange=repchange)
        self.weight += vote.delta
        self.annotator.reputation += repchange.delta
        db.session.add(vote)

    def rollback(self, vote):
        self.weight -= vote.delta
        if self.annotator.reputation - vote.repchange.delta < 0:
            delta = -self.annotator.reputation
        else:
            delta = vote.repchange.delta
        self.annotator.reputation -= delta
        db.session.delete(vote)
        db.session.delete(vote.repchange)

    def flag(self, flag, thrower):
        event = AnnotationFlag(flag=flag, annotation=self, thrower=thrower)
        db.session.add(event)

    def readable_weight(self):
        if self.weight >= 1000000 or self.weight <= -1000000:
            return f"{round(self.weight/1000000,1)}m"
        elif self.weight >= 1000 or self.weight <= -1000:
            return f"{round(self.weight/1000,1)}k"
        else:
            return f"{self.weight}"

class EditVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    edit_id = db.Column(db.Integer,
            db.ForeignKey("edit.id", ondelete="CASCADE"),
            index=True)
    delta = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow())
    reputation_change_id = db.Column(db.Integer,
            db.ForeignKey("reputation_change.id"), default=None)

    repchange = db.relationship("ReputationChange",
            backref=backref("edit_vote", uselist=False))

    user = db.relationship("User")
    edit = db.relationship("Edit",
            backref=backref("edit_ballots", lazy="dynamic", passive_deletes=True))

    def __repr__(self):
        return f"<{self.user.displayname} {self.delta} on {self.edit}>"

    def is_up(self):
        return self.delta > 0

class Edit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    editor_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    edition_id = db.Column(db.Integer, db.ForeignKey("edition.id"), index=True)
    num = db.Column(db.Integer, default=0)
    annotation_id = db.Column(db.Integer, db.ForeignKey("annotation.id",
        ondelete="CASCADE"), index=True)

    weight = db.Column(db.Integer, default=0)
    approved = db.Column(db.Boolean, default=False, index=True)
    rejected = db.Column(db.Boolean, default=False, index=True)
    current = db.Column(db.Boolean, default=False, index=True)

    hash_id = db.Column(db.String(40), index=True)

    first_line_num = db.Column(db.Integer, db.ForeignKey("line.num"))
    last_line_num = db.Column(db.Integer, db.ForeignKey("line.num"), index=True)
    first_char_idx = db.Column(db.Integer)
    last_char_idx = db.Column(db.Integer)

    body = db.Column(db.Text)
    edit_reason = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)


    editor = db.relationship("User")
    annotation = db.relationship("Annotation", foreign_keys=[annotation_id])
    previous = db.relationship("Edit",
            primaryjoin="and_(remote(Edit.annotation_id)==foreign(Edit.annotation_id),"
            "remote(Edit.num)==foreign(Edit.num-1))")
    priors = db.relationship("Edit",
            primaryjoin="and_(remote(Edit.annotation_id)==foreign(Edit.annotation_id),"
            "remote(Edit.num)<=foreign(Edit.num-1))",
            uselist=True)
    tags = db.relationship("Tag", secondary=tags, passive_deletes=True)
    lines = db.relationship("Line",
            primaryjoin="and_(Line.num>=Edit.first_line_num,"
            "Line.num<=Edit.last_line_num, Line.edition_id==Edit.edition_id)",
            uselist=True, foreign_keys=[edition_id,first_line_num,last_line_num])
    context = db.relationship("Line",
            primaryjoin="and_(Line.num>=Edit.first_line_num-5,"
            "Line.num<=Edit.last_line_num+5, Line.edition_id==Edit.edition_id)",
            uselist=True, viewonly=True,
            foreign_keys=[edition_id,first_line_num,last_line_num])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        s = f"{self.first_line_num},{self.last_line_num}," \
                f"{self.first_char_idx},{self.last_char_idx}," \
                f"{self.body},{self.tags}"
        self.hash_id = sha1(s.encode("utf8")).hexdigest()
        if self.first_line_num > self.last_line_num:
            tmp = self.last_line_num
            self.last_line_num = self.first_line_num
            self.first_line_num = tmp

    def __repr__(self):
        return f"<Ann {self.id} on {self.edition.text.title}>"

    def get_hl(self):
        lines = self.lines
        if self.first_line_num == self.last_line_num:
            lines[0].line = lines[0].line[self.first_char_idx:self.last_char_idx]
        else:
            lines[0].line = lines[0].line[self.first_char_idx:]
            lines[-1].line = lines[-1].line[:self.last_char_idx]
        return lines

    def upvote(self, voter):
        if self.weight >= app.config["MIN_EDIT_APPROVAL_RATING"]\
                or voter.is_authorized("approve_edits"):
            self.approve(voter)
        else:
            # create the repchange and the vote
            vote = EditVote(user=voter, edit=self, delta=1, repchange=None)
            db.session.add(vote)
            # apply the repchanges
            self.weight += vote.delta

    def approve(self, voter):
        # apply the approval
        self.annotation.HEAD.current = False 
        self.current = True
        self.approved = True
        # create the repchange and the vote
        reptype = ReputationEnum.query.filter_by(code="edit_approval").first()
        repchange = ReputationChange(user=self.editor, type=reptype,
                delta=reptype.default_delta)
        vote = EditVote(user=voter, edit=self, delta=1, repchange=repchange)
        db.session.add(vote, repchange)
        # apply the repchanges
        self.weight += vote.delta
        self.editor.reputation += repchange.delta
        db.session.commit()
        # create the notification object
        object = NotificationObject(entity_id=vote.id, actor=voter,
                type=NotificationEnum.query\
                        .filter_by(code="edit_approved").first())
        # notify the editor
        if not self.editor.is_authorized("immediate_edits"):
            db.session.add(Notification(object=object, notifier=self.editor))
        # notify the annotator unless he's the editor (immediate_edits) or the
        # voter
        if not self.editor == self.annotation.annotator\
                and not voter == self.annotation.annotator:
            db.session.add(Notification(object=object,
                notifier=self.annotation.annotator))
        self.notify_edit(object)

    def notify_edit(self, object):
        for follower in self.annotation.followers:
            db.session.add(Notification(object=object, notifier=follower))

    def reject(self, voter):
        vote = EditVote(user=voter, edit=self, delta=-1)
        self.weight += vote.delta
        self.rejected = True
        db.session.add(vote)
        db.session.commit()
        object = NotificationObject(entity_id=vote.id, actor=voter,
                type=NotificationEnum.query\
                        .filter_by(code="edit_rejected").first())
        if not self.editor.is_authorized("immediate_edits"):
            db.session.add(Notification(object=object, notifier=self.editor))
        # notify the annotator
        if not self.editor == self.annotation.annotator\
                and not voter == self.annotation.annotator:
            db.session.add(Notification(object=object,
                notifier=self.annotation.annotator))

    def downvote(self, voter):
        if self.weight >= app.config["MIN_EDIT_REJECTION_RATING"]\
                or voter.is_authorized("reject_edits"):
            self.reject(voter)
        else:
            # create the repchange and the vote
            vote = EditVote(user=voter, edit=self, delta=-1, repchange=None)
            db.session.add(vote)
            # apply the repchanges
            self.weight += vote.delta

####################
####################
## ## Requests ## ##
####################
####################

###################
## Book Requests ##
###################

class TextRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(127), index=True)
    authors = db.Column(db.String(127), index=True)
    weight = db.Column(db.Integer, default=0, index=True)
    approved = db.Column(db.Boolean, default=False, index=True)
    rejected = db.Column(db.Boolean, default=False, index=True)
    description = db.Column(db.Text)
    notes = db.Column(db.Text)
    wikipedia = db.Column(db.String(127), default=None)
    gutenberg = db.Column(db.String(127), default=None)
    requester_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    text_id = db.Column(db.Integer, db.ForeignKey("text.id"), index=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    requester = db.relationship("User", backref="text_requests")
    text = db.relationship("Text", backref="request")

    def __repr__(self):
        return f"<Request for {self.title}>"

    def rollback(self, vote):
        self.weight -= vote.delta
        db.session.delete(vote)

    def upvote(self, voter):
        weight = 1
        self.weight += weight
        vote = TextRequestVote(user=voter, text_request=self, delta=weight)
        db.session.add(vote)

    def downvote(self, voter):
        weight = -1
        self.weight += weight
        vote = TextRequestVote(user=voter, text_request=self, delta=weight)
        db.session.add(vote)

    def readable_weight(self):
        if self.weight >= 1000000 or self.weight <= -1000000:
            return f"{round(self.weight/1000000,1)}m"
        elif self.weight >= 1000 or self.weight <= -1000:
            return f"{round(self.weight/1000,1)}k"
        else:
            return f"{self.weight}"

    def reject(self):
        self.rejected=True

class TextRequestVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    text_request_id = db.Column(db.Integer,
            db.ForeignKey("text_request.id", ondelete="CASCADE"), index=True)
    delta = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow())

    user = db.relationship("User")
    text_request = db.relationship("TextRequest",
            backref=backref("ballots", passive_deletes=True))

    def __repr__(self):
        return f"<{self.user.displayname} {self.delta} on {self.text_request}>"

    def is_up(self):
        return self.delta > 0

##################
## Tag Requests ##
##################

class TagRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tag = db.Column(db.String(127), index=True)
    weight = db.Column(db.Integer, default=0, index=True)
    approved = db.Column(db.Boolean, default=False, index=True)
    rejected = db.Column(db.Boolean, default=False, index=True)
    tag_id = db.Column(db.Integer, db.ForeignKey("tag.id"), index=True)
    description = db.Column(db.Text)
    notes = db.Column(db.Text)
    wikipedia = db.Column(db.String(127), default=None)
    requester_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    requester = db.relationship("User", backref="tag_requests")
    created_tag = db.relationship("Tag", backref="tag_request")

    def rollback(self, vote):
        self.weight -= vote.delta
        db.session.delete(vote)

    def upvote(self, voter):
        weight = 1
        self.weight += weight
        vote = TagRequestVote(user=voter, tag_request=self, delta=weight)
        db.session.add(vote)

    def downvote(self, voter):
        weight = -1
        self.weight += weight
        vote = TagRequestVote(user=voter, tag_request=self, delta=weight)
        db.session.add(vote)

    def readable_weight(self):
        if self.weight >= 1000000 or self.weight <= -1000000:
            return f"{round(self.weight/1000000,1)}m"
        elif self.weight >= 1000 or self.weight <= -1000:
            return f"{round(self.weight/1000,1)}k"
        else:
            return f"{self.weight}"

class TagRequestVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    tag_request_id = db.Column(db.Integer,
            db.ForeignKey("tag_request.id", ondelete="CASCADE"),
            index=True)
    delta = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow())

    user = db.relationship("User")
    tag_request = db.relationship("TagRequest",
            backref=backref("ballots", passive_deletes=True))

    def __repr__(self):
        return f"<{self.user.displayname} {self.delta} on {self.annotation}>"

    def is_up(self):
        return self.delta > 0

class UserFlagEnum(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    flag = db.Column(db.String(127))

    def __repr__(self):
        return f"<UserFlagEnum {self.flag}>"

class UserFlag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_flag_id = db.Column(db.Integer, db.ForeignKey("user_flag_enum.id"),
            index=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)

    thrower_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    time_thrown = db.Column(db.DateTime, default=datetime.utcnow())

    time_resolved = db.Column(db.DateTime)
    resolver_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)

    user = db.relationship("User", foreign_keys=[user_id])
    thrower = db.relationship("User", foreign_keys=[thrower_id])
    resolver = db.relationship("User", foreign_keys=[resolver_id])

    flag = db.relationship("UserFlagEnum")

    def __repr__(self):
        if self.resolved:
            return f"<X UserFlag: {self.flag.flag} at {self.time_thrown}>"
        else:
            return f"<UserFlag thrown: {self.flag.flag} at {self.time_thrown}>"
   
    def resolve(self, resolver):
        self.time_resolved = datetime.utcnow()
        self.resolver = resolver

    def unresolve(self):
        self.time_resolved = None
        self.resolver = None

class AnnotationFlagEnum(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    flag = db.Column(db.String(127))

    def __repr__(self):
        return f"<AnnotationFlagEnum {self.flag}>"

class AnnotationFlag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    annotation_flag_id = db.Column(db.Integer,
            db.ForeignKey("annotation_flag_enum.id"), index=True)
    annotation_id = db.Column(db.Integer,
            db.ForeignKey("annotation.id", ondelete="CASCADE"), index=True)

    thrower_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    time_thrown = db.Column(db.DateTime, default=datetime.utcnow())

    time_resolved = db.Column(db.DateTime)
    resolver_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)

    annotation = db.relationship("Annotation", foreign_keys=[annotation_id])
    thrower = db.relationship("User", foreign_keys=[thrower_id])
    resolver = db.relationship("User", foreign_keys=[resolver_id])
    flag = db.relationship("AnnotationFlagEnum")

    def __repr__(self):
        if self.resolved:
            return f"<X AnnotationFlag: {self.flag.flag} at {self.time_thrown}>"
        else:
            return f"<AnnotationFlag thrown: {self.flag.flag} at" \
                        " {self.time_thrown}>"
   
    def resolve(self, resolver):
        self.time_resolved = datetime.utcnow()
        self.resolver = resolver

    def unresolve(self):
        self.time_resolved = None
        self.resolver = None

# This has to be at the end of the file.
classes = dict(inspect.getmembers(sys.modules[__name__], inspect.isclass))
