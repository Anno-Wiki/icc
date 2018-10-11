from collections import defaultdict
import hashlib
from flask import render_template, flash, redirect, url_for, request, Markup, \
        abort
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from sqlalchemy import or_
from app import app, db
from app.models import User, Book, Author, Line, Kind, Annotation, \
        AnnotationVersion, Tag, EditVote, AdminRight, Vote, BookRequest, \
        BookRequestVote
from app.forms import LoginForm, RegistrationForm, AnnotationForm, \
        LineNumberForm, TagForm, LineForm, BookRequestForm
from app.funky import preplines, is_filled


###########
## Index ##
###########

@app.route("/")
@app.route("/index/")
def index():
    page = request.args.get("page", 1, type=int)
    annotations = Annotation.query.filter_by(active=True
            ).order_by(Annotation.added.desc()
            ).paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    next_url = url_for("index", page=annotations.next_num) \
            if annotations.has_next else None
    prev_url = url_for("index", page=annotations.prev_num) \
            if annotations.has_prev else None
    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None
    return render_template("index.html", title="Home",
            annotations=annotations.items, uservotes=uservotes,
            next_url=next_url, prev_url=prev_url)


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
        elif user.locked:
            flash("That account is locked.")
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
    return render_template("forms/register.html", title="Register", form=form)


@app.route("/user/<user_id>/")
def user(user_id):
    page = request.args.get("page", 1, type=int)
    user = User.query.get_or_404(user_id)
    annotations = user.annotations.order_by(Annotation.added.desc()
            ).paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)

    next_url = url_for("user", user_id=user.id, page=annotations.next_num) \
            if annotations.has_next else None
    prev_url = url_for("user", user_id=user.id, page=annotations.prev_num) \
            if annotations.has_prev else None

    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None
    return render_template("view/user.html", title=user.username, user=user,
            annotations=annotations.items, uservotes=uservotes,
            next_url=next_url, prev_url=prev_url)


#####################
## Content Indexes ##
#####################

@app.route("/list/authors/")
def author_index():
    page = request.args.get("page", 1, type=int)
    authors = Author.query.order_by(Author.last_name
            ).paginate(page, app.config["CARDS_PER_PAGE"], False)

    next_url = url_for("author_index", page=authors.next_num) \
            if authors.has_next else None
    prev_url = url_for("author_index", page=authors.prev_num) \
            if authors.has_prev else None

    return render_template("indexes/authors.html", title="Authors",
            authors=authors.items, next_url=next_url, prev_url=prev_url)


@app.route("/author/<name>/")
def author(name):
    author = Author.query.filter_by(url=name).first_or_404()
    return render_template("view/author.html", title=author.name, author=author)


@app.route("/list/books/")
def book_index():
    page = request.args.get("page", 1, type=int)
    books = Book.query.order_by(Book.sort_title
            ).paginate(page, app.config["CARDS_PER_PAGE"], False)

    next_url = url_for("book_index", page=books.next_num) \
            if books.has_next else None
    prev_url = url_for("book_index", page=books.prev_num) \
            if books.has_prev else None

    return render_template("indexes/books.html", title="Books",
            books=books.items, next_url=next_url, prev_url=prev_url)


@app.route("/book/<book_url>/", methods=["GET", "POST"])
def book(book_url):
    book = Book.query.filter_by(url=book_url).first_or_404()

    # get the kinds for each heierarchical chapter level
    bk_kind = Kind.query.filter_by(kind="bk").first()
    pt_kind = Kind.query.filter_by(kind="pt").first()
    ch_kind = Kind.query.filter_by(kind="ch").first()

    # get all the heierarchical chapter lines
    hierarchy = book.lines.filter(
            or_(Line.kind==bk_kind, Line.kind==pt_kind, Line.kind==ch_kind)
            ).order_by(Line.l_num.asc()).all()

    return render_template("view/book.html", title=book.title, book=book,
            hierarchy=hierarchy)

@app.route("/list/tags/")
def tag_index():
    page = request.args.get("page", 1, type=int)
    tags = Tag.query.order_by(Tag.tag
            ).paginate(page, app.config["CARDS_PER_PAGE"], False)

    next_url = url_for("tag_index", page=tags.next_num) \
            if tags.has_next else None
    prev_url = url_for("tag_index", page=tags.prev_num) \
            if tags.has_prev else None

    return render_template("indexes/tags.html", title="Tags",
            tags=tags.items, next_url=next_url, prev_url=prev_url)

@app.route("/tag/<tag>/")
def tag(tag):
    page = request.args.get("page", 1, type=int)
    tag = Tag.query.filter_by(tag=tag).first_or_404()
    annotations = tag.annotations.order_by(Annotation.weight.desc()).paginate(page,
            app.config["ANNOTATIONS_PER_PAGE"], False)

    next_url = url_for("tag", tag=tag.tag, page=annotations.next_num) \
            if annotations.has_next else None
    prev_url = url_for("tag", tag=tag.tag, page=annotations.prev_num) \
            if annotations.has_prev else None

    return render_template("view/tag.html", title=tag.tag, tag=tag,
            annotations=annotations.items,
            next_url=next_url, prev_url=prev_url)


####################
## Reading Routes ##
####################

@app.route("/annotation/<annotation_id>")
def view_annotation(annotation_id):
    annotation = Annotation.query.get_or_404(annotation_id)
    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None
    return render_template("view/annotation.html", title=annotation.book.title,
            annotation=annotation, uservotes=uservotes)


@app.route("/read/<book_url>", methods=["GET", "POST"])
def read(book_url):
    book = Book.query.filter_by(url=book_url).first_or_404()
    tag = request.args.get("tag", None, type=str)
    bk = request.args.get("book", 0, type=int)
    pt = request.args.get("part", 0, type=int)
    ch = request.args.get("chapter", 0, type=int)

    if ch != 0:
        lines = book.lines.filter(
                Line.bk_num==bk, Line.pt_num==pt, Line.ch_num==ch
                ).order_by(Line.l_num.asc()).all()
    elif pt != 0:
        lines = book.lines.filter(Line.bk_num==bk, Line.pt_num==pt
                ).order_by(Line.l_num.asc()).all()
    else:
        lines = book.lines.filter(Line.bk_num==bk,
                ).order_by(Line.l_num.asc()).all()

    if len(lines) <= 0:
        abort(404)

    form = LineNumberForm()


    next_page = lines[0].get_next_section() if ch == 0 else \
            lines[-1].get_next_section()
    prev_page = lines[0].get_prev_section()
    if next_page != None:
        next_page = next_page.get_url()
    if prev_page != None:
        prev_page = prev_page.get_url()

    if form.validate_on_submit():
        # line number boiler plate
        if not is_filled(form.first_line.data) and not is_filled(form.last_line.data):
            flash("Please enter a first and last line number to annotate a selection.")
            return redirect(url_for("read", book_url=book.url, bk=bk, pt=pt,
                ch=ch, tag=tag))
        elif not is_filled(form.first_line.data):
            ll = int(form.last_line.data)
            fl = ll
        elif not is_filled(form.last_line.data):
            fl = int(form.first_line.data)
            ll = fl
        else:
            fl = int(form.first_line.data)
            ll = int(form.last_line.data)

        if ll - fl > 5:
            fl = ll - 4

        if fl < 1:
            fl = 1
        if ll < 1:
            fl = 1
            ll = 1

        # redirect to annotate page, with next query param being the current
        # page. Multi-layered nested return statement. Read carefully.
        return redirect(url_for("annotate", book_url=book_url,
            first_line=fl, last_line=ll,
            next=url_for("read", book_url=book.url, bk=bk, pt=pt, ch=ch,
                tag=tag)
                )
            )

    # get all the annotations
    if tag:
        tag = Tag.query.filter_by(tag=tag).first_or_404()
        annotations = tag.annotations.filter(Annotation.book_id==book.id).all()
        tags = None
    else:
        annotations = book.annotations
        tags = []
        for a in annotations:
            for t in a.HEAD.tags:
                if t not in tags:
                    tags.append(t)

    # index the annotations in a dictionary
    annotations_idx = defaultdict(list)
    for a in annotations:
        if a.HEAD.last_line_num >= lines[0].l_num and \
                a.HEAD.last_line_num <= lines[-1].l_num:
            annotations_idx[a.HEAD.last_line_num].append(a)

    # replace markdown-style _ with <em> and </em>
    preplines(lines)

    # to darken up/down voted annotations
    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None

    # I have to query this so I only make a db call once instead of each time
    # for every line to find out if the user has edit_rights
    edit_right = AdminRight.query.filter_by(right="edit_lines").first()

    return render_template("read.html", title=book.title, form=form, book=book,
            lines=lines, annotations_idx=annotations_idx, uservotes=uservotes,
            tags=tags, tag=tag, next_page=next_page, prev_page=prev_page,
            edit_right=edit_right)


#####################
## Creation Routes ##
#####################

@app.route("/edit/<anno_id>", methods=["GET", "POST"])
@login_required
def edit(anno_id):
    annotation = Annotation.query.get_or_404(anno_id)

    if annotation.locked == True and not \
            current_user.has_right("edit_locked_annotations"):
        flash("That annotation is locked from editing.")
        next_page = request.args.get("next")
        if not next_page or url_parse(next_page).netloc != "":
            next_page = lines[0].get_url()
        return redirect(next_page)

    lines = annotation.lines
    form = AnnotationForm()

    if form.cancel.data:
        next_page = request.args.get("next")
        if not next_page or url_parse(next_page).netloc != "":
            next_page = lines[0].get_url()
        return redirect(next_page)

    elif form.validate_on_submit():
        # line number boilerplate
        fl = int(form.first_line.data)
        ll = int(form.last_line.data)
        if ll - fl > 5:
            fl = ll - 4
        if fl < 1:
            fl = 1
        if ll < 1:
            fl = 1
            ll = 1

        # Process all the tags
        raw_tags = form.tags.data.split()
        tags = []
        for t in raw_tags:
            tags.append(Tag.query.filter_by(tag=t).first())

        if len(tags) > 5:
            flash("There is a five tag limit.")
            return redirect(url_for("edit", anno_id=annotation.id))

        approved = current_user.has_right("immediate_edits")

        lockchange = False
        if current_user.has_right("lock_annotations"):
            lockchange = annotation.locked != form.locked.data
            annotation.locked = form.locked.data

        edit = AnnotationVersion(book=annotation.book,
                editor_id=current_user.id, pointer_id=anno_id,
                previous_id=annotation.HEAD.id,
                approved=approved,
                first_line_num=fl, last_line_num=ll,
                first_char_idx=form.first_char_idx.data,
                last_char_idx=form.last_char_idx.data,
                annotation=form.annotation.data, tags=tags)

        if edit.hash_id == annotation.HEAD.hash_id and not lockchange:
            flash("Your suggested edit is no different from the previous version.")
            return redirect(url_for("edit", anno_id=annotation.id))
        elif edit.hash_id == annotation.HEAD.hash_id and lockchange:
            db.session.commit()
            flash("Annotation Locked")
        else:
            annotation.edit_pending = not approved
            if approved:
                annotation.HEAD = edit
            db.session.add(edit)
            db.session.commit()

        if approved:
            flash("Edit complete.")
        else:
            flash("Edit submitted for review.")

        next_page = request.args.get("next")
        if not next_page or url_parse(next_page).netloc != "":
            next_page = lines[0].get_url()
        return redirect(next_page)

    elif not annotation.edit_pending:
        tag_strings = []
        for t in annotation.HEAD.tags:
            tag_strings.append(t.tag)
        form.first_line.data = annotation.HEAD.first_line_num
        form.last_line.data = annotation.HEAD.last_line_num
        form.first_char_idx.data = annotation.HEAD.first_char_idx
        form.last_char_idx.data = annotation.HEAD.last_char_idx
        form.annotation.data = annotation.HEAD.annotation
        form.tags.data = " ".join(tag_strings)
        form.locked.data = annotation.locked

    return render_template("forms/annotation.html", title=annotation.HEAD.book.title,
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
    elif int(last_line) - int(first_line) > 5:
        first_line = int(last_line) - 5
    if int(first_line) < 1:
        first_line = 1
    if int(last_line) < 1:
        last_line = 1

    book = Book.query.filter_by(url=book_url).first_or_404()
    lines = book.lines.filter(
            Line.l_num>=first_line, Line.l_num<=last_line).all()
    form = AnnotationForm()

    if lines == None:
        abort(404)

    if form.cancel.data:
        next_page = request.args.get("next")
        if not next_page or url_parse(next_page).netloc != "":
            next_page = lines[0].get_url()
        return redirect(next_page)

    elif form.validate_on_submit():
        # line number boiler plate
        fl = int(form.first_line.data)
        ll = int(form.last_line.data)
        if ll - fl > 5:
            fl = ll - 5
        if fl < 1:
            fl = 1
        if ll < 1:
            ll = 1

        # Process all the tags
        raw_tags = form.tags.data.split()
        tags = []
        for t in raw_tags:
            tags.append(Tag.query.filter_by(tag=t).first())

        if len(tags) > 5:
            flash("There is a five tag limit.")
            return redirect(url_for("edit", anno_id=annotation.id))

        # I'll use the language of git
        # Create the inital transient sqlalchemy AnnotationVersion object
        commit = AnnotationVersion(
                book=book, approved=True, editor=current_user,
                first_line_num=fl, last_line_num=ll,
                first_char_idx=form.first_char_idx.data,
                last_char_idx=form.last_char_idx.data,
                annotation=form.annotation.data, tags=tags)

        # Create the annotation pointer with HEAD pointing to anno
        head = Annotation(book=book, HEAD=commit, author=current_user)

        # add anno, commit it
        db.session.add(commit)
        db.session.add(head)
        db.session.commit()

        # make anno's pointer point to the 
        commit.pointer = head
        db.session.commit()

        flash("Annotation Submitted")

        next_page = request.args.get("next")
        if not next_page or url_parse(next_page).netloc != "":
            next_page = lines[0].get_url()
        return redirect(next_page)

    else:
        form.first_line.data = first_line
        form.last_line.data = last_line
        form.first_char_idx.data = 0
        form.last_char_idx.data = -1

    return render_template("forms/annotation.html", title=book.title, form=form,
             book=book, lines=lines)


@app.route("/upvote/<anno_id>/")
@login_required
def upvote(anno_id):
    annotation = Annotation.query.get_or_404(anno_id)

    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = annotation.lines[0].get_url()

    if current_user.already_voted(annotation):
        vote = current_user.ballots.filter(Vote.annotation==annotation).first()
        if vote.is_up():
            annotation.rollback(vote)
            db.session.commit()
            return redirect(next_page)
        else:
            annotation.rollback(vote)
    elif current_user == annotation.author:
        flash("You cannot vote on your own annotations.")
        return redirect(next_page)

    annotation.upvote(current_user)
    db.session.commit()

    return redirect(next_page)

@app.route("/downvote/<anno_id>/")
@login_required
def downvote(anno_id):
    annotation = Annotation.query.get_or_404(anno_id)

    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = annotation.lines[0].get_url()

    if current_user.already_voted(annotation):
        vote = current_user.ballots.filter(Vote.annotation==annotation).first()
        if not vote.is_up():
            annotation.rollback(vote)
            db.session.commit()
            return redirect(next_page)
        else:
            annotation.rollback(vote)
    elif current_user == annotation.author:
        flash("You cannot vote on your own annotation.")
        return redirect(next_page)

    annotation.downvote(current_user)
    db.session.commit()

    return redirect(next_page)

###########################
## Administration Routes ##
###########################

@app.route("/admin/tags/create", methods=["GET","POST"])
@login_required
def create_tag():
    current_user.authorize_rights("create_tags")
    form = TagForm()
    if form.cancel.data:
        return redirect(url_for("index"))
    if form.validate_on_submit():
        if form.tag.data != None and form.description.data != None:
            tag = Tag(tag=form.tag.data, description=form.description.data)
            db.session.add(tag)
            db.session.commit()
            flash("Tag created.")
            return redirect(url_for("index"))

    return render_template("forms/tag.html", title="Create Tag", form=form)


@app.route("/admin/queue/edits/")
@login_required
def edit_review_queue():
    current_user.authorize_rep(app.config["AUTHORIZATION"]["EDIT_QUEUE"])
    edits = AnnotationVersion.query.filter_by(approved=False,
            rejected=False).all()
    votes = current_user.edit_votes

    return render_template("indexes/edits.html", title="Edit Queue", edits=edits,
        votes=votes)

@app.route("/admin/approve/edit/<edit_hash>/")
@login_required
def approve(edit_hash):
    current_user.authorize_rep(app.config["AUTHORIZATION"]["EDIT_QUEUE"])
    edit = AnnotationVersion.query.filter_by(hash_id=edit_hash).first_or_404()
    if current_user.get_edit_vote(edit):
        flash(f"You already voted on edit {edit.hash_id}")
        return redirect(url_for("edit_review_queue"))
    elif edit.editor == current_user:
        flash("You cannot approve or reject your own edits")
        return redirect(url_for("edit_review_queue"))
    edit.approve(current_user)
    if edit.weight >= app.config["MIN_APPROVAL_RATING"]:
        edit.approved = True
        edit.pointer.HEAD = edit
        edit.pointer.edit_pending = False
    db.session.commit()
    return redirect(url_for("edit_review_queue"))

@app.route("/admin/reject/edit/<edit_hash>/")
def reject(edit_hash):
    current_user.authorize_rep(app.config["AUTHORIZATION"]["EDIT_QUEUE"])
    edit = AnnotationVersion.query.filter_by(hash_id=edit_hash).first_or_404()
    if current_user.get_edit_vote(edit):
        flash(f"You already voted on edit {edit.hash_id}")
        return redirect(url_for("edit_review_queue"))
    elif edit.editor == current_user:
        flash("You cannot approve or reject your own edits")
        return redirect(url_for("edit_review_queue"))
    edit.reject(current_user)
    if edit.weight <= app.config["MIN_REJECTION_RATING"]:
        edit.pointer.edit_pending = False
        edit.rejected = True
    db.session.commit()
    return redirect(url_for("edit_review_queue"))

@app.route("/admin/rescind_vote/edit/<edit_hash>/")
def rescind(edit_hash):
    current_user.authorize_rep(app.config["AUTHORIZATION"]["EDIT_QUEUE"])
    edit = AnnotationVersion.query.filter_by(hash_id=edit_hash).first_or_404()
    if edit.approved == True:
        flash("This annotation is already approved; your vote cannot be rescinded.")
        return redirect(url_for("edit_review_queue"))
    elif edit.rejected == True:
        flash("This annotation is already rejected; your vote cannot be rescinded.")
        return redirect(url_for("edit_review_queue"))
    vote = current_user.get_edit_vote(edit)
    if not vote:
        abort(404)
    edit.weight -= vote.delta
    db.session.delete(vote)
    db.session.commit()
    flash("Vote rescinded")
    return redirect(url_for("edit_review_queue"))

@app.route("/admin/edit/line/<line_id>/", methods=["GET", "POST"])
def edit_line(line_id):
    current_user.authorize_rights("edit_lines")
    line = Line.query.get_or_404(line_id)
    form = LineForm()
    form.line.data = line.line

    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = url_for("index")

    if form.cancel.data:
        return redirect(next_page)
    if form.validate_on_submit():
        if form.line.data != None and len(form.line.data) <= 200:
            line.line = form.line.data
            db.session.commit()
            flash("Line updated.")
            return redirect(next_page)
    return render_template("forms/line.html", title="Edit Line", form=form)

@app.route("/admin/delete/annotation/<anno_id>/")
def delete(anno_id):
    current_user.authorize_rights("delete_annotations")
    annotation = Annotation.query.get_or_404(anno_id)
    annotation.active = not annotation.active
    db.session.commit()
    if annotation.active:
        flash(f"Annotation {annotation.id} activated")
    else:
        flash(f"Annotation {annotation.id} inactivated.")

    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = url_for("index")
    return redirect(next_page)

@app.route("/admin/list/deleted_annotations/")
def view_deleted_annotations():
    page = request.args.get("page", 1, type=int)
    current_user.authorize_rights("view_deleted_annotations")
    annotations = Annotation.query.filter_by(active=False
            ).paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    next_url = url_for("view_deleted_annotations", page=annotations.next_num) \
            if annotations.has_next else None
    prev_url = url_for("view_deleted_annotations", page=annotations.prev_num) \
            if annotations.has_prev else None
    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None
    return render_template("index.html", title="Deleted Annotations",
            annotations=annotations.items, prev_url=prev_url, next_url=next_url,
            uservotes=uservotes)

@app.route("/request/book/", methods=["GET", "POST"])
@login_required
def book_request():
    current_user.authorize_rep(app.config["AUTHORIZATION"]["BOOK_REQUEST"])
    form = BookRequestForm()
    if form.cancel.data:
        return redirect(url_for("index"))
    if form.validate_on_submit():
        book_request = BookRequest(title=form.title.data,
                author=form.author.data, notes=form.notes.data,
                description=form.description.data,
                wikipedia=form.wikipedia.data, gutenberg=form.gutenberg.data,
                weight=1)
        vote = BookRequestVote(user=current_user, book_request=book_request)
        db.session.add(book_request)
        db.session.add(vote)
        db.session.commit()
        flash("Book request created and your vote has been applied.")
        return redirect(url_for("index"))
    return render_template("forms/book_request.html", title="Request Book",
            form=form)

@app.route("/list/book_requests/")
def book_request_index():
    page = request.args.get("page", 1, type=int)
    requests = BookRequest.query.order_by(BookRequest.weight
            ).paginate(page, app.config["BOOK_REQUESTS_PER_PAGE"], False)
    next_url = url_for("book_request_index", page=requests.next_num) \
            if requests.has_next else None
    prev_url = url_for("book_request_index", page=requests.prev_num) \
            if requests.has_prev else None
    uservotes = current_user.get_book_request_vote_dict() \
            if current_user.is_authenticated else None
    return render_template("indexes/book_requests.html", title="Book Requests",
            next_url=next_url, prev_url=prev_url, requests=requests.items,
            uservotes=uservotes)

@app.route("/book_request/<book_request_id>/")
def view_book_request(book_request_id):
    book_request = BookRequest.query.get_or_404(book_request_id)
    return render_template("view/book_request.html", book_request=book_request)

@app.route("/edit/book_request/<book_request_id>/", methods=["GET", "POST"])
@login_required
def edit_book_request(book_request_id):
    current_user.authorize_rights("edit_book_requests")
    book_request = BookRequest.query.get_or_404(book_request_id)
    form = BookRequestForm()
    if form.cancel.data:
        return redirect(url_for("view_book_request",
            book_request_id=book_request_id))
    if form.validate_on_submit():
        book_request.title = form.title.data
        book_request.author = form.author.data
        book_request.notes = form.notes.data
        book_request.description = form.description.data
        book_request.wikipedia = form.wikipedia.data
        book_request.gutenberg = form.gutenberg.data
        db.session.commit()
        flash("Book request edit complete.")
        return redirect(url_for("view_book_request",
            book_request_id=book_request_id))
    else:
        form.title.data = book_request.title
        form.author.data = book_request.author
        form.notes.data = book_request.notes
        form.description.data = book_request.description
        form.wikipedia.data = book_request.wikipedia
        form.gutenberg.data = book_request.gutenberg
    return render_template("forms/book_request.html", title="Edit Book Request",
            form=form)

@app.route("/upvote/book_request/<book_request_id>/")
@login_required
def upvote_book_request(book_request_id):
    book_request = BookRequest.query.get_or_404(book_request_id)

    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = url_for("book_request_index")

    if current_user.already_voted_book_request(book_request):
        vote = current_user.book_request_ballots.filter(
                BookRequestVote.book_request==book_request).first()
        rd = True if vote.is_up() else False
        book_request.rollback(vote)
        db.session.commit()
        if rd:
            return redirect(next_page)

    book_request.upvote(current_user)
    db.session.commit()

    return redirect(next_page)

@app.route("/downvote/book_request/<book_request_id>/")
@login_required
def downvote_book_request(book_request_id):
    book_request = BookRequest.query.get_or_404(book_request_id)

    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = url_for("book_request_index")

    if current_user.already_voted_book_request(book_request):
        vote = current_user.book_request_ballots.filter(
                BookRequestVote.book_request==book_request).first()
        rd = True if not vote.is_up() else False
        book_request.rollback(vote)
        db.session.commit()
        if rd:
            return redirect(next_page)

    book_request.downvote(current_user)
    db.session.commit()

    return redirect(next_page)
