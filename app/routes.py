from flask import render_template, flash, redirect, url_for, request, Markup
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from app import app, db
from app.forms import LoginForm, RegistrationForm
from app.models import User, Book, Author, Word, Position, Page


@app.route('/')
@app.route('/index/')
def index():
    books = Book.query.all()
    return render_template('index.html', title='Home', books = books)


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

@app.route('/book/<title>/')
def book(title):
    book = Book.query.filter_by(url = title).first()
    pages = Page.query.filter(Page.book_id == book.id, 
            Page.ident == '<page>').all()
    chapters = Page.query.filter(Page.book_id == book.id,
            Page.ident == '<ch>').all()
    return render_template('book.html', book = book, pages = pages,
            chapters = chapters, author = book.author)

@app.route('/book/<title>/page<page_num>/')
def book_page(title, page_num):
    book = Book.query.filter_by(url = title).first()
    if page_num:
        page = Page.query.filter(Page.page_number == page_num, 
                Page.book_id == book.id, Page.ident == '<page>').first()
    typesetting = Position.query.filter(Position.book_id == book.id,
            Position.position >= page.start_id, 
            Position.position <= page.stop_id)
    return render_template('book_page.html', typesetting = typesetting, book =
            book, author = book.author, title = book.title)
