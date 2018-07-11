from datetime import datetime
from app import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash



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

@login.user_loader
def load_user(id):
    return User.query.get(int(id))




class Word(db.Model):
    # Columns
    id = db.Column(db.Integer, primary_key = True)
    word = db.Column(db.VARCHAR(128, collation="utf8mb4_bin"), unique=True, index = True)

    def __repr__(self):
        return "<Word {}>".format(self.word)

class Position(db.Model):
    # Columns
    id = db.Column(db.Integer, primary_key = True)

    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), index = True)
    book = db.relationship("Book", backref="typesetting")

    position = db.Column(db.Integer, index = True)

    word_id = db.Column(db.Integer, db.ForeignKey("word.id"), index = True)
    word = db.relationship("Word")

    number = db.Column(db.Integer, index = True)

    def __repr__(self):
        return f"<Position {self.position} of {self.book.title}: {self.word.word}>"

class Book(db.Model):
    # Columns
    id = db.Column(db.Integer, primary_key = True)
    title = db.Column(db.String(128))

    author_id = db.Column(db.Integer, db.ForeignKey("author.id"), index = True)
    author = db.relationship("Author", backref="books")

    published = db.Column(db.Date)

    ts_added = db.Column(db.DateTime, default = datetime.utcnow)

    def __repr__(self):
        return f"<Book: {self.title} by {self.author}>"

class Author(db.Model):
    # Columns
    id = db.Column(db.Integer, primary_key = True)

    name = db.Column(db.String(128), index = True)
    first_name = db.Column(db.String(128), index = True)
    last_name = db.Column(db.String(128), index = True)

    birth_date = db.Column(db.Date, index = True)
    death_date = db.Column(db.Date, index = True)

    ts_added = db.Column(db.DateTime, index = True, default = datetime.utcnow)

    def __repr__(self):
        return f"<Author: {self.name}>"
