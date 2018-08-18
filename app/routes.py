import math
from collections import defaultdict
from flask import render_template, flash, redirect, url_for, request, Markup
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from sqlalchemy import func
from app import app, db
from app.models import User, Book, Author, Line, L_class, Annotation
from app.forms import LoginForm, RegistrationForm
from app.forms import AnnotationForm, LineNumberForm
from app.funky import opened, closed, ahash, preplines

###########
## Index ##
###########

@app.route('/')
@app.route('/index/')
def index():
    books = Book.query.all()
    authors = Author.query.all()
    return render_template('index.html', title='Home', books = books, 
            authors = authors)

####################
## User Functions ##
####################

@app.route('/login/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))

        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')

        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')

        return redirect(next_page)

    return render_template('login.html', title='Sign In', form=form)

@app.route('/logout/')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register/', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = RegistrationForm()

    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))

    return render_template('register.html', title='Register', form=form)

@app.route('/author/<name>/')
@app.route('/authors/<name>/')
def author(name):
    author = Author.query.filter_by(url = name).first_or_404()
    books = Book.query.filter_by(author_id = author.id).order_by(Book.sort_title)
    return render_template('author.html', books = books, author = author,
            title = author.name)

#####################
## Content Indexes ##
#####################

@app.route('/author/')
@app.route('/authors/')
def author_index():
    authors = Author.query.order_by(Author.last_name).all()
    return render_template('author_index.html', authors=authors,
            title='Authors')

@app.route('/book/')
@app.route('/books/')
def book_index():
    books = Book.query.order_by(Book.sort_title).all()
    return render_template('book_index.html', books=books, title='Books')


@app.route('/book/<title>/', methods=['GET', 'POST'])
@app.route('/books/<title>/', methods=['GET', 'POST'])
def book(title):
    book = Book.query.filter_by(url = title).first_or_404()
    return render_template('book.html', title = book.title, book = book)



####################
## Reading Routes ##
####################

@app.route('/book/<title>/read')
@app.route('/books/<title>/read')
def read(title):
    book = Book.query.filter_by(url = title).first_or_404()
    lines = Line.query.filter_by(book_id = book.id).all()
    annotations = Annotation.query.filter(
            Annotation.book_id == book.id).order_by(
            Annotation.last_line_id.asc(),
            Annotation.last_char_idx.desc()).all()
    form = LineNumberForm()

    annos = defaultdict(list)
    for a in annotations:
        annos[a.last_line_id].append(a)

    preplines(lines, annos)

    return render_template('read.html', title = book.title, form = form,
            book = book, lines = lines, annotations = annotations)



#####################
## Creation Routes ##
#####################

@app.route('/book/<title>/create', methods=['GET', 'POST'])
@app.route('/books/<title>/create', methods=['GET', 'POST'])
def create(title):
    book = Book.query.filter_by(url = title).first_or_404()
    lines = Line.query.filter_by(book_id = book.id).all()
    form = AnnotationForm()

    if form.validate_on_submit():
        anno = Annotation(book_id = book.id, 
                first_line_id = form.first_line.data,
                last_line_id = form.last_line.data,
                first_char_idx = form.first_char_idx.data,
                last_char_idx = form.last_char_idx.data,
                annotation = form.annotation.data)
        db.session.add(anno)
        db.session.commit()
        flash('Annotation Submitted')
        return redirect(url_for('read', title=book.url))
    else:
        form.annotation.data = "Type your annotation here."
        form.first_char_idx.data = 0
        form.last_char_idx.data = 0

    return render_template('create.html', title = book.title, form = form,
            book = book, lines = lines)
