from flask import render_template, flash, redirect, url_for, request, Markup
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from app import app, db
from app.forms import LoginForm, RegistrationForm
from app.models import User, Book, Author, Word, Position


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

@app.route('/book/<title>')
def book(title):
    book = Book.query.filter_by(url = title).first()
    start = 617
    stop = 1464
    typesetting = Position.query.filter(Position.book_id == book.id, 
            Position.position >= start, Position.position <= stop)
#    typesetting = Position.query.filter_by(book_id = book.id).all()
#    results = typesetting.paginate(1,500).items
    return render_template('book.html', typesetting = typesetting, book =
            book, author = book.author, title = book.title)
