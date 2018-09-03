from collections import defaultdict
import hashlib
from flask import render_template, flash, redirect, url_for, request, Markup, \
        abort
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from sqlalchemy import or_
from app import app, db
from app.models import User, Book, Author, Line, Kind, Annotation, \
        AnnotationVersion, Tag
from app.forms import LoginForm, RegistrationForm, AnnotationForm, \
        LineNumberForm
from app.funky import preplines, is_empty, proc_tag


###########
## Index ##
###########

@app.route("/")
@app.route("/index/")
def index():
    annotations = Annotation.query.order_by(Annotation.added.desc()).all()
    return render_template("index.html", title="Home", annotations=annotations)


####################
## User Functions ##
####################

@app.route("/login/", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user is None or not user.check_password(form.password.data):
            flash("Invalid username or password")
            return redirect(url_for("login"))

        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get("next")

        if not next_page or url_parse(next_page).netloc != "":
            next_page = url_for("index")

        return redirect(next_page)

    return render_template("login.html", title="Sign In", form=form)


@app.route("/logout/")
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/register/", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    form = RegistrationForm()

    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Congratulations, you are now a registered user!")
        return redirect(url_for("login"))

    return render_template("register.html", title="Register", form=form)


@app.route("/user/<user_id>/")
def user(user_id):
    user = User.query.filter_by(id = user_id).first_or_404()
    return render_template("user.html", title=user.username, user=user)


#####################
## Content Indexes ##
#####################

@app.route("/authors/")
def author_index():
    authors = Author.query.order_by(Author.last_name)
    return render_template("author_index.html", title="Authors",
            authors=authors)


@app.route("/authors/<name>/")
def author(name):
    author = Author.query.filter_by(url=name).first_or_404()
    return render_template("author.html", title=author.name, author=author)


@app.route("/books/")
def book_index():
    books = Book.query.order_by(Book.sort_title)
    return render_template("book_index.html", title="Books", books=books)


@app.route("/books/<book_url>/", methods=["GET", "POST"])
def book(book_url):
    book = Book.query.filter_by(url=book_url).first_or_404()

    # get the kinds for each heierarchical chapter level
    bk_kind = Kind.query.filter_by(kind="bk").first()
    pt_kind = Kind.query.filter_by(kind="pt").first()
    ch_kind = Kind.query.filter_by(kind="ch").first()

    # get all the heierarchical chapter lines
    heierarchy = Line.query.filter(or_(Line.kind==bk_kind,
        Line.kind==pt_kind, Line.kind==ch_kind)).all()

    return render_template("book.html", title=book.title, book=book,
            heierarchy=heierarchy)


####################
## Reading Routes ##
####################

@app.route("/read/<book_url>/", methods=["GET", "POST"])
def read(book_url):
    form = LineNumberForm()

    if form.validate_on_submit():
        return redirect(url_for("annotate", book_url=book_url,
            first_line=form.first_line.data, last_line=form.last_line.data))

    book = Book.query.filter_by(url=book_url).first_or_404()
    lines = book.lines
    annotations = book.annotations

    # index all of the annotations by their last line number
    annotations_idx = defaultdict(list)
    for a in annotations:
        annotations_idx[a.HEAD.last_line_num].append(a)

    # insert the [n] annotation in each line (to be changed)
    preplines(lines, annotations_idx)

    # get a dictionary of all the annotations and the vote on each for the
    # current user to be used to show vote status on each annotation
    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None

    return render_template("read.html", title=book.title, form=form, book=book,
            lines=lines, annotations=annotations, uservotes=uservotes)


# unfortunately, this one is a lot more complicated than simple read.
@app.route("/read/<book_url>/<level>/<number>/", methods=["GET", "POST"])
def read_section(book_url, level, number):
    number = int(number) # convert number to int for transparency
    form = LineNumberForm()

    # initialize next and prev pages
    next_page = None
    prev_page = None

    if form.validate_on_submit():
        # redirect to annotate page, with next query param being the current
        # page. Multi-layered nested return statement. Read carefully.
        return redirect(url_for("annotate", book_url=book_url,
            first_line=form.first_line.data, last_line=form.last_line.data,
            next=url_for("read_section", book_url=book_url, level=level,
                number=number)
                )
            )

    # c'mon joker, there is no 0 page, even if I am a programmer.
    if int(number) < 1:
        abort(404)

    book = Book.query.filter_by(url=book_url).first_or_404()

    # because we have to access one of three different fields based on the
    # heierarchical level, we have to test for the level instead of just passing
    # it to the query as a variable.
    if level == "bk":
        lines = Line.query.filter(Line.book_id==book.id, Line.bk_num==number
                ).all()
    elif level == "pt":
        lines = Line.query.filter(Line.book_id==book.id, Line.pt_num==number
                ).all()
    elif level == "ch":
        lines = Line.query.filter(Line.book_id==book.id, Line.ch_num==number
                ).all()
    elif level == "pg":
        lines = Line.query.filter_by(book_id=book.id).paginate(int(number),
                app.config["LINES_PER_PAGE"], False)

        # to build the next_page url I have first to test for has_next
        next_page = url_for("read_section", book_url=book.url, level="pg",
                number=lines.next_num) if lines.has_next else None

        # then I can cash lines out to the actual lines
        lines = lines.items

    else:
        # this is not the level you are looking for.
        abort(404)

    if len(lines) <= 0:
        # the section you requested didn't actually exist (you must have typed
        # it into the url bar like some kind of a weirdo)
        abort(404)

    # the next_page url is already built for pg by now. 
    # if it's not pg a pg you're reading, build it.
    if level != "pg":
        # get the last section based on level being read
        sections = Line.query.filter(Line.book_id==book.id,
                Line.kind==Kind.query.filter_by(kind=level).first()
                ).order_by(Line.l_num.desc()).first()
        # cash it out to the actual number based on one of those three fields
        if level == "bk":
            sections = sections.bk_num
        elif level =="pt":
            sections = sections.pt_num
        elif level == "ch":
            sections = sections.ch_num
        # now that it's cashed out, if it's not too big, build the next url
        if number + 1 <= sections:
            next_page = url_for("read_section", book_url=book_url, level=level,
                    number=number+1)

    # if it's not the first page, build a previous url
    if number > 1:
        prev_page = url_for("read_section", book_url=book_url,
                level=level, number=number-1)

    # get all the annotations
    annotations = book.annotations

    # index the annotations in a dictionary
    annotations_idx = defaultdict(list)
    for a in annotations:
        annotations_idx[a.HEAD.last_line_num].append(a)

    # call the annotator
    preplines(lines, annotations_idx)

    # to darken up/down voted annotations
    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None

    return render_template("read.html", title=book.title, form=form, book=book,
            lines=lines, annotations=annotations, uservotes=uservotes,
            next_page=next_page, prev_page=prev_page)


@app.route("/view/<annotation_id>")
def view_annotation(annotation_id):
    annotation = Annotation.query.filter_by(id=annotation_id).first_or_404()
    lines = annotation.HEAD.get_lines() # we call it now to query it later
    return render_template("annotation.html", title=annotation.book.title,
            annotation=annotation, lines=lines)


#####################
## Creation Routes ##
#####################

@app.route("/edit/<anno_id>", methods=["GET", "POST"])
@login_required
def edit(anno_id):
    annotation = Annotation.query.filter_by(id=anno_id).first_or_404()
    lines = annotation.HEAD.get_lines()
    form = AnnotationForm()

    if form.cancel.data:
        next_page = request.args.get("next")
        if not next_page or url_parse(next_page).netloc != "":
            next_page = url_for("read", book_url=annotation.book.book_url)
        return redirect(next_page)

    elif form.validate_on_submit():
        tag1 = proc_tag(form.tag_1.data) if not is_empty(form.tag_1.data) else None
        tag2 = proc_tag(form.tag_2.data) if not is_empty(form.tag_2.data) else None
        tag3 = proc_tag(form.tag_3.data) if not is_empty(form.tag_3.data) else None
        tag4 = proc_tag(form.tag_4.data) if not is_empty(form.tag_4.data) else None
        tag5 = proc_tag(form.tag_5.data) if not is_empty(form.tag_5.data) else None

        anno = AnnotationVersion(book_id=annotation.HEAD.book.id,
                editor_id=current_user.id, pointer_id=anno_id,
                previous_id=annotation.HEAD.id,
                first_line_num=form.first_line.data,
                last_line_num=form.last_line.data,
                first_char_idx=form.first_char_idx.data,
                last_char_idx=form.last_char_idx.data,
                annotation=form.annotation.data,
                tag_1=tag1, tag_2=tag2, tag_3=tag3, tag_4=tag4, tag_5=tag5)

        annotation.edit_pending = True
        db.session.add(anno)
        db.session.commit()
        flash("Edit submitted for review.")

        next_page = request.args.get("next")
        if not next_page or url_parse(next_page).netloc != "":
            next_page = url_for("read", book_url=annotation.book.book_url)
        return redirect(next_page)

    elif not annotation.edit_pending:
        tag1 = annotation.HEAD.tag_1.tag if annotation.HEAD.tag_1 else None
        tag2 = annotation.HEAD.tag_2.tag if annotation.HEAD.tag_2 else None
        tag3 = annotation.HEAD.tag_3.tag if annotation.HEAD.tag_3 else None
        tag4 = annotation.HEAD.tag_4.tag if annotation.HEAD.tag_4 else None
        tag5 = annotation.HEAD.tag_5.tag if annotation.HEAD.tag_5 else None
        form.first_line.data = annotation.HEAD.first_line_num
        form.last_line.data = annotation.HEAD.last_line_num
        form.first_char_idx.data = annotation.HEAD.first_char_idx
        form.last_char_idx.data = annotation.HEAD.last_char_idx
        form.annotation.data = annotation.HEAD.annotation
        form.tag_1.data = tag1
        form.tag_2.data = tag2
        form.tag_3.data = tag3
        form.tag_4.data = tag4
        form.tag_5.data = tag5

    return render_template("annotate.html", title=annotation.HEAD.book.title,
            form=form, book=annotation.HEAD.book, lines=lines,
            annotation=annotation)


@app.route("/annotate/<book_url>/<first_line>/<last_line>/",
        methods=["GET", "POST"])
@login_required
def annotate(book_url, first_line, last_line):
    if int(first_line) > int(last_line):
        tmp = first_line
        first_line = last_line
        last_line = tmp

    book = Book.query.filter_by(url = book_url).first_or_404()
    lines = Line.query.filter(Line.book_id==book.id, Line.l_num>=first_line,
            Line.l_num<=last_line).all()
    form = AnnotationForm()

    tag1 = None
    tag2 = None
    tag3 = None
    tag4 = None
    tag5 = None

    if form.cancel.data:
        next_page = request.args.get("next")
        if not next_page or url_parse(next_page).netloc != "":
            next_page = url_for("read", book_url=book_url)
        return redirect(next_page)

    elif form.validate_on_submit():

        # Process all the tags as sqlalchemy objects if the form isn't empty
        tag1 = proc_tag(form.tag_1.data) if not is_empty(form.tag_1.data) else None
        tag2 = proc_tag(form.tag_2.data) if not is_empty(form.tag_2.data) else None
        tag3 = proc_tag(form.tag_3.data) if not is_empty(form.tag_3.data) else None
        tag4 = proc_tag(form.tag_4.data) if not is_empty(form.tag_4.data) else None
        tag5 = proc_tag(form.tag_5.data) if not is_empty(form.tag_5.data) else None

        # Create the inital transient sqlalchemy AnnotationVersion object
        anno = AnnotationVersion(book_id=book.id, approved=True,
                editor_id=current_user.id,
                first_line_num=form.first_line.data,
                last_line_num=form.last_line.data,
                first_char_idx=form.first_char_idx.data,
                last_char_idx=form.last_char_idx.data,
                annotation=form.annotation.data,
                tag_1=tag1, tag_2=tag2, tag_3=tag3, tag_4=tag4, tag_5=tag5)

        # Save the hash_id from the transient object
        ahash = anno.hash_id

        # Add/commit it to db
        db.session.add(anno)
        db.session.commit()

        # Grab the a_v object for its id using the hash
        anno = AnnotationVersion.query.filter_by(hash_id=ahash).first()

        # Create the head with the a_v id, add/commit it
        head = Annotation(book_id=book.id, head_id=anno.id,
                author_id=current_user.id)
        db.session.add(head)
        db.session.commit()

        # Get the same head object for its id
        pointer = Annotation.query.filter_by(head_id=anno.id).first()

        # Set the a_v's pointer_id to the pointer
        anno.pointer_id = pointer.id
        db.session.add(anno)
        db.session.commit()

        # That seems needlessly complex.
        flash("Annotation Submitted")

        next_page = request.args.get("next")
        if not next_page or url_parse(next_page).netloc != "":
            next_page = url_for("read", book_url=book_url)
        return redirect(next_page)

    else:
        form.first_line.data = first_line
        form.last_line.data = last_line
        form.first_char_idx.data = 0
        form.last_char_idx.data = -1

    return render_template("annotate.html", title=book.title, form=form,
             book=book, lines=lines)


@app.route("/upvote/<anno_id>/")
@login_required
def upvote(anno_id):
    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = url_for("read", book_url=anno.book.url)

    anno = Annotation.query.filter_by(id=anno_id).first_or_404()

    if current_user.already_voted(anno):
        vote = current_user.get_vote(anno)
        if vote.is_up():
            anno.rollback(vote)
            db.session.commit()
            return redirect(next_page)
        else:
            anno.rollback(vote)
    elif current_user == anno.author:
        flash("You cannot vote on your own annotation.")
        return redirect(next_page)

    anno.upvote(current_user)
    db.session.commit()

    return redirect(next_page)
    
@app.route("/downvote/<anno_id>/")
@login_required
def downvote(anno_id):
    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = url_for("read", book_url=anno.book.url)

    anno = Annotation.query.filter_by(id=anno_id).first_or_404()
    
    if current_user.already_voted(anno):
        vote = current_user.get_vote(anno)
        if not vote.is_up():
            anno.rollback(vote)
            db.session.commit()
            return redirect(next_page)
        else:
            anno.rollback(vote)
    elif current_user == anno.author:
        flash("You cannot vote on your own annotation.")
        return redirect(next_page)

    anno.downvote(current_user)
    db.session.commit()

    return redirect(next_page)

###########################
## Administration Routes ##
###########################

@app.route("/queue/edits/")
@login_required
def edit_review_queue():
    current_user.authorize(app.config["AUTHORIZATION"]["EDIT_QUEUE"])
    edits = AnnotationVersion.query.filter_by(approved=False).all()
    return render_template("queue.html", edits=edits)

@app.route("/approve/edit/<edit_hash>/")
@login_required
def approve(edit_hash):
    current_user.authorize(app.config["AUTHORIZATION"]["EDIT_QUEUE"])
    edit = AnnotationVersion.query.filter_by(hash_id = edit_hash).first_or_404()
    edit.approved = True
    edit.pointer.HEAD = edit
    edit.pointer.edit_pending = False
    db.session.commit()
    return redirect(url_for("edit_review_queue"))

@app.route("/reject/edit/<edit_hash>/")
def reject(edit_hash):
    current_user.authorize(app.config["AUTHORIZATION"]["EDIT_QUEUE"])
    edit = AnnotationVersion.query.filter_by(hash_id=edit_hash).first_or_404()
    edit.pointer.edit_pending = False
    db.session.delete(edit)
    db.session.commit()
    return redirect(url_for("edit_review_queue"))
