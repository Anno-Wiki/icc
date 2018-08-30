import hashlib
from datetime import datetime
from app import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

####################
## User Functions ##
####################

@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(64), index = True, unique = True)
    email = db.Column(db.String(128), index = True, unique = True)
    password_hash = db.Column(db.String(128))
    
    def __repr__(self):
        return "<User {}>".format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

###########################
## Book/Author Meta Data ##
###########################

class Author(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(128), index = True)
    first_name = db.Column(db.String(128), index = True)
    last_name = db.Column(db.String(128), index = True)
    url = db.Column(db.String(128), index = True)
    birth_date = db.Column(db.Date, index = True)
    death_date = db.Column(db.Date, index = True)
    added = db.Column(db.DateTime, index = True, default = datetime.utcnow)

    def __repr__(self):
        return f"<Author: {self.name}>"

class Book(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    title = db.Column(db.String(128), index = True)
    sort_title = db.Column(db.String(128), index = True)
    url = db.Column(db.String(128), index = True)
    author_id = db.Column(db.Integer, db.ForeignKey("author.id"), index = True)
    author = db.relationship("Author", backref="books")
    summary = db.Column(db.Text)
    published = db.Column(db.Date)
    added = db.Column(db.DateTime)

    def __repr__(self):
        return f"<Book {self.id}: {self.title} by {self.author}>"


####################
## Content Models ##
####################

class Kind(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    kind = db.Column(db.String(12), index = True)

    def __repr__(self):
        return f"<k {self.id}: {self.kind}>"

class Line(db.Model):
    id = db.Column(db.Integer, primary_key = True)

    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), index = True)
    book = db.relationship("Book")

    l_num = db.Column(db.Integer, index = True)

    kind_id = db.Column(db.Integer, db.ForeignKey("kind.id"), index = True)
    kind = db.relationship("Kind", foreign_keys = [kind_id])

    bk_num = db.Column(db.Integer, index = True)
    pt_num = db.Column(db.Integer, index = True)
    ch_num = db.Column(db.Integer, index = True)

    em_status_id = db.Column(db.Integer, db.ForeignKey("kind.id"), index = True)
    em_status = db.relationship("Kind", foreign_keys = [em_status_id])

    line = db.Column(db.String(200))
    
    def __repr__(self):
        return f"<l {self.id}: {self.l_num} of {self.book.title} [{self.kind.kind}]>"

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    tag = db.Column(db.String(128), index = True)
    
    def __repr__(self):
        return f"<Tag {self.id}: {self.tag}>"

class Annotation(db.Model):
    id = db.Column(db.Integer, primary_key = True)

    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), index = True)
    book = db.relationship("Book")

    head_id = db.Column(db.Integer, db.ForeignKey("annotation_version.id"))
    HEAD = db.relationship("AnnotationVersion", foreign_keys = [head_id]) 

    weight = db.Column(db.Integer, default = 0)
    added = db.Column(db.DateTime, index = True, default = datetime.utcnow)

    edit_pending = db.Column(db.Boolean, index = True, default = False)
    
class AnnotationVersion(db.Model):
    id = db.Column(db.Integer, primary_key = True)

    approved = db.Column(db.Boolean, default = False, index = True)

    pointer_id = db.Column(db.Integer, db.ForeignKey("annotation.id"), index = True)
    pointer = db.relationship("Annotation", foreign_keys = [pointer_id]) 

    hash_id = db.Column(db.String(40), index = True)

    author_id = db.Column(db.Integer, index = True)

    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), index = True)
    book = db.relationship("Book")

    previous_id = db.Column(db.Integer, db.ForeignKey("annotation_version.id"),
            default = None)
    previous = db.relationship("AnnotationVersion")

    first_line_num = db.Column(db.Integer)
    last_line_num = db.Column(db.Integer, index=True)
    first_char_idx = db.Column(db.Integer)
    last_char_idx = db.Column(db.Integer)

    annotation = db.Column(db.Text)

    modified = db.Column(db.DateTime, index = True, default = datetime.utcnow)

    tag_1_id = db.Column(db.Integer, db.ForeignKey("tag.id"), index = True)
    tag_2_id = db.Column(db.Integer, db.ForeignKey("tag.id"), index = True)
    tag_3_id = db.Column(db.Integer, db.ForeignKey("tag.id"), index = True)
    tag_4_id = db.Column(db.Integer, db.ForeignKey("tag.id"), index = True)
    tag_5_id = db.Column(db.Integer, db.ForeignKey("tag.id"), index = True)

    tag_1 = db.relationship("Tag", foreign_keys = [tag_1_id])
    tag_2 = db.relationship("Tag", foreign_keys = [tag_2_id])
    tag_3 = db.relationship("Tag", foreign_keys = [tag_3_id])
    tag_4 = db.relationship("Tag", foreign_keys = [tag_4_id])
    tag_5 = db.relationship("Tag", foreign_keys = [tag_5_id])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        s = f"{self.author_id},{self.book_id}," \
                f"{self.first_line_num},{self.last_line_num}," \
                f"{self.first_char_idx},{self.last_char_idx}," \
                f"{self.annotation},{self.modified}," \
                f"{self.tag_1_id},{self.tag_2_id},{self.tag_3_id}," \
                f"{self.tag_4_id},{self.tag_5_id}" 
        self.hash_id = hashlib.sha1(s.encode("utf8")).hexdigest()

    def __repr__(self):
        return f"<Ann {self.id} on book {self.book.title}>"

    def get_lines(self):
        lines = Line.query.filter(Line.book_id == self.book_id,
                Line.l_num >= self.first_line_num, 
                Line.l_num <= self.last_line_num).all()
        return lines

    def get_hl(self):
        lines = self.get_lines()
        
        if self.first_line_num == self.last_line_num: 
            lines[0].line = lines[0].line[self.first_char_idx:self.last_char_idx]
        else:
            lines[0].line = lines[0].line[self.first_char_idx:]
            lines[-1].line = lines[-1].line[:self.last_char_idx]

        return lines

