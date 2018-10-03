from collections import defaultdict
import hashlib
from flask import render_template, flash, redirect, url_for, request, Markup, \
        abort
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from sqlalchemy import or_
from app import app, db
from app.models import User, Book, Author, Line, Kind, Annotation, \
        AnnotationVersion, Tag, EditVote
from app.forms import LoginForm, RegistrationForm, AnnotationForm, \
        LineNumberForm, TagForm, LineForm
from app.funky import preplines, is_filled


###########
## Index ##
###########

@app.route("/")
@app.route("/index/")
def index():
    page = request.args.get('page', 1, type=int)
    annotations = Annotation.query.order_by(Annotation.added.desc()
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

    return render_template("register.html", title="Register", form=form)


@app.route("/user/<user_id>/")
def user(user_id):
    user = User.query.filter_by(id=user_id).first_or_404()
    return render_template("user.html", title=user.username, user=user)


#####################
## Content Indexes ##
#####################

@app.route("/authors/")
def author_index():
    authors = Author.query.order_by(Author.last_name).all()
    return render_template("author_index.html", title="Authors",
            authors=authors)


@app.route("/authors/<name>/")
def author(name):
    author = Author.query.filter_by(url=name).first_or_404()
    return render_template("author.html", title=author.name, author=author)


@app.route("/books/")
def book_index():
    books = Book.query.order_by(Book.sort_title).all()
    return render_template("book_index.html", title="Books", books=books)


@app.route("/books/<book_url>/", methods=["GET", "POST"])
def book(book_url):
    book = Book.query.filter_by(url=book_url).first_or_404()

    # get the kinds for each heierarchical chapter level
    bk_kind = Kind.query.filter_by(kind="bk").first()
    pt_kind = Kind.query.filter_by(kind="pt").first()
    ch_kind = Kind.query.filter_by(kind="ch").first()

    # get all the heierarchical chapter lines
    hierarchy = Line.query.filter(Line.book_id==book.id,
            or_(Line.kind==bk_kind, Line.kind==pt_kind, Line.kind==ch_kind)
            ).order_by(Line.l_num.asc()).all()

    return render_template("book.html", title=book.title, book=book,
            hierarchy=hierarchy)

@app.route("/tags/")
def tag_index():
    tags = Tag.query.all()
    return render_template("tag_index.html", title="Tags", tags=tags)


####################
## Reading Routes ##
####################

@app.route("/annotation/<annotation_id>")
def view_annotation(annotation_id):
    annotation = Annotation.query.filter_by(id=annotation_id).first_or_404()
    lines = annotation.HEAD.get_lines() # we call it now to query it later
    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None
    return render_template("annotation.html", title=annotation.book.title,
            annotation=annotation, uservotes=uservotes, lines=lines)

@app.route("/tags/<tag>/")
def tag(tag):
    tag = Tag.query.filter_by(tag=tag).first_or_404()

    annotations = tag.get_annotations() 
    return render_template("tag.html", title=tag.tag, tag=tag,
            annotations=annotations)

@app.route("/read/<book_url>/book/<bk>/part/<pt>/chapter/<ch>/",
        defaults={"tag": None}, methods=["GET", "POST"])
@app.route("/read/<book_url>/book/<bk>/part/<pt>/chapter/<ch>/<tag>/",
        methods=["GET", "POST"])
def read(book_url, bk, pt, ch, tag):
    book = Book.query.filter_by(url=book_url).first_or_404()
    if int(ch) != 0:
        lines = Line.query.filter(Line.book_id==book.id,
                Line.bk_num==bk, Line.pt_num==pt, Line.ch_num==ch
                ).order_by(Line.l_num.asc()).all()
    elif int(pt) != 0:
        lines = Line.query.filter(Line.book_id==book.id,
                Line.bk_num==bk, Line.pt_num==pt
                ).order_by(Line.l_num.asc()).all()
    else:
        lines = Line.query.filter(Line.book_id==book.id,
                Line.bk_num==bk,
                ).order_by(Line.l_num.asc()).all()

    if len(lines) <= 0:
        abort(404)

    form = LineNumberForm()

    next_page = lines[0].get_next_section() if ch == 0 else \
            lines[-1].get_next_section()
    prev_page = lines[0].get_prev_section()
    if next_page != None:
        next_page = url_for("read", book_url=book.url, bk=next_page.bk_num,
                pt=next_page.pt_num, ch=next_page.ch_num, tag=tag)
    if prev_page != None:
        prev_page = url_for("read", book_url=book.url, bk=prev_page.bk_num,
                pt=prev_page.pt_num, ch=prev_page.ch_num, tag=tag)

    if form.validate_on_submit():
        # line number boiler plate
        if not is_filled(form.first_line.data) and not is_filled(form.last_line.data):
            flash("Please enter a first and last line number to annotate a selection.")
            return redirect(url_for("read", book_url=book.url, bk=bk, pt=pt,
                ch=ch, tag=tag))
        elif not is_filled(form.first_line.data):
            ll = int(form.last_line.data)
            fl = ll
        elif not is_filled(form.last_line.data) == "":
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
        annotations = tag.get_annotations_by_book(book)
        tags = None
    else:
        annotations = book.annotations
        tags = []
        for a in annotations:
            for t in a.get_tags():
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

    return render_template("read.html", title=book.title, form=form, book=book,
            lines=lines, annotations_idx=annotations_idx, uservotes=uservotes,
            tags=tags, tag=tag, next_page=next_page, prev_page=prev_page)


#####################
## Creation Routes ##
#####################

@app.route("/edit/<anno_id>", methods=["GET", "POST"])
@login_required
def edit(anno_id):
    annotation = Annotation.query.filter_by(id=anno_id).first_or_404()

    if annotation.locked == True and not \
            current_user.has_right("edit_locked_annotations"):
        flash("That annotation is locked from editing.")
        next_page = request.args.get("next")
        if not next_page or url_parse(next_page).netloc != "":
            next_page = lines[0].get_url()
        return redirect(next_page)

    lines = annotation.HEAD.get_lines()
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

        tag1 = Tag.query.filter_by(tag=form.tag_1.data).first()
        tag2 = Tag.query.filter_by(tag=form.tag_2.data).first()
        tag3 = Tag.query.filter_by(tag=form.tag_3.data).first()
        tag4 = Tag.query.filter_by(tag=form.tag_4.data).first()
        tag5 = Tag.query.filter_by(tag=form.tag_5.data).first()

        approved = True if current_user.has_right("immediate_edits") else False

        edit = AnnotationVersion(book_id=annotation.HEAD.book.id,
                editor_id=current_user.id, pointer_id=anno_id,
                previous_id=annotation.HEAD.id,
                approved=approved,
                first_line_num=fl, last_line_num=ll,
                first_char_idx=form.first_char_idx.data,
                last_char_idx=form.last_char_idx.data,
                annotation=form.annotation.data,
                tag_1=tag1, tag_2=tag2, tag_3=tag3, tag_4=tag4, tag_5=tag5)

        if edit.hash_id == annotation.HEAD.hash_id:
            flash("Your suggested edit is no different from the previous version.")
            return redirect(url_for("edit", anno_id=annotation.id))

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
        form.first_line.data = annotation.HEAD.first_line_num
        form.last_line.data = annotation.HEAD.last_line_num
        form.first_char_idx.data = annotation.HEAD.first_char_idx
        form.last_char_idx.data = annotation.HEAD.last_char_idx
        form.annotation.data = annotation.HEAD.annotation
        tag1 = annotation.HEAD.tag_1.tag if annotation.HEAD.tag_1 else None
        tag2 = annotation.HEAD.tag_2.tag if annotation.HEAD.tag_2 else None
        tag3 = annotation.HEAD.tag_3.tag if annotation.HEAD.tag_3 else None
        tag4 = annotation.HEAD.tag_4.tag if annotation.HEAD.tag_4 else None
        tag5 = annotation.HEAD.tag_5.tag if annotation.HEAD.tag_5 else None
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
    elif int(last_line) - int(first_line) > 5:
        first_line = int(last_line) - 5
    if int(first_line) < 1:
        first_line = 1
    if int(last_line) < 1:
        last_line = 1

    book = Book.query.filter_by(url=book_url).first_or_404()
    lines = Line.query.filter(Line.book_id==book.id, Line.l_num>=first_line,
            Line.l_num<=last_line).all()
    form = AnnotationForm()

    if lines == None:
        abort(404)

    tag1 = None
    tag2 = None
    tag3 = None
    tag4 = None
    tag5 = None

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
        tag1 = Tag.query.filter_by(tag=form.tag_1.data).first()
        tag2 = Tag.query.filter_by(tag=form.tag_2.data).first()
        tag3 = Tag.query.filter_by(tag=form.tag_3.data).first()
        tag4 = Tag.query.filter_by(tag=form.tag_4.data).first()
        tag5 = Tag.query.filter_by(tag=form.tag_5.data).first()

        # I'll use the language of git
        # Create the inital transient sqlalchemy AnnotationVersion object
        commit = AnnotationVersion(book=book, approved=True,
                editor=current_user,
                first_line_num=fl,
                last_line_num=ll,
                first_char_idx=form.first_char_idx.data,
                last_char_idx=form.last_char_idx.data,
                annotation=form.annotation.data,
                tag_1=tag1, tag_2=tag2, tag_3=tag3, tag_4=tag4, tag_5=tag5)

        # Create the annotation pointer with HEAD pointing to anno
        head = Annotation(book=book, HEAD=commit, author=current_user)

        # add anno, commit it
        db.session.add(commit)
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

    return render_template("annotate.html", title=book.title, form=form,
             book=book, lines=lines)


@app.route("/upvote/<anno_id>/")
@login_required
def upvote(anno_id):
    anno = Annotation.query.filter_by(id=anno_id).first_or_404()

    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = anno.HEAD.get_lines()[0].get_url()

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
    anno = Annotation.query.filter_by(id=anno_id).first_or_404()

    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = anno.HEAD.get_lines()[0].get_url()
    
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
            
    return render_template("create_tag.html", title="Create Tag", form=form)


@app.route("/admin/queue/edits/")
@login_required
def edit_review_queue():
    current_user.authorize_rep(app.config["AUTHORIZATION"]["EDIT_QUEUE"])
    edits = AnnotationVersion.query.filter_by(approved=False,
            rejected=False).all()
    votes = current_user.edit_votes

    return render_template("queue.html", title="Edit Queue", edits=edits,
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
    line = Line.query.filter_by(id=line_id).first_or_404()
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
    return render_template("edit_line.html", title="Edit Line", form=form)
