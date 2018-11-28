import jwt
from time import time
from hashlib import sha1, md5
from math import log10 as l
from datetime import datetime
from flask_login import UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_, func
from sqlalchemy.orm import backref
from flask import url_for, abort
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
    def reindex(cls):
        for obj in cls.query:
            add_to_index(cls.__tablename__, obj)

db.event.listen(db.session, "before_commit", SearchableMixin.before_commit)
db.event.listen(db.session, "after_commit", SearchableMixin.after_commit)

############
## Tables ##
############

tags = db.Table(
        "tags",
        db.Column("tag_id", db.Integer, db.ForeignKey("tag.id")),
        db.Column("edit_id", db.Integer,
            db.ForeignKey("edit.id", ondelete="CASCADE"))
        )

conferred_right = db.Table(
        "conferred_rights",
        db.Column("right_id", db.Integer, db.ForeignKey("right.id")),
        db.Column("user_id", db.Integer, db.ForeignKey("user.id"))
        )

book_followers = db.Table(
        "book_followers",
        db.Column("book_id", db.Integer, db.ForeignKey("book.id")),
        db.Column("user_id", db.Integer, db.ForeignKey("user.id"))
        )

author_followers = db.Table(
        "author_followers",
        db.Column("author_id", db.Integer, db.ForeignKey("author.id")),
        db.Column("user_id", db.Integer, db.ForeignKey("user.id"))
        )

user_followers = db.Table(
        "user_followers",
        db.Column("follower_id", db.Integer, db.ForeignKey("user.id")),
        db.Column("followed_id", db.Integer, db.ForeignKey("user.id"))
        )

tag_followers = db.Table(
        "tag_followers",
        db.Column("tag_id", db.Integer, db.ForeignKey("tag.id")),
        db.Column("user_id", db.Integer, db.ForeignKey("user.id"))
        )

annotation_followers = db.Table(
        "annotation_followers",
        db.Column("annotation_id", db.Integer, db.ForeignKey("annotation.id",
            ondelete="CASCADE")),
        db.Column("user_id", db.Integer, db.ForeignKey("user.id"))
        )

tag_request_followers = db.Table(
        "tag_request_followers",
        db.Column("tag_request_id", db.Integer, db.ForeignKey("tag_request.id",
            ondelete="CASCADE")),
        db.Column("user_id", db.Integer, db.ForeignKey("user.id"))
        )

book_request_followers = db.Table(
        "book_request_followers",
        db.Column("book_request_id", db.Integer,
            db.ForeignKey("book_request.id", ondelete="CASCADE")),
        db.Column("user_id", db.Integer, db.ForeignKey("user.id"))
        )

####################
## User Functions ##
####################

class Right(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    right = db.Column(db.String(128), index=True)

    def __repr__(self):
        return f"<Right to {self.right}>"

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    displayname = db.Column(db.String(64), index=True)
    email = db.Column(db.String(128), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    reputation = db.Column(db.Integer, default=0)
    cumulative_negative = db.Column(db.Integer, default=0)
    cumulative_positive = db.Column(db.Integer, default=0)
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
            "Edit.edit_num>0)", lazy="dynamic")
    ballots = db.relationship("Vote", primaryjoin="User.id==Vote.user_id",
            lazy="dynamic")
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

    # book request relationships
    book_request_ballots = db.relationship("BookRequestVote",
            primaryjoin="User.id==BookRequestVote.user_id", lazy="dynamic")
    book_request_votes = db.relationship("BookRequest",
            secondary="book_request_vote",
            primaryjoin="BookRequestVote.user_id==User.id",
            secondaryjoin="BookRequestVote.book_request_id==BookRequest.id",
            backref="voters", lazy="dynamic")

    # tag request relationships
    tag_request_ballots = db.relationship("TagRequestVote",
            primaryjoin="User.id==TagRequestVote.user_id", lazy="dynamic")
    tag_request_votes = db.relationship("TagRequest",
            secondary="tag_request_vote",
            primaryjoin="TagRequestVote.user_id==User.id",
            secondaryjoin="TagRequestVote.tag_request_id==TagRequest.id",
            backref="voters", lazy="dynamic")

    # flag relationships
    flags = db.relationship("UserFlag",
            secondary="user_flag_event",
            primaryjoin="and_(UserFlagEvent.user_id==User.id,"
            "UserFlagEvent.resolved_by==None)",
            secondaryjoin="UserFlagEvent.user_flag_id==UserFlag.id",
            backref="users")
    flag_history = db.relationship("UserFlagEvent",
            primaryjoin="UserFlagEvent.user_id==User.id", lazy="dynamic")
    active_flags = db.relationship("UserFlagEvent",
            primaryjoin="and_(UserFlagEvent.user_id==User.id,"
                "UserFlagEvent.resolved_by==None)")

    # notification relationships
    notifications = db.relationship("NotificationEvent",
            primaryjoin="NotificationEvent.user_id==User.id", lazy="dynamic")
    new_notifications = db.relationship("NotificationEvent",
            primaryjoin="and_(NotificationEvent.user_id==User.id,"
            "NotificationEvent.seen==False)",
            lazy="joined")

    # followed books
    followed_books = db.relationship("Book",
            secondary="book_followers",
            primaryjoin="book_followers.c.user_id==User.id",
            secondaryjoin="book_followers.c.book_id==Book.id",
            backref="followers")

    # followed authors
    followed_authors = db.relationship("Author",
            secondary="author_followers",
            primaryjoin="author_followers.c.user_id==User.id",
            secondaryjoin="author_followers.c.author_id==Author.id",
            backref="followers")
    
    # followed users
    followed_users = db.relationship(
            "User", secondary=user_followers,
            primaryjoin=(user_followers.c.follower_id==id),
            secondaryjoin=(user_followers.c.followed_id==id),
            backref=db.backref("followers", lazy="dynamic"), lazy="dynamic")

    # followed tags
    followed_tags = db.relationship("Tag",
            secondary="tag_followers",
            primaryjoin="tag_followers.c.user_id==User.id",
            secondaryjoin="tag_followers.c.tag_id==Tag.id",
            backref="followers")

    # followed annotations
    followed_annotations = db.relationship("Annotation",
            secondary="annotation_followers",
            primaryjoin="annotation_followers.c.user_id==User.id",
            secondaryjoin="annotation_followers.c.annotation_id==Annotation.id",
            backref="followers")

    # followed tag_requests
    followed_tag_requests = db.relationship("TagRequest",
            secondary="tag_request_followers",
            primaryjoin="tag_request_followers.c.user_id==User.id",
            secondaryjoin="tag_request_followers.c.tag_request_id==TagRequest.id",
            backref="followers")

    # followed book_requests
    followed_book_requests = db.relationship("BookRequest",
            secondary="book_request_followers",
            primaryjoin="book_request_followers.c.user_id==User.id",
            secondaryjoin="book_request_followers.c.book_request_id==BookRequest.id",
            backref="followers")

    def __repr__(self):
        return "<User {}>".format(self.displayname)

    # Utilities

    def update_last_seen(self):
        self.last_seen = datetime.utcnow()

    def notify_flag(self, event):
        for f in self.followers:
            if f.has_right("resolve_user_flags") and f != event.thrower:
                f.notify("new_user_flag", 
                        url_for("user_flags", user_id=self.id), 
                        f"New \"{event.flag.flag}\" flag thrown on user "
                        f"\"{self.displayname}\"")

    def flag(self, flag, thrower):
        event = UserFlagEvent(flag=flag, user=self, thrower=thrower)
        db.session.add(event)
        self.notify_flag(event)

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

    def authorize_rep(self, min_rep):
        if self.reputation < min_rep:
            abort(403)

    def authorize_rights(self, right):
        r = Right.query.filter_by(right=right).first()
        if not r in self.rights:
            abort(403)

    def has_right(self, right):
        r = Right.query.filter_by(right=right).first()
        return r in self.rights

    def is_authorized(self, min_rep):
        return self.reputation >= min_rep

    def notify(self, notification, link, information, *args, **kwargs):
        notification_type = NotificationType.query.filter_by(code=notification).first()
        hash_string = kwargs.get("hash_string", None)
        if notification_type:
            if hash_string:
                evt = NotificationEvent(time=datetime.utcnow(),
                        notification=notification_type, user=self,
                        information=information, link=link,
                        hash_id=sha1(hash_string.encode("utf8")).hexdigest())
            else:
                evt = NotificationEvent(time=datetime.utcnow(),
                        notification=notification_type, user=self,
                        information=information, link=link)
        else:
            raise AttributeError(f"Notification type {notification} does not exist")
        db.session.add(evt)

    # Annotation utilities
    def upvote(self):
        self.reputation += 5
        self.cumulative_positive += 5

    def downvote(self):
        self.reputation -= 2
        if self.reputation <= 0:
            self.reputation = 0
        self.cumulative_negative -= 2

    def rollback_upvote(self):
        self.reputation -= 5
        if self.reputation <= 0:
            self.reputation = 0
        self.cumulative_positive -= 5

    def rollback_downvote(self):
        self.reputation += 2
        self.cumulative_negative += 2

    def up_power(self):
        if self.reputation <= 1:
            return 1
        else:
            return int(10*l(self.reputation))

    def down_power(self):
        if self.up_power() / 2 <= 1:
            return 1
        else:
            return int(self.up_power()/2)

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

    # book request vote utilities
    def get_book_request_vote_dict(self):
        v = {}
        for vote in self.book_request_ballots:
            v[vote.book_request.id] = vote.is_up()
        return v

    def already_voted_book_request(self, book_request):
        return book_request in self.book_request_votes

    def get_book_request_vote(self, book_request):
        return self.book_request_ballots.filter(
                BookRequestVote.book_request==book_request).first()

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

class Author(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    first_name = db.Column(db.String(128), index=True)
    last_name = db.Column(db.String(128), index=True)
    url = db.Column(db.String(128), index=True)
    birth_date = db.Column(db.Date, index=True)
    death_date = db.Column(db.Date, index=True)
    bio = db.Column(db.Text)
    added = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    books = db.relationship("Book", primaryjoin="Book.author_id==Author.id")
    annotations = db.relationship("Annotation", secondary="book",
            primaryjoin="Book.author_id==Author.id",
            secondaryjoin="and_(Annotation.book_id==Book.id,"
            "Annotation.active==True)", lazy="dynamic")

    def __repr__(self):
        return f"<Author: {self.name}>"

class Book(SearchableMixin, db.Model):
    __searchable__ = ["title", "author_name"]
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), index=True)
    sort_title = db.Column(db.String(128), index=True)
    url = db.Column(db.String(128), index=True)
    author_id = db.Column(db.Integer, db.ForeignKey("author.id"), index=True)
    summary = db.Column(db.Text)
    published = db.Column(db.Date)
    added = db.Column(db.DateTime)

    # we have to lazy="joined" author relationship for the sake of getattr()
    # during __searchable__ indexing because if we do not, when we access
    # author_name, we end up with an error from issuing sql after modification
    # of the book before committing. If we load it immediately, which is no skin
    # off our processor's back, we don't have to issue any sql!
    author = db.relationship("Author", lazy="joined")
    lines = db.relationship("Line", primaryjoin="Line.book_id==Book.id",
        lazy="dynamic")
    annotations = db.relationship("Annotation",
        primaryjoin="and_(Book.id==Annotation.book_id,"
        "Annotation.active==True)",
        lazy="dynamic")

    def __repr__(self):
        return f"<Book {self.id}: {self.title} by {self.author}>"

    def __getattr__(self, attr):
        if attr.startswith("author_"):
            return getattr(self.author, attr.replace("author_", "", 1))
        else:
            raise AttributeError(f"No such attribute {attr}")

################
## Tag System ##
################

class Tag(SearchableMixin, db.Model):
    __searchable__ = ["tag", "description"]

    id = db.Column(db.Integer, primary_key=True)
    tag = db.Column(db.String(128), index=True, unique=True)
    admin = db.Column(db.Boolean, default=False)
    description = db.Column(db.Text)

    annotations = db.relationship("Annotation",
            secondary="join(tags, Edit,"
            "and_(tags.c.edit_id==Edit.id,"
            "Edit.current==True))",
            primaryjoin="Tag.id==tags.c.tag_id",
            secondaryjoin="and_(Edit.annotation_id==Annotation.id,"
            "Annotation.active==True)",
            lazy="dynamic")

    def __repr__(self):
        return f"<Tag {self.id}: {self.tag}>"

####################
## Content Models ##
####################

class LineLabel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(12), index=True)
    display = db.Column(db.String(64))

    def __repr__(self):
        return f"<{self.label}: {self.display}>"

class Line(SearchableMixin, db.Model):
    __searchable__ = ["line", "book_title"]
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), index=True)
    line_num = db.Column(db.Integer, index=True)
    label_id = db.Column(db.Integer, db.ForeignKey("line_label.id"), index=True)
    lvl1 = db.Column(db.Integer, index=True)
    lvl2 = db.Column(db.Integer, index=True)
    lvl3 = db.Column(db.Integer, index=True)
    lvl4 = db.Column(db.Integer, index=True)
    em_id = db.Column(db.Integer, db.ForeignKey("line_label.id"), index=True)
    line = db.Column(db.String(200))

    book = db.relationship("Book", lazy="joined")
    label = db.relationship("LineLabel", foreign_keys=[label_id])
    em_status = db.relationship("LineLabel", foreign_keys=[em_id])
    context = db.relationship("Line",
            primaryjoin="and_(remote(Line.line_num)<=Line.line_num+1,"
                "remote(Line.line_num)>=Line.line_num-1,"
                "remote(Line.book_id)==Line.book_id)",
            foreign_keys=[line_num, book_id], remote_side=[line_num, book_id],
            uselist=True, viewonly=True)
    annotations = db.relationship("Annotation", secondary="edit",
            primaryjoin="and_(Edit.first_line_num<=foreign(Line.line_num),"
                    "Edit.last_line_num>=foreign(Line.line_num),"
                    "Edit.book_id==foreign(Line.book_id),"
                    "Edit.current==True)",
            secondaryjoin="and_(foreign(Edit.annotation_id)==Annotation.id,"
                    "Annotation.active==True)",
            uselist=True, foreign_keys=[line_num,book_id])

    def __repr__(self):
        return f"<l{self.id}: l{self.line_num} {self.book.title} [{self.label.display}]>"

    def __getattr__(self, attr):
        if attr.startswith("book_"):
            return getattr(self.book, attr.replace("book_", "", 1))
        else:
            raise AttributeError(f"No such attribute {attr}")

    def get_prev_page(self):
        line = None
        if self.lvl4 > 1:
            line = Line.query.filter(
                    Line.book_id==self.book_id,
                    Line.lvl1==self.lvl1,
                    Line.lvl2==self.lvl2,
                    Line.lvl3==self.lvl3,
                    Line.lvl4==self.lvl4-1).first()
        elif self.lvl3 > 1:
            line = Line.query.filter(
                    Line.book_id==self.book_id,
                    Line.lvl1==self.lvl1,
                    Line.lvl2==self.lvl2,
                    Line.lvl3==self.lvl3-1)\
                        .order_by(Line.line_num.desc()).first()
        elif self.lvl2 > 1:
            line = Line.query.filter(
                    Line.book_id==self.book_id,
                    Line.lvl1==self.lvl1,
                    Line.lvl2==self.lvl2-1)\
                            .order_by(Line.line_num.desc()).first()
        elif self.lvl1 > 1:
            line = Line.query.filter(
                    Line.book_id==self.book_id,
                    Line.lvl1==self.lvl1-1)\
                            .order_by(Line.line_num.desc()).first()
        return line.get_url() if line else None

    def get_next_page(self):
        line = None
        lvl1 = 0
        lvl2 = 0
        lvl3 = 0
        lvl4 = 0
        if self.lvl4 != 0:
            line = Line.query.filter(
                    Line.book_id==self.book_id,
                    Line.lvl1==self.lvl1,
                    Line.lvl2==self.lvl2,
                    Line.lvl3==self.lvl3,
                    Line.lvl4==self.lvl4+1)\
                        .order_by(Line.line_num.desc()).first()
            lvl4 = 1
        if self.lvl3 != 0 and not line:
            line = Line.query.filter(
                    Line.book_id==self.book_id,
                    Line.lvl1==self.lvl1,
                    Line.lvl2==self.lvl2,
                    Line.lvl3==self.lvl3+1,
                    Line.lvl4==lvl4)\
                        .order_by(Line.line_num.desc()).first()
            lvl3 = 1
        if self.lvl2 != 0 and not line:
            line = Line.query.filter(
                    Line.book_id==self.book_id,
                    Line.lvl1==self.lvl1,
                    Line.lvl2==self.lvl2+1,
                    Line.lvl3==lvl3,
                    Line.lvl4==lvl4)\
                        .order_by(Line.line_num.desc()).first()
            lvl2 = 1
        if self.lvl1 != 0 and not line:
            print(f"{self.lvl1+1},{lvl2},{lvl3},{lvl4}")
            line = Line.query.filter(
                    Line.book_id==self.book_id,
                    Line.lvl1==self.lvl1+1,
                    Line.lvl2==lvl2,
                    Line.lvl3==lvl3,
                    Line.lvl4==lvl4)\
                        .order_by(Line.line_num.desc()).first()
        return line.get_url() if line else None

    def get_url(self):
        lvl1 = self.lvl1 if self.lvl1 > 0 else None
        lvl2 = self.lvl2 if self.lvl2 > 0 else None
        lvl3 = self.lvl3 if self.lvl3 > 0 else None
        lvl4 = self.lvl4 if self.lvl4 > 0 else None
        return url_for("read", book_url=self.book.url, l1=lvl1,
                l2=lvl2, l3=lvl3, l4=lvl4)


#################
## Annotations ##
#################

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    annotation_id = db.Column(db.Integer, 
            db.ForeignKey("annotation.id", ondelete="CASCADE"), index=True)
    delta = db.Column(db.Integer)
    time = db.Column(db.DateTime, default=datetime.utcnow())

    user = db.relationship("User")
    annotation = db.relationship("Annotation")

    def __repr__(self):
        return f"<{self.user.id} {self.delta} on {self.annotation}>"

    def is_up(self):
        return self.delta > 0

class Annotation(SearchableMixin, db.Model):
    __searchable__ = ["book_title", "annotator_displayname", "body"]
    id = db.Column(db.Integer, primary_key=True)
    annotator_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), index=True)
    weight = db.Column(db.Integer, default=0)
    added = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    edit_pending = db.Column(db.Boolean, index=True, default=False)
    locked = db.Column(db.Boolean, index=True, default=False)
    active = db.Column(db.Boolean, default=True)

    annotator = db.relationship("User", lazy="joined")
    book = db.relationship("Book", lazy="joined")
    HEAD = db.relationship("Edit",
            primaryjoin="and_(Edit.current==True,"
            "Edit.annotation_id==Annotation.id)", uselist=False,
            lazy="joined", passive_deletes=True)
    lines = db.relationship("Line", secondary="edit",
            primaryjoin="and_(Annotation.id==Edit.annotation_id,"
                "Edit.current==True)",
            secondaryjoin="and_(Line.line_num>=Edit.first_line_num,"
                "Line.line_num<=Edit.last_line_num,"
                "Line.book_id==Edit.book_id)",
            viewonly=True, uselist=True, passive_deletes=True)
    context = db.relationship("Line", secondary="edit",
            primaryjoin="and_(Annotation.id==Edit.annotation_id,"
                "Edit.current==True)",
            secondaryjoin="and_(Line.line_num>=Edit.first_line_num-5,"
                "Line.line_num<=Edit.last_line_num+5,"
                "Line.book_id==Edit.book_id)",
            viewonly=True, uselist=True, passive_deletes=True)

    flag_history = db.relationship("AnnotationFlagEvent",
            primaryjoin="Annotation.id==AnnotationFlagEvent.annotation_id",
            lazy="dynamic")
    active_flags = db.relationship("AnnotationFlagEvent",
            primaryjoin="and_(Annotation.id==AnnotationFlagEvent.annotation_id,"
            "AnnotationFlagEvent.resolved_by==None)", passive_deletes=True)

    edits = db.relationship("Edit",
            primaryjoin="and_(Edit.annotation_id==Annotation.id,"
                "Edit.approved==True)", lazy="joined", passive_deletes=True)
    history = db.relationship("Edit",
            primaryjoin="and_(Edit.annotation_id==Annotation.id,"
                "Edit.approved==True)", lazy="dynamic", passive_deletes=True)
    all_edits = db.relationship("Edit",
            primaryjoin="Edit.annotation_id==Annotation.id", lazy="dynamic",
            passive_deletes=True)

    def __getattr__(self, attr):
        if attr.startswith("annotator_"):
            return getattr(self.annotator, attr.replace("annotator_", "", 1))
        elif attr.startswith("book_"):
            return getattr(self.book, attr.replace("book_", "", 1))
        elif attr.startswith("body"):
            return self.HEAD.body
        else:
            raise AttributeError(f"No such attribute {attr}")

    def upvote(self, voter):
        weight = voter.up_power()
        self.weight += weight
        self.annotator.upvote()
        vote = Vote(user=voter, annotation=self, delta=weight)
        hash_string = f"{vote}"
        self.annotator.notify("annotation_upvote",
                url_for("annotation", annotation_id=self.id), 
                information=f"Upvote on annotation [{self.id}] on "
                f"\"{self.book.title}\"",
                hash_string=hash_string)
        db.session.add(vote)

    def downvote(self, voter):
        weight = voter.down_power()
        weight = -weight
        self.weight += weight
        self.annotator.downvote()
        vote = Vote(user=voter, annotation=self, delta=weight)
        hash_string = f"{vote}"
        self.annotator.notify("annotation_downvote", 
                url_for("annotation", annotation_id=self.id), 
                information=f"Downvote on annotation [{self.id}] on "
                f"\"{self.book.title}\"",
                hash_string=hash_string)
        db.session.add(vote)

    def rollback(self, vote):
        self.weight -= vote.delta
        if vote.is_up():
            self.annotator.rollback_upvote()
        else:
            self.annotator.rollback_downvote()
        db.session.delete(vote)
        hash_string = f"{vote}"
        evt = NotificationEvent.query.filter_by(
                hash_id=sha1(hash_string.encode("utf8")).hexdigest()
                ).first()
        if evt:
            db.session.delete(evt)

    def flag(self, flag, thrower):
        event = AnnotationFlagEvent(flag=flag, annotation=self, thrower=thrower)
        db.session.add(event)
        self.notify_flag(event)

    def notify_lockchange(self):
        if self.locked:
            for f in self.followers:
                f.notify("annotation_locked",
                        url_for("annotation", annotation_id=self.id),
                        f"Annotation [{self.id}] on \"{self.book.title}\" "
                        "locked from further editing")
        else:
            for f in self.followers:
                f.notify("annotation_unlocked",
                        url_for("annotation", annotation_id=self.id),
                        f"Annotation [{self.id}] on \"{self.book.title}\" "
                        "unlocked for editing")

    def notify_flag(self, event):
        for f in self.followers:
            if f.has_right("resolve_annotation_flags") and f != event.thrower:
                f.notify("new_annotation_flag",
                        url_for("annotation_flags", annotation_id=self.id),
                        f"New \"{event.flag.flag}\" flag thrown on annotation "
                        f"[{self.id}]")

    def notify_edit(self, notification, editor):
        if self.annotator != editor:
            # notify the annotator his annotation has been edited
            # but only if he isn't the editor.
            self.annotator.notify("edit_approved",
                    url_for("annotation", annotation_id=self.id),
                    f"New edit on your annotation [{self.id}] on "
                    f"\"{self.book.title}\"",
                    hash_string=f"newediton{self.id}at{datetime.utcnow()}")
        # notify all the annotation's followers of a new edit.
        for follower in self.followers:
            follower.notify("edit_approved",
                    url_for("annotation", annotation_id=self.id),
                    f"New edit on followed annotation [{self.id}] on "
                    f"\"{self.book.title}\"",
                    hash_string=f"newediton{self.id}at{datetime.utcnow()}")
    
    def notify_new(self):
        # followers of the annotation's book
        for follower in self.book.followers:
            follower.notify("new_annotation",
                    url_for("annotation", annotation_id=self.id),
                    f"New annotation on followed book \"{self.book.title}\"",
                    hash_string=f"new_annotation{self.id}on{self.book.id}")
        # follower of the annotation's book's author
        for follower in self.book.author.followers:
            follower.notify("new_annotation",
                    url_for("annotation", annotation_id=self.id),
                    f"New annotation on book \"{self.book.title}\" from "
                    f"followed author \"{self.book.author.name}\"",
                    hash_string=f"new_annotation{self.id}on{self.book.id}")
        # followers of the annotator
        for follower in self.annotator.followers:
            follower.notify("new_annotation",
                    url_for("annotation", annotation_id=self.id),
                    f"New annotation from followed user "
                    f"\"{self.annotator.displayname}\"",
                    hash_string=f"new_annotation{self.id}on{self.book.id}")
        for tag in self.HEAD.tags:
            for follower in tag.followers:
                follower.notify("new_annotation",
                        url_for("annotation", annotation_id=self.id),
                        f"New annotation with followed tag \"{tag.tag}\"",
                        hash_string=f"new_annotation{self.id}on{self.book.id}")

    def notify_reputation(self):
        for follower in self.followers:
            follower.notify("annotation_upvote",
                    url_for("annotation", annotation_id=self.id),
                    f"The reputation of annotation [{self.id}] on "
                    f"\"{self.book.title}\" is now "
                    "<strong>{self.reputation}</strong>")

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
    time = db.Column(db.DateTime, default=datetime.utcnow())

    user = db.relationship("User")
    edit = db.relationship("Edit", 
            backref=backref("edit_ballots", lazy="dynamic"))

    def __repr__(self):
        return f"<{self.user.displayname} {self.delta} on {self.edit}>"

    def is_up(self):
        return self.delta > 0

class Edit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    editor_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    edit_num = db.Column(db.Integer, default=0)
    weight = db.Column(db.Integer, default=0)
    approved = db.Column(db.Boolean, default=False, index=True)
    rejected = db.Column(db.Boolean, default=False, index=True)
    annotation_id = db.Column(db.Integer,
            db.ForeignKey("annotation.id", ondelete="CASCADE"), index=True)
    hash_id = db.Column(db.String(40), index=True)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), index=True)
    first_line_num = db.Column(db.Integer, db.ForeignKey("line.line_num"))
    last_line_num = db.Column(db.Integer, db.ForeignKey("line.line_num"), index=True)
    first_char_idx = db.Column(db.Integer)
    last_char_idx = db.Column(db.Integer)
    body = db.Column(db.Text)
    modified = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    current = db.Column(db.Boolean, default=False, index=True)
    edit_reason = db.Column(db.String(255))

    editor = db.relationship("User")
    annotation = db.relationship("Annotation", foreign_keys=[annotation_id])
    book = db.relationship("Book")
    previous = db.relationship("Edit",
            primaryjoin="and_(remote(Edit.annotation_id)==foreign(Edit.annotation_id),"
            "remote(Edit.edit_num)==foreign(Edit.edit_num-1))")
    priors = db.relationship("Edit",
            primaryjoin="and_(remote(Edit.annotation_id)==foreign(Edit.annotation_id),"
            "remote(Edit.edit_num)<=foreign(Edit.edit_num-1))",
            uselist=True)

    tags = db.relationship("Tag", secondary=tags)

    lines = db.relationship("Line",
        primaryjoin="and_(Line.line_num>=Edit.first_line_num,"
            "Line.line_num<=Edit.last_line_num,"
            "Line.book_id==Edit.book_id)",
            viewonly=True, uselist=True)
    context = db.relationship("Line",
        primaryjoin="and_(Line.line_num>=Edit.first_line_num-5,"
            "Line.line_num<=Edit.last_line_num+5,"
            "Line.book_id==Edit.book_id)",
            foreign_keys=[first_line_num,last_line_num],
            viewonly=True, uselist=True)

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
        return f"<Ann {self.id} on book {self.book.title}>"

    def get_hl(self):
        lines = self.lines
        if self.first_line_num == self.last_line_num:
            lines[0].line = lines[0].line[self.first_char_idx:self.last_char_idx]
        else:
            lines[0].line = lines[0].line[self.first_char_idx:]
            lines[-1].line = lines[-1].line[:self.last_char_idx]

        return lines

    def approve(self, voter):
        self.weight += 1
        vote = EditVote(user=voter, edit=self, delta=1)
        db.session.add(vote)

    def reject(self, voter):
        self.weight -= 1
        vote = EditVote(user=voter, edit=self, delta=-1)
        db.session.add(vote)

    def notify_edit(self, notification):
        if notification == "approved":
            # notify the editor
            self.editor.notify("edit_approved",
                    url_for("annotation", annotation_id=self.annotation_id),
                    f"Edit #{self.edit_num} on annotation [{self.annotation_id}]"
                    " approved.",
                    hash_string=f"edit_approved{self.id}on{self.annotation_id}")
            # notify all the editor's followers
            for follower in self.editor.followers:
                follower.notify("edit_approved",
                        url_for("annotation", annotation_id=self.annotation_id),
                        f"New edit approved from followed user"
                        f" \"{self.editor.displayname}\"",
                        hash_string=f"edit_approved{self.id}on{self.annotation_id}")
            # notify the annotation's followers
            self.annotation.notify_edit("approved", self.editor)
        elif notification == "rejected":
            # if it's rejected, only notify the editor.
            self.editor.notify("edit_rejected",
                    url_for("annotation", annotation_id=self.annotation_id),
                    f"Edit #{self.edit_num} on annotation [{self.annotation_id}]"
                    " rejected",
                    hash_string=f"edit_rejected{self.id}on{self.annotation_id}")

####################
####################
## ## Requests ## ##
####################
####################

###################
## Book Requests ##
###################

class BookRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(127), index=True)
    author = db.Column(db.String(127), index=True)
    weight = db.Column(db.Integer, default=0, index=True)
    approved = db.Column(db.Boolean, default=False, index=True)
    rejected = db.Column(db.Boolean, default=False, index=True)
    description = db.Column(db.Text)
    notes = db.Column(db.Text)
    wikipedia = db.Column(db.String(127), default=None)
    gutenberg = db.Column(db.String(127), default=None)
    requester_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), index=True)
    requested = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    requester = db.relationship("User", backref="book_requests")
    book = db.relationship("Book", backref="request")

    def __repr__(self):
        return f"<Request for {self.title}>"

    def rollback(self, vote):
        self.weight -= vote.delta
        db.session.delete(vote)

    def upvote(self, voter):
        weight = 1
        self.weight += weight
        vote = BookRequestVote(user=voter, book_request=self, delta=weight)
        db.session.add(vote)
        if self.weight % 25 == 0:
            self.notify()

    def downvote(self, voter):
        weight = -1
        self.weight += weight
        vote = BookRequestVote(user=voter, book_request=self, delta=weight)
        db.session.add(vote)
        if self.weight % 25 == 0:
            self.notify()

    def readable_weight(self):
        if self.weight >= 1000000 or self.weight <= -1000000:
            return f"{round(self.weight/1000000,1)}m"
        elif self.weight >= 1000 or self.weight <= -1000:
            return f"{round(self.weight/1000,1)}k"
        else:
            return f"{self.weight}"

    def notify(self):
        for follower in self.followers:
            if self.weight > 0:
                follower.notify("annotation_upvote",
                        url_for("view_book_request", book_request_id=self.id),
                        f"Followed book request for \"{self.title}\" now has"
                        f" <strong>{self.weight}</strong> upvotes.")
            elif self.weight < 0:
                follower.notify("annotation_downvote",
                        url_for("view_book_request", book_request_id=self.id),
                        f"Followed book request for \"{self.title}\"     now has"
                        f" <strong>{self.weight}</strong> downvotes.")

    def notify_approval(self):
        for follower in self.followers:
            follower.notify("book_approved",
                    url_for("view_book_request", book_request_id=self.id),
                    f"The book request for \"{self.title}\" has been approved.")

    def reject(self):
        self.rejected=True
        for follower in self.followers:
            follower.notify("book_approved",
                    url_for("view_book_request", book_request_id=self.id),
                    f"The book request for \"{self.title}\" has been approved.")

    def notify_added(self):
        if self.book_id:
            for follower in self.followers:
                follower.notify("book_added",
                        url_for("book", book_url=self.book.url),
                        f"The book \"{self.book.title}\" has been added to the "
                        "library.")
        else:
            print("C'mon, dude, get it together: link the book_request object"
                    "to the book, _then_ send the notification.")

class BookRequestVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    book_request_id = db.Column(db.Integer,
            db.ForeignKey("book_request.id", ondelete="CASCADE"), index=True)
    delta = db.Column(db.Integer)
    time = db.Column(db.DateTime, default=datetime.utcnow())

    user = db.relationship("User")
    book_request = db.relationship("BookRequest")

    def __repr__(self):
        return f"<{self.user.displayname} {self.delta} on {self.book_request}>"

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
    requested = db.Column(db.DateTime, index=True, default=datetime.utcnow)

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
        if self.weight % 25 == 0:
            self.notify()

    def downvote(self, voter):
        weight = -1
        self.weight += weight
        vote = TagRequestVote(user=voter, tag_request=self, delta=weight)
        db.session.add(vote)
        if self.weight % 25 == 0:
            self.notify()

    def notify(self):
        for follower in self.followers:
            if self.weight > 0:
                follower.notify("annotation_upvote",
                        url_for("view_tag_request", tag_request_id=self.id),
                        f"Followed tag request for <tag>{self.tag}</tag> now "
                        f"has <strong>{self.weight}</strong> upvotes.")
            elif self.weight < 0:
                follower.notify("annotation_downvote",
                        url_for("view_tag_request", tag_request_id=self.id),
                        f"Followed tag request for <tag>{self.tag}</tag> now "
                        f"has <strong>{self.weight}</strong> downvotes.")

    def readable_weight(self):
        if self.weight >= 1000000 or self.weight <= -1000000:
            return f"{round(self.weight/1000000,1)}m"
        elif self.weight >= 1000 or self.weight <= -1000:
            return f"{round(self.weight/1000,1)}k"
        else:
            return f"{self.weight}"

    def notify_approval(self):
        for follower in self.followers:
            follower.notify("tag_approved",
                    url_for("tag", tag=self.tag),
                    f"The tag request for <tag>{self.tag}</tag> "
                    "has been approved.")

    def notify_rejection(self):
        for follower in self.followers:
            follower.notify("tag_rejected",
                    url_for("tag_request", tag_request_id=self.id),
                    f"The tag request for <tag>{self.tag}</tag> "
                    "has been rejected.")

class TagRequestVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    tag_request_id = db.Column(db.Integer,
            db.ForeignKey("tag_request.id", ondelete="CASCADE"),
            index=True)
    delta = db.Column(db.Integer)
    time = db.Column(db.DateTime, default=datetime.utcnow())

    user = db.relationship("User")
    tag_request = db.relationship("TagRequest")

    def __repr__(self):
        return f"<{self.user.displayname} {self.delta} on {self.annotation}>"

    def is_up(self):
        return self.delta > 0

class UserFlag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    flag = db.Column(db.String(127))

    def __repr__(self):
        return f"<UserFlag {self.flag}>"

class UserFlagEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_flag_id = db.Column(db.Integer, db.ForeignKey("user_flag.id"),
            index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    thrower_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    time_thrown = db.Column(db.DateTime, default=datetime.utcnow())
    resolved = db.Column(db.DateTime)
    resolved_by = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)

    user = db.relationship("User", foreign_keys=[user_id])
    thrower = db.relationship("User", foreign_keys=[thrower_id])
    flag = db.relationship("UserFlag")
    resolver = db.relationship("User", foreign_keys=[resolved_by])

    def __repr__(self):
        if self.resolved:
            return f"<X UserFlag: {self.flag.flag} at {self.time_thrown}>"
        else:
            return f"<UserFlag thrown: {self.flag.flag} at {self.time_thrown}>"
   
    def resolve(self, resolver):
        self.resolved = datetime.utcnow()
        self.resolver = resolver

    def unresolve(self):
        self.resolved = None
        self.resolver = None

class AnnotationFlag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    flag = db.Column(db.String(127))

    def __repr__(self):
        return f"<AnnotationFlag {self.flag}>"

class AnnotationFlagEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    annotation_flag_id = db.Column(db.Integer,
            db.ForeignKey("annotation_flag.id"), index=True)
    annotation_id = db.Column(db.Integer,
            db.ForeignKey("annotation.id", ondelete="CASCADE"), index=True)
    thrower_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    time_thrown = db.Column(db.DateTime, default=datetime.utcnow())
    resolved = db.Column(db.DateTime)
    resolved_by = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)

    annotation = db.relationship("Annotation", foreign_keys=[annotation_id])
    thrower = db.relationship("User", foreign_keys=[thrower_id])
    flag = db.relationship("AnnotationFlag")
    resolver = db.relationship("User", foreign_keys=[resolved_by])

    def __repr__(self):
        if self.resolved:
            return f"<X AnnotationFlag: {self.flag.flag} at {self.time_thrown}>"
        else:
            return f"<AnnotationFlag thrown: {self.flag.flag} at" \
                        " {self.time_thrown}>"
   
    def resolve(self, resolver):
        self.resolved = datetime.utcnow()
        self.resolver = resolver

    def unresolve(self):
        self.resolved = None
        self.resolver = None

##################
## Notifactions ##
##################

class NotificationType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), index=True)
    description = db.Column(db.String(64))

    def __repr__(self):
        return f"<Notification {self.code}>"

class NotificationEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    time = db.Column(db.DateTime, default=datetime.utcnow())
    notification_id = db.Column(db.Integer, db.ForeignKey("notification_type.id"))
    seen = db.Column(db.Boolean, default=False)
    seen_on = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    information = db.Column(db.Text)
    hash_id = db.Column(db.String(128))
    link = db.Column(db.String(128))

    notification = db.relationship("NotificationType",
            foreign_keys=[notification_id])
    user = db.relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<{self.notification.event} for {self.user} on {self.time}>"

    def mark_read(self):
        self.seen = True
        self.seen_on = datetime.utcnow()
    
    def mark_unread(self):
        self.seen = False
        self.seen_on = None
