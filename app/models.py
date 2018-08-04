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
        return f"<Book: {self.title} by {self.author}>"


####################
## Content Models ##
####################

class Lclass(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    l_class = db.Column(db.String(12), index = True)

    def __repr__(self):
        return f"<Line Class: {lclass}>"


class Line(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), index = True)
    book = db.relationship("Book")
    l_num = db.Column(db.Integer, index = True)
    l_class_id = db.Column(db.Integer, db.ForeignKey("lclass.id"), index = True)
    l_class = db.relationship("Lclass")
    bk_num = db.Column(db.Integer, index = True)
    pt_num = db.Column(db.Integer, index = True)
    ch_num = db.Column(db.Integer, index = True)
    line = db.Column(db.String(200))
    
    def __repr__(self):
        return f"<Line: {self.id} of {self.book.title} [{self.l_class.l_class}]>"


