from flask import render_template, flash, redirect, url_for, request, Markup
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from app import app, db
from app.forms import LoginForm, RegistrationForm, PageNumberForm, AnnotationForm
from app.models import User, Book, Author, Line, L_class, Annotation
from sqlalchemy import func
import math


#######################
## General Utilities ##
#######################

linesperpage = 30;
# The line has is dangling with an open <em>, close it.
def opened(line):
    if line.count('<em>') > line.count('</em>'):
        return True
    else:
        return False

# The line
def closed(line):
    if line.count('</em>') > line.count('<em>'):
        return True
    else:
        return False


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

#############
## Indexes ##
#############

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
    form = PageNumberForm()
    last_page = math.ceil(Line.query.filter_by(book_id = book.id).paginate(
        1, 30, True).total / 30)
    
    if form.validate_on_submit():
        pg = form.page_num.data
        if pg <= last_page and pg >= 1:
            return redirect(url_for('book_page', title=book.url, page_num = pg))
    return render_template('book.html', title = book.title, book = book,
            form = form, last_page = last_page)

####################
## Reading Routes ##
####################

@app.route('/book/<title>/read')
@app.route('/books/<title>/read')
def read(title):
    book = Book.query.filter_by(url = title).first_or_404()

    lines = Line.query.filter_by(book_id = book.id).all()

    annotations = Annotation.query.filter_by(book_id = book.id).all()

    us = False
    lem = False
    for i, line in enumerate(lines):
        # This fails. I need to convert it to char level iteration because the
        # index changes and throws off multiple annotations.
        for anno in annotations:
            if anno.last_line_id == line.id:
                lines[i].line = line.line[:anno.last_char_idx] + \
                    f'<sup><a href="#a{anno.id}">[a{anno.id}]</a></sup>' + \
                    line.line[anno.last_char_idx:]
        if '_' in line.line:
            newline = []
            for c in line.line:
                if c == '_':
                    if us:
                        newline.append('</em>')
                        us = False
                    else:
                        newline.append('<em>')
                        us = True
                else:
                    newline.append(c)
            lines[i].line = ''.join(newline)
        
        if opened(lines[i].line):
            lines[i].line = lines[i].line + '</em>'
            lem = True
        elif closed(lines[i].line):
            lines[i].line = '<em>' + lines[i].line
            lem = False
        elif lem:
            lines[i].line = '<em>' + lines[i].line + '</em>'

    return render_template('read.html', 
            book = book, author = book.author,
            title = book.title, 
            linesperpage = linesperpage, 
            lines = lines, page_num = 0,
            annotations = annotations)

# This route is fundamentally screwed up for the following reason: In order to
# process underscores into <em> tags we have to iterate through every character
# in every line with underscores in order to flip on and off us as to whether us
# is running. Then we have to use a line level flag (I might be wrong about this
# but it works) in order to ensure when a _..._ spans multiple lines we properly
# close and open and buttress lines with <em> and </em> tags. But this only
# works for one page. There's no way, to my mind, to keep track of em's past a
# single page with my current data model. Therefore this code is commented out
# until I can imporove it to track that. I might just need add a new "oem" and
# "cem" field to my line model. Until then, this stays closed and we operate on
# the book (and eventually heierarchical chapter) level
    
#@app.route('/book/<title>/page<page_num>/read', methods=['GET', 'POST'])
#@app.route('/books/<title>/page<page_num>/read', methods=['GET', 'POST'])
#def read_page(title, page_num):
#    book = Book.query.filter_by(url = title).first_or_404()
#
#    lines = Line.query.filter_by(book_id = book.id).paginate(
#            int(page_num), linesperpage, True)
#
#    next_page = url_for('read_page', title = title, page_num = lines.next_num) \
#            if lines.has_next else None
#
#    prev_page = url_for('read_page', title = title, page_num = lines.prev_num) \
#            if lines.has_prev else None
#
#    annotations = Annotation.query.filter_by(book_id = book.id).all()
#
#    us = False
#    lem = False
#    for i, line in enumerate(lines.items):
#        for anno in annotations:
#            if anno.last_line_id == line.id:
#                lines.items[i].line = line.line[:anno.last_char_idx] + \
#                    f'<sup><a href="#a{anno.id}">[a{anno.id}]</a></sup>' + \
#                    line.line[anno.last_char_idx:]
#        if '_' in line.line:
#            newline = []
#            for c in line.line:
#                if c == '_':
#                    if us:
#                        newline.append('</em>')
#                        us = False
#                    else:
#                        newline.append('<em>')
#                        us = True
#                else:
#                    newline.append(c)
#            lines.items[i].line = ''.join(newline)
#        
#        if opened(lines.items[i].line):
#            lines.items[i].line = lines.items[i].line + '</em>'
#            lem = True
#        elif closed(lines.items[i].line):
#            lines.items[i].line = '<em>' + lines.items[i].line
#            lem = False
#        elif lem:
#            lines.items[i].line = '<em>' + lines.items[i].line + '</em>'
#
#    return render_template('read_page.html', 
#            book = book, author = book.author,
#            title = book.title + f" p. {page_num}", 
#            prev_page = prev_page, next_page = next_page, 
#            linesperpage = linesperpage, 
#            page_num = int(page_num), lines = lines.items,
#            annotations = annotations)


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
        return redirect(url_for('create', title=book.url))
    else:
        form.annotation.data = "Type your annotation here."

    return render_template('create.html', title = book.title, form = form,
            book = book, author = book.author, lines = lines)

