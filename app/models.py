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

class L_class(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    l_class = db.Column(db.String(12), index = True)

    def __repr__(self):
        return f"<Line Class {self.id}: {self.l_class}>"


class Line(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), index = True)
    book = db.relationship("Book")
    l_num = db.Column(db.Integer, index = True)
    l_class_id = db.Column(db.Integer, db.ForeignKey("L_class.id"), index = True)
    l_class = db.relationship("L_class")
    bk_num = db.Column(db.Integer, index = True)
    pt_num = db.Column(db.Integer, index = True)
    ch_num = db.Column(db.Integer, index = True)
    line = db.Column(db.String(200))
    
    def __repr__(self):
        return f"<Line {self.id}: {self.l_num} of {self.book.title} [{self.l_class.l_class}]>"

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    tag = db.Column(db.String(128), index = True)
    
    def __repr__(self):
        return f"<Tag {self.id}: {self.tag}>"

class Annotation(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), index = True)
    book = db.relationship("Book")
    first_line_id = db.Column(db.Integer, db.ForeignKey("line.id"), index = True)
    first_line = db.relationship("Line", backref = "annotations", foreign_keys = [first_line_id])
    last_line_id = db.Column(db.Integer, db.ForeignKey("line.id"), index = True)
    last_line = db.relationship("Line", foreign_keys = [last_line_id])
    first_char_idx = db.Column(db.Integer)
    last_char_idx = db.Column(db.Integer)
    weight = db.Column(db.Integer, default = 0)
    annotation = db.Column(db.Text)

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

    def __repr__(self):
        return f"<Annotation {self.id}: {self.weight} lbs. on book {self.book.title}>"

