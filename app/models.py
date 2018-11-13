import jwt
from time import time
from hashlib import sha1, md5
from math import log10 as l
from datetime import datetime
from flask_login import UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import app, db, login
from sqlalchemy import or_, func
from sqlalchemy.orm import backref
from flask import url_for, abort
from app.search import *

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
                db.case(when, value=cls.id)), total

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
        db.Column("annotation_version_id", db.Integer,
            db.ForeignKey("annotation_version.id"))
        )

conferred_right = db.Table(
        "conferred_rights",
        db.Column("right_id", db.Integer, db.ForeignKey("admin_right.id")),
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
        db.Column("annotation_id", db.Integer, db.ForeignKey("annotation.id")),
        db.Column("user_id", db.Integer, db.ForeignKey("user.id"))
        )


####################
## User Functions ##
####################

class AdminRight(db.Model):
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
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    # user meta information relationships
    rights = db.relationship("AdminRight", secondary=conferred_right,
            backref="admins")

    # annotation relationship
    annotations = db.relationship("Annotation",
            primaryjoin="and_(User.id==Annotation.author_id,"
            "Annotation.active==True)", lazy="dynamic")
    ballots = db.relationship("Vote", primaryjoin="User.id==Vote.user_id",
            lazy="dynamic")
    votes = db.relationship("Annotation", secondary="vote",
            primaryjoin="User.id==Vote.user_id",
            secondaryjoin="Annotation.id==Vote.annotation_id",
            backref="voters", lazy="dynamic")

    # edit relationships
    edit_ballots = db.relationship("EditVote",
            primaryjoin="User.id==EditVote.user_id", lazy="dynamic")
    edit_votes = db.relationship("AnnotationVersion", secondary="edit_vote",
            primaryjoin="User.id==EditVote.user_id",
            secondaryjoin="AnnotationVersion.id==EditVote.edit_id",
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

    # annotation watchers
    followed_annotations = db.relationship("Annotation",
            secondary="annotation_followers",
            primaryjoin="annotation_followers.c.user_id==User.id",
            secondaryjoin="annotation_followers.c.annotation_id==Annotation.id",
            backref="followers")

    def __repr__(self):
        return "<User {}>".format(self.displayname)

    # Utilities

    def update_last_seen(self):
        self.last_seen = datetime.utcnow()
        db.session.commit()

    def flag(self, flag, thrower):
        event = UserFlagEvent(flag=flag, user=self, thrower=thrower)
        db.session.add(event)
        db.session.commit()

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
        r = AdminRight.query.filter_by(right=right).first()
        if not r in self.rights:
            abort(403)

    def has_right(self, right):
        r = AdminRight.query.filter_by(right=right).first()
        return r in self.rights

    def is_authorized(self, min_rep):
        return self.reputation >= min_rep

    def notify(self, notification, link, hash_string, information):
        notification_type = NotificationType.query.filter_by(code=notification).first()
        if notification_type:
            evt = NotificationEvent(time=datetime.utcnow(),
                    notification=notification_type, user=self,
                    information=information, link=link,
                    hash_id=sha1(hash_string.encode("utf8")).hexdigest())
        else:
            raise AttributeError(f"Notification type {notification} does not exist")
        db.session.add(evt)
        db.session.commit()

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
            secondary="join(tags, AnnotationVersion,"
            "and_(tags.c.annotation_version_id==AnnotationVersion.id,"
            "AnnotationVersion.current==True))",
            primaryjoin="Tag.id==tags.c.tag_id",
            secondaryjoin="and_(AnnotationVersion.pointer_id==Annotation.id,"
            "Annotation.active==True)",
            lazy="dynamic")

    def __repr__(self):
        return f"<Tag {self.id}: {self.tag}>"

####################
## Content Models ##
####################

class Kind(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(12), index=True)

    def __repr__(self):
        return f"<k {self.id}: {self.kind}>"

class Line(db.Model):
    __searchable__ = ["line", "book_title"]
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), index=True)
    l_num = db.Column(db.Integer, index=True)
    kind_id = db.Column(db.Integer, db.ForeignKey("kind.id"), index=True)
    bk_num = db.Column(db.Integer, index=True)
    pt_num = db.Column(db.Integer, index=True)
    ch_num = db.Column(db.Integer, index=True)
    em_status_id = db.Column(db.Integer, db.ForeignKey("kind.id"), index=True)
    line = db.Column(db.String(200))

    book = db.relationship("Book")
    kind = db.relationship("Kind", foreign_keys=[kind_id])
    em_status = db.relationship("Kind", foreign_keys=[em_status_id])

    def __repr__(self):
        return f"<l {self.id}: {self.l_num} of {self.book.title} [{self.kind.kind}]>"

    def __getattr__(self, attr):
        if attr.startswith("book_"):
            return getattr(self.book, attr.replace("book_", "", 1))
        else:
            raise AttributeError(f"No such attribute {attr}")

    def get_prev_section(self):     # cleverer than expected
        if self.ch_num != 0:        # decrementing by chapters
            lines = Line.query.filter(Line.book_id==self.book_id,
                    Line.l_num<self.l_num).order_by(Line.l_num.desc()
                            ).limit(10).all()
            for l in lines:         # go backwards through lines
                if l.ch_num != 0:   # the 1st time ch_num != 0, return it
                    return l
        elif self.pt_num != 0:      # decrementing by parts
            lines = Line.query.filter(Line.book_id==self.book_id,
                    Line.ch_num==0, Line.l_num<self.l_num
                    ).order_by(Line.l_num.desc()).limit(10).all()
            for l in lines:
                if l.pt_num != 0:
                    return l
        else:                       # decrementing by books
            lines = Line.query.filter(Line.book_id==self.book_id,
                    Line.ch_num==0, Line.pt_num==0, Line.l_num<self.l_num
                    ).order_by(Line.l_num.desc()).limit(10).all()
            for l in lines:
                if l.bk_num != 0:
                    return l
        return None                 # there is no previous section

    def get_next_section(self):
        if self.ch_num != 0:
            lines = Line.query.filter(Line.book_id==self.book_id,
                    Line.l_num>self.l_num
                    ).order_by(Line.l_num.asc()).limit(10).all()
            for l in lines:
                if l.ch_num != 0:
                    return l
        elif self.pt_num != 0:
            lines = Line.query.filter(Line.book_id==self.book_id,
                    Line.ch_num==0, Line.l_num>self.l_num
                    ).order_by(Line.l_num.asc()).limit(10).all()
            for l in lines:
                if l.pt_num != 0:
                    return l
        else:
            lines = Line.query.filter(Line.book_id==self.book_id,
                    Line.ch_num==0, Line.pt_num==0, Line.l_num>self.l_num
                    ).order_by(Line.l_num.asc()).limit(10).all()
            for l in lines:
                if l.bk_num != 0:
                    return l
        return None

    def get_url(self):
        bk = self.bk_num if self.bk_num > 0 else None
        pt = self.pt_num if self.pt_num > 0 else None
        ch = self.ch_num if self.ch_num > 0 else None
        return url_for("read", book_url=self.book.url, book=bk,
                part=pt, chapter=ch)


#################
## Annotations ##
#################

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    annotation_id = db.Column(db.Integer, db.ForeignKey("annotation.id"),
            index=True)
    delta = db.Column(db.Integer)
    time = db.Column(db.DateTime, default=datetime.utcnow())

    user = db.relationship("User")
    annotation = db.relationship("Annotation")

    def __repr__(self):
        return f"<{self.user.id} {self.delta} on {self.annotation}>"

    def is_up(self):
        return self.delta > 0

class Annotation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), index=True)
    weight = db.Column(db.Integer, default=0)
    added = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    edit_pending = db.Column(db.Boolean, index=True, default=False)
    locked = db.Column(db.Boolean, index=True, default=False)
    active = db.Column(db.Boolean, default=True)

    author = db.relationship("User")
    book = db.relationship("Book")
    HEAD = db.relationship("AnnotationVersion",
            primaryjoin="and_(AnnotationVersion.current==True,"
            "AnnotationVersion.pointer_id==Annotation.id)", uselist=False)
    lines = db.relationship("Line", secondary="annotation_version",
            primaryjoin="and_(Annotation.id==AnnotationVersion.pointer_id,"
                "AnnotationVersion.current==True)",
            secondaryjoin="and_(Line.l_num>=AnnotationVersion.first_line_num,"
                "Line.l_num<=AnnotationVersion.last_line_num,"
                "Line.book_id==AnnotationVersion.book_id)",
            viewonly=True, uselist=True)
    context = db.relationship("Line", secondary="annotation_version",
            primaryjoin="and_(Annotation.id==AnnotationVersion.pointer_id,"
                "AnnotationVersion.current==True)",
            secondaryjoin="and_(Line.l_num>=AnnotationVersion.first_line_num-5,"
                "Line.l_num<=AnnotationVersion.last_line_num+5,"
                "Line.book_id==AnnotationVersion.book_id)",
            viewonly=True, uselist=True)
    flag_history = db.relationship("AnnotationFlagEvent",
            primaryjoin="Annotation.id==AnnotationFlagEvent.annotation_id",
            lazy="dynamic")
    active_flags = db.relationship("AnnotationFlagEvent",
            primaryjoin="and_(Annotation.id==AnnotationFlagEvent.annotation_id,"
            "AnnotationFlagEvent.resolved_by==None)")
    edits = db.relationship("AnnotationVersion",
            primaryjoin="and_(AnnotationVersion.pointer_id==Annotation.id,"
                "AnnotationVersion.approved==True)")
    history = db.relationship("AnnotationVersion",
            primaryjoin="and_(AnnotationVersion.pointer_id==Annotation.id,"
                "AnnotationVersion.approved==True)", lazy="dynamic")

    def upvote(self, voter):
        weight = voter.up_power()
        self.weight += weight
        self.author.upvote()
        vote = Vote(user=voter, annotation=self, delta=weight)
        hash_string = f"{vote}"
        self.author.notify("upvote",
                url_for("annotation", annotation_id=self.id), hash_string,
                information=f"Upvote on annotation {self.id} on {self.book.title}")
        db.session.add(vote)

    def downvote(self, voter):
        weight = voter.down_power()
        weight = -weight
        self.weight += weight
        self.author.downvote()
        vote = Vote(user=voter, annotation=self, delta=weight)
        hash_string = f"{vote}"
        self.author.notify("downvote", 
                url_for("annotation", annotation_id=self.id), hash_string,
                information=f"Downvote on annotation {self.id} on {self.book.title}")
        db.session.add(vote)

    def rollback(self, vote):
        self.weight -= vote.delta
        if vote.is_up():
            self.author.rollback_upvote()
        else:
            self.author.rollback_downvote()
        db.session.delete(vote)
        hash_string = f"{vote}"
        evt = NotificationEvent.query.filter_by(
                hash_id=sha1(hash_string.encode("utf8")).hexdigest()
                ).first()
        if evt:
            db.session.delete(evt)

    def get_history(self):
        history_list = []
        edit = self.HEAD.previous
        while edit.previous != None:
            history_list.append(edit)
            edit = edit.previous
        history_list.append(edit)
        history = {}
        i = len(history_list)
        for edit in history_list:
            history[i] = edit
            i -= 1
        return history

    def flag(self, flag, thrower):
        event = AnnotationFlagEvent(flag=flag, annotation=self, thrower=thrower)
        db.session.add(event)
        db.session.commit()

    def notify_edit(self, notification, editor):
        if self.author != editor:
            # notify the author his annotation has been edited
            # but only if he isn't the editor.
            self.author.notify("edit_approved",
                    url_for("annotation", annotation_id=self.id),
                    f"newediton{self.id}at{datetime.utcnow()}",
                    f"New edit on your annotation {self.id} on {self.book.title}.")
        # notify all the annotation's followers of a new edit.
        for follower in self.followers:
            follower.notify("edit_approved",
                    url_for("annotation", annotation_id=self.id),
                    f"newediton{self.id}at{datetime.utcnow()}",
                    f"New edit on followed annotation {self.id} on {self.book.title}.")
    
    def notify_new(self):
        # followers of the annotation's book
        for follower in self.book.followers:
            follower.notify("new_annotation",
                    url_for("annotation", annotation_id=self.id),
                    f"new_annotation{self.id}on{self.book.id}",
                    f"New annotation on followed book {self.book.title}.")
        # follower of the annotation's book's author
        for follower in self.book.author.followers:
            follower.notify("new_annotation",
                    url_for("annotation", annotation_id=self.id),
                    f"new_annotation{self.id}on{self.book.id}",
                    f"New annotation on book {self.book.title} from followed"
                    f" author {self.book.author.name}.")
        # followers of the annotator
        for follower in self.author.followers:
            follower.notify("new_annotation",
                    url_for("annotation", annotation_id=self.id),
                    f"new_annotation{self.id}on{self.book.id}",
                    f"New annotation from followed annotator"
                    f" {self.author.displayname}.")
        for tag in self.HEAD.tags:
            for follower in tag.followers:
                follower.notify("new_annotation",
                        url_for("annotation", annotation_id=self.id),
                        f"new_annotation{self.id}on{self.book.id}",
                        f"New annotation using followed tag {tag.tag}.")

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
    edit_id = db.Column(db.Integer, db.ForeignKey("annotation_version.id"),
            index=True)
    delta = db.Column(db.Integer)
    time = db.Column(db.DateTime, default=datetime.utcnow())

    user = db.relationship("User")
    edit = db.relationship("AnnotationVersion", 
            backref=backref("edit_ballots", lazy="dynamic"))

    def __repr__(self):
        return f"<{self.user.displayname} {self.delta} on {self.edit}>"

    def is_up(self):
        return self.delta > 0

class AnnotationVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    editor_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    edit_num = db.Column(db.Integer, default=0)
    weight = db.Column(db.Integer, default=0)
    approved = db.Column(db.Boolean, default=False, index=True)
    rejected = db.Column(db.Boolean, default=False, index=True)
    pointer_id = db.Column(db.Integer, db.ForeignKey("annotation.id"), index=True)
    hash_id = db.Column(db.String(40), index=True)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), index=True)
    previous_id = db.Column(db.Integer, db.ForeignKey("annotation_version.id"),
            default=None)
    first_line_num = db.Column(db.Integer, db.ForeignKey("line.l_num"))
    last_line_num = db.Column(db.Integer, db.ForeignKey("line.l_num"), index=True)
    first_char_idx = db.Column(db.Integer)
    last_char_idx = db.Column(db.Integer)
    annotation = db.Column(db.Text)
    modified = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    current = db.Column(db.Boolean, default=False, index=True)
    edit_reason = db.Column(db.String(255))

    editor = db.relationship("User")
    pointer = db.relationship("Annotation", foreign_keys=[pointer_id])
    book = db.relationship("Book")
    previous = db.relationship("AnnotationVersion", remote_side=[id])

    tags = db.relationship("Tag", secondary=tags)

    lines = db.relationship("Line",
        primaryjoin="and_(Line.l_num>=AnnotationVersion.first_line_num,"
            "Line.l_num<=AnnotationVersion.last_line_num,"
            "Line.book_id==AnnotationVersion.book_id)",
            viewonly=True, uselist=True)
    context = db.relationship("Line",
        primaryjoin="and_(Line.l_num>=AnnotationVersion.first_line_num-5,"
            "Line.l_num<=AnnotationVersion.last_line_num+5,"
            "Line.book_id==AnnotationVersion.book_id)",
            foreign_keys=[first_line_num,last_line_num],
            viewonly=True, uselist=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        s = f"{self.book}," \
                f"{self.first_line_num},{self.last_line_num}," \
                f"{self.first_char_idx},{self.last_char_idx}," \
                f"{self.annotation},{self.tags}"
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
                    url_for("annotation", annotation_id=self.pointer_id),
                    f"edit_approved{self.id}on{self.pointer_id}",
                    f"Edit {self.id} on annotation {self.pointer_id} approved.")
            # notify all the editor's followers
            for follower in self.editor.followers:
                follower.notify("edit_approved",
                        url_for("annotation", annotation_id=self.pointer_id),
                        f"edit_approved{self.id}on{self.pointer_id}",
                        f"New edit approved from followed annotatior"
                        f" {self.editor.displayname}.")
            # notify the annotation's followers
            self.pointer.notify_edit("approved", self.editor)
        elif notification == "rejected":
            # if it's rejected, only notify the editor.
            self.editor.notify("edit_rejected",
                    url_for("annotation", annotation_id=self.pointer_id),
                    f"edit_rejected{self.id}on{self.pointer_id}",
                    f"Edit {self.id} on annotation {self.pointer_id} rejected.")

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

    def downvote(self, voter):
        weight = -1
        self.weight += weight
        vote = BookRequestVote(user=voter, book_request=self, delta=weight)
        db.session.add(vote)

class BookRequestVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    book_request_id = db.Column(db.Integer, db.ForeignKey("book_request.id"),
            index=True)
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

    def downvote(self, voter):
        weight = -1
        self.weight += weight
        vote = TagRequestVote(user=voter, tag_request=self, delta=weight)
        db.session.add(vote)

class TagRequestVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    tag_request_id = db.Column(db.Integer, db.ForeignKey("tag_request.id"),
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
    annotation_id = db.Column(db.Integer, db.ForeignKey("annotation.id"),
            index=True)
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
