import hashlib
from math import log10 as l
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import app, db, login
from sqlalchemy import or_, func
from flask import url_for, abort


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

####################
## User Functions ##
####################

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(128), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    reputation = db.Column(db.Integer, default=0)
    cumulative_negative = db.Column(db.Integer, default=0)
    cumulative_positive = db.Column(db.Integer, default=0)
    locked = db.Column(db.Boolean, default=False)

    annotations = db.relationship("Annotation",
        primaryjoin="and_(User.id==Annotation.author_id,"
        "Annotation.active==True)", lazy="dynamic")
    ballots = db.relationship("Vote", primaryjoin="User.id==Vote.user_id",
            lazy="dynamic")
    votes = db.relationship("Annotation", secondary="vote",
            primaryjoin="User.id==Vote.user_id",
            secondaryjoin="Annotation.id==Vote.annotation_id",
            backref="voters", lazy="dynamic")
    edit_votes = db.relationship("AnnotationVersion", secondary="edit_vote",
            primaryjoin="User.id==EditVote.user_id",
            secondaryjoin="AnnotationVersion.id==EditVote.edit_id",
            backref="edit_voters", lazy="dynamic")
    rights = db.relationship("AdminRight", secondary=conferred_right,
            backref="admins")



    def __repr__(self):
        return "<User {}>".format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def upvote(self):
        self.reputation += 5
        self.cumulative_positive += 5

    def rollback_upvote(self):
        self.reputation -= 5
        if self.reputation <= 0:
            self.reputation = 0
        self.cumulative_positive -= 5

    def downvote(self):
        self.reputation -= 2
        if self.reputation <= 0:
            self.reputation = 0
        self.cumulative_negative -= 2

    def rollback_downvote(self):
        self.reputation += 2
        self.cumulative_negative += 2

    def already_voted(self, annotation):
        return annotation in self.votes

    def get_vote(self, annotation):
        return self.ballots.filter(Vote.annotation==annotation).first()
                

    def get_vote_dict(self):
        v = {}
        for vote in self.ballots:
            v[vote.annotation.id] = vote.is_up()
        return v

    def get_edit_vote(self, edit):
        return self.edit_votes.filter(EditVote.edit==edit,
                EditVote.user==self).first()

    def up_power(self):
        if self.reputation <= 10:
            return 1
        elif self.reputation == 10**int(l(self.reputation)):
            log = int(l(self.reputation) - (l(11) - int(l(11))))
            return int(self.reputation / 10**log) + 10*log - 10
        log = int(l(self.reputation))
        return int(self.reputation / 10**log) + 10*log - 10

    def down_power(self):
        if self.reputation <= 10:
            return 1
        return round(self.up_power() / 2)

    def authorize_rep(self, min_rep):
        if self.reputation < min_rep:
            abort(403)

    def authorize_rights(self, right):
        r = AdminRight.query.filter_by(right=right).first()
        if not r:
            abort(403)

    def has_right(self, right):
        r = AdminRight.query.filter_by(right=right).first()
        return r in self.rights

    def is_authorized(self, min_rep):
        return self.reputation >= min_rep

@login.user_loader
def load_user(id):
    return User.query.get(int(id))


###########
## Votes ##
###########

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    annotation_id = db.Column(db.Integer, db.ForeignKey("annotation.id"),
            index=True)
    delta = db.Column(db.Integer)

    user = db.relationship("User")
    annotation = db.relationship("Annotation")

    def __repr__(self):
        return f"<{self.user.username} {self.delta} on {self.annotation}>"

    def is_up(self):
        return self.delta > 0

class EditVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    edit_id = db.Column(db.Integer, db.ForeignKey("annotation_version.id"),
            index=True)
    delta = db.Column(db.Integer)

    user = db.relationship("User", backref="edit_ballots")
    edit = db.relationship("AnnotationVersion", backref="edit_ballots")

    def __repr__(self):
        return f"<{self.user.username} {self.delta} on {self.edit}>"

    def is_up(self):
        return self.delta > 0


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

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), index=True)
    sort_title = db.Column(db.String(128), index=True)
    url = db.Column(db.String(128), index=True)
    author_id = db.Column(db.Integer, db.ForeignKey("author.id"), index=True)
    summary = db.Column(db.Text)
    published = db.Column(db.Date)
    added = db.Column(db.DateTime)

    author = db.relationship("Author")
    lines = db.relationship("Line", primaryjoin="Line.book_id==Book.id",
        lazy="dynamic")
    annotations = db.relationship("Annotation",
        primaryjoin="and_(Book.id==Annotation.book_id, Annotation.active==True)",
        lazy="dynamic")

    def __repr__(self):
        return f"<Book {self.id}: {self.title} by {self.author}>"

###################
## Site Metadata ##
###################

class Kind(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(12), index=True)

    def __repr__(self):
        return f"<k {self.id}: {self.kind}>"

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tag = db.Column(db.String(128), index=True, unique=True)
    admin = db.Column(db.Boolean, default=False)
    description = db.Column(db.Text)

    annotations = db.relationship("Annotation",
            secondary="join(AnnotationVersion, tags,"
                "AnnotationVersion.id==tags.c.annotation_version_id)",
            primaryjoin="Tag.id==tags.c.tag_id",
            secondaryjoin="Annotation.head_id==AnnotationVersion.id",
            lazy="dynamic")

    def __repr__(self):
        return f"<Tag {self.id}: {self.tag}>"

class AdminRight(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    right = db.Column(db.String(128), index=True)

    def __repr__(self):
        return self.right

####################
## Content Models ##
####################

class Line(db.Model):
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

class Annotation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), index=True)
    head_id = db.Column(db.Integer, db.ForeignKey("annotation_version.id"))
    weight = db.Column(db.Integer, default=0)
    added = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    edit_pending = db.Column(db.Boolean, index=True, default=False)
    locked = db.Column(db.Boolean, index=True, default=False)
    active = db.Column(db.Boolean, default=True)

    author = db.relationship("User")
    book = db.relationship("Book")
    HEAD = db.relationship("AnnotationVersion", foreign_keys=[head_id])
#    tags = db.relationship("Tag", secondary="annotation_version",
#            primaryjoin="Annotation.head_id==AnnotationVersion.id",
#            secondaryjoin="or_(Tag.id==AnnotationVersion.tag_1_id,"
#            "Tag.id==AnnotationVersion.tag_2_id,"
#            "Tag.id==AnnotationVersion.tag_3_id,"
#            "Tag.id==AnnotationVersion.tag_4_id,"
#            "Tag.id==AnnotationVersion.tag_5_id)")
    lines = db.relationship("Line", secondary="annotation_version",
        primaryjoin="Annotation.head_id==AnnotationVersion.id",
        secondaryjoin="and_(Line.l_num>=AnnotationVersion.first_line_num,"
            "Line.l_num<=AnnotationVersion.last_line_num,"
            "Line.book_id==AnnotationVersion.book_id)", viewonly=True,
            uselist=True)

    def upvote(self, voter):
        weight = voter.up_power()
        self.weight += weight
        self.author.upvote()
        vote = Vote(user=voter, annotation=self, delta=weight)
        db.session.add(vote)

    def downvote(self, voter):
        weight = voter.down_power()
        weight = -weight
        self.weight += weight
        self.author.downvote()
        vote = Vote(user=voter, annotation=self, delta=weight)
        db.session.add(vote)

    def rollback(self, vote):
        self.weight -= vote.delta
        if vote.is_up():
            self.author.rollback_upvote()
        else:
            self.author.rollback_downvote()
        db.session.delete(vote)

class AnnotationVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    editor_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        s = f"{self.book}," \
                f"{self.first_line_num},{self.last_line_num}," \
                f"{self.first_char_idx},{self.last_char_idx}," \
                f"{self.annotation},{self.tags}"
        print(s)
        self.hash_id = hashlib.sha1(s.encode("utf8")).hexdigest()

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
