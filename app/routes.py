from collections import defaultdict
from datetime import datetime
import hashlib
from flask import render_template, flash, redirect, url_for, request, Markup, \
        abort, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from sqlalchemy import or_
from app import app, db
from app.models import User, Book, Author, Line, Kind, Annotation, \
        AnnotationVersion, Tag, EditVote, AdminRight, Vote, BookRequest, \
        BookRequestVote, TagRequest, TagRequestVote, UserFlag, AnnotationFlag
from app.forms import LoginForm, RegistrationForm, AnnotationForm, \
        LineNumberForm, TagForm, LineForm, BookRequestForm, TagRequestForm, \
        EditProfileForm, ResetPasswordRequestForm, ResetPasswordForm, TextForm,\
        AreYouSureForm
from app.email import send_password_reset_email
from app.funky import preplines, is_filled

@app.before_request
def before_request():
    if current_user.is_authenticated and current_user.locked:
        logout_user()

###########
## Index ##
###########

@app.route("/")
@app.route("/index/")
def index():
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "new", type=str)
    if sort == "new":
        annotations = Annotation.query.filter_by(active=True
                ).order_by(Annotation.added.desc()
                ).paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "weight":
        annotations = Annotation.query.filter_by(active=True
                ).order_by(Annotation.weight.desc()
                ).paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    annotationflags = AnnotationFlag.query.all()
    next_page = url_for("index", page=annotations.next_num) \
            if annotations.has_next else None
    prev_page = url_for("index", page=annotations.prev_num) \
            if annotations.has_prev else None
    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None
    return render_template("index.html", title="Home",
            annotations=annotations.items, uservotes=uservotes,
            next_page=next_page, prev_page=prev_page,
            annotationflags=annotationflags, sort=sort)


####################
## User Functions ##
####################

@app.route("/login/", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash("Invalid email or password")
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
        user = User(displayname=form.displayname.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Congratulations, you are now a registered user!")
        return redirect(url_for("login"))
    return render_template("forms/register.html", title="Register", form=form)

@app.route("/user/edit_profile/", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.cancel.data:
        return redirect(next_page)
    if form.validate_on_submit():
        current_user.displayname = form.displayname.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash("Your changes have been saved.")
        return redirect(url_for("user", user_id=current_user.id))
    elif request.method == "GET":
        form.displayname.data = current_user.displayname
        form.about_me.data = current_user.about_me
    return render_template("forms/edit_profile.html", title="Edit Profile",
                           form=form)

@app.route("/reset_password_request", methods=["GET", "POST"])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = ResetPasswordRequestForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
            flash("Check your email for the instructions ot request your "
            "password.")
            return redirect(url_for("login"))
        else:
            flash("Email not found.")

    return render_template("forms/reset_password_request.html", title="Reset "
            "Password", form=form)

@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for("index"))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash("Your password has been changed.")
        return redirect(url_for("login"))
    return render_template("forms/reset_password.html", form=form)

@app.route("/flag/<flag_id>/user/<user_id>/")
@login_required
def flag_user(flag_id, user_id):
    user = User.query.get_or_404(user_id)
    flag = UserFlag.query.get_or_404(flag_id)

    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = url_for("user", user_id=user.id)

    user.flag(flag, current_user)
    db.session.commit()
    flash(f"User {user.displayname} flagged \"{flag.flag}\"")
    return redirect(next_page)

@app.route("/user/delete_account/")
@login_required
def delete_account():
    current_user.displayname = f"deleted_user_{current_user.id}"
    current_user.email = ""
    current_user.password_hash = "***"
    current_user.about_me = ""
    db.session.commit()
    logout_user()
    flash("Account anonymized.")
    return redirect(url_for("index"))

@app.route("/user/delete_account_check/", methods=["GET", "POST"])
@login_required
def delete_account_check():
    form = AreYouSureForm()

    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = url_for("user", user_id=user.id)

    if form.cancel.data:
        flash("Phew, you almost pulled the trigger!")
        return redirect(next_page)
    elif form.validate_on_submit():
        return redirect(url_for("delete_account"))

    return render_template("forms/delete_account_check.html", form=form,
            title="Are you sure?")

#############
## Indexes ##
#############

@app.route("/list/authors/")
def author_index():
    page = request.args.get("page", 1, type=int)
    authors = Author.query.order_by(Author.last_name
            ).paginate(page, app.config["CARDS_PER_PAGE"], False)

    next_page = url_for("author_index", page=authors.next_num) \
            if authors.has_next else None
    prev_page = url_for("author_index", page=authors.prev_num) \
            if authors.has_prev else None

    return render_template("indexes/authors.html", title="Authors",
            authors=authors.items, next_page=next_page, prev_page=prev_page)

@app.route("/list/books/")
def book_index():
    page = request.args.get("page", 1, type=int)
    books = Book.query.order_by(Book.sort_title
            ).paginate(page, app.config["CARDS_PER_PAGE"], False)

    next_page = url_for("book_index", page=books.next_num) \
            if books.has_next else None
    prev_page = url_for("book_index", page=books.prev_num) \
            if books.has_prev else None

    return render_template("indexes/books.html", title="Books",
            books=books.items, prev_page=prev_page, next_page=next_page)

@app.route("/list/tags/")
def tag_index():
    page = request.args.get("page", 1, type=int)
    tags = Tag.query.order_by(Tag.tag
            ).paginate(page, app.config["CARDS_PER_PAGE"], False)
    next_page = url_for("tag_index", page=tags.next_num) \
            if tags.has_next else None
    prev_page = url_for("tag_index", page=tags.prev_num) \
            if tags.has_prev else None
    return render_template("indexes/tags.html", title="Tags",
            tags=tags.items, next_page=next_page, prev_page=prev_page)

@app.route("/list/users/")
def user_index():
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "reputation", type=str)
    if sort == "reputation":
        users = User.query.order_by(User.reputation.desc()
                ).paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "name":
        users = User.query.order_by(User.displayname.desc()
                ).paginate(page, app.config["CARDS_PER_PAGE"], False)
    next_page = url_for("user_index", page=users.next_num) \
            if users.has_next else None
    prev_page = url_for("user_index", page=users.prev_num) \
            if users.has_prev else None
    return render_template("indexes/users.html", title="Users",
            users=users.items, next_page=next_page, prev_page=prev_page,
            sort=sort)


#######################
## Single Item Views ##
#######################

@app.route("/author/<name>/")
def author(name):
    author = Author.query.filter_by(url=name).first_or_404()
    return render_template("view/author.html", title=author.name, author=author)

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

@app.route("/tag/<tag>/")
def tag(tag):
    page = request.args.get("page", 1, type=int)
    tag = Tag.query.filter_by(tag=tag).first_or_404()
    annotations = tag.annotations.order_by(Annotation.weight.desc()).paginate(page,
            app.config["ANNOTATIONS_PER_PAGE"], False)

    next_page = url_for("tag", tag=tag.tag, page=annotations.next_num) \
            if annotations.has_next else None
    prev_page = url_for("tag", tag=tag.tag, page=annotations.prev_num) \
            if annotations.has_prev else None

    return render_template("view/tag.html", title=tag.tag, tag=tag,
            annotations=annotations.items,
            next_page=next_page, prev_page=prev_page)

@app.route("/annotation/<annotation_id>")
def view_annotation(annotation_id):
    annotation = Annotation.query.get_or_404(annotation_id)
    annotationflags = AnnotationFlag.query.all()
    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None
    return render_template("view/annotation.html", title=annotation.book.title,
            annotation=annotation, uservotes=uservotes,
            annotationflags=annotationflags)

@app.route("/annotation/<annotation_id>/edit_history/")
def edit_history(annotation_id):
    annotation = Annotation.query.get_or_404(annotation_id)
    annotationflags = AnnotationFlag.query.all()
    history = annotation.get_history()
    return render_template("view/edit_history.html", title=f"Edit History",
            history=history, annotation=annotation,
            annotationflags=annotationflags)

@app.route("/user/<user_id>/")
def user(user_id):
    page = request.args.get("page", 1, type=int)
    user = User.query.get_or_404(user_id)
    annotations = user.annotations.order_by(Annotation.added.desc()
            ).paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    userflags = UserFlag.query.all()

    next_page = url_for("user", user_id=user.id, page=annotations.next_num) \
            if annotations.has_next else None
    prev_page = url_for("user", user_id=user.id, page=annotations.prev_num) \
            if annotations.has_prev else None

    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None
    return render_template("view/user.html", title=f"User {user.displayname}",
            user=user, annotations=annotations.items, uservotes=uservotes,
            next_page=next_page, prev_page=prev_page, userflags=userflags)

####################
## Reading Routes ##
####################

@app.route("/read/<book_url>", methods=["GET", "POST"])
def read(book_url):
    book = Book.query.filter_by(url=book_url).first_or_404()
    tag = request.args.get("tag", None, type=str)
    bk = request.args.get("book", 0, type=int)
    pt = request.args.get("part", 0, type=int)
    ch = request.args.get("chapter", 0, type=int)
    annotationflags = AnnotationFlag.query.all()

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
            return redirect(url_for("read", book_url=book.url, book=bk, part=pt,
                chapter=ch, tag=tag))
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
            next=url_for("read", book_url=book.url, book=bk, part=pt,
                chapter=ch, tag=tag)
                )
            )

    # get all the annotations
    if tag:
        tag = Tag.query.filter_by(tag=tag).first_or_404()
        annotations = tag.annotations.filter(Annotation.book_id==book.id).all()
        tags = None
    else:
        annotations = book.annotations.all()
        tags = []
        for a in annotations:
            if a.HEAD.first_line_num >= lines[0].l_num and a.HEAD.last_line_num <= lines[-1].l_num:
                for t in a.HEAD.tags:
                    if t not in tags:
                        tags.append(t)

    # index the annotations in a dictionary
    annotations_idx = defaultdict(list)
    for a in annotations:
        if a.HEAD.last_line_num >= lines[0].l_num and \
                a.HEAD.last_line_num <= lines[-1].l_num:
            annotations_idx[a.HEAD.last_line_num].append(a)


    # to darken up/down voted annotations
    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None

    # I have to query this so I only make a db call once instead of each time
    # for every line to find out if the user has edit_rights
    edit_right = AdminRight.query.filter_by(right="edit_lines").first()

    preplines(lines)

    return render_template("read.html", title=book.title, form=form, book=book,
            lines=lines, annotations_idx=annotations_idx, uservotes=uservotes,
            tags=tags, tag=tag, next_page=next_page, prev_page=prev_page,
            edit_right=edit_right, annotationflags=annotationflags)

#######################
## Annotation System ##
#######################

@app.route("/annotate/<book_url>/<first_line>/<last_line>/",
        methods=["GET", "POST"])
@login_required
def annotate(book_url, first_line, last_line):
    if int(first_line) > int(last_line):
        tmp = first_line
        first_line = last_line
        last_line = tmp
    if int(first_line) < 1:
        first_line = 1
    if int(last_line) < 1:
        first_line = 1
        last_line = 1

    book = Book.query.filter_by(url=book_url).first_or_404()
    lines = book.lines.filter(Line.l_num>=first_line,
            Line.l_num<=last_line).all()
    context = book.lines.filter(Line.l_num>=int(first_line)-5,
            Line.l_num<=int(last_line)+5).all()
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
        if fl < 1:
            fl = 1
        if ll < 1:
            ll = 1
            fl = 1

        # Process all the tags
        raw_tags = form.tags.data.split()
        tags = []
        fail = False
        for tag in raw_tags:
            t = Tag.query.filter_by(tag=tag).first()
            if t:
                tags.append(t)
            else:
                flash(f"tag {tag} does not exist.")
                fail = True

        if fail:
            return render_template("forms/annotation.html", title=book.title,
                    form=form, book=book, lines=lines, context=context)
        elif len(tags) > 5:
            flash("There is a five tag limit.")
            return render_template("forms/annotation.html", title=book.title,
                    form=form, book=book, lines=lines, context=context)

        # I'll use the language of git
        # Create the inital transient sqlalchemy AnnotationVersion object
        commit = AnnotationVersion(
                book=book, approved=True, editor=current_user,
                first_line_num=fl, last_line_num=ll,
                first_char_idx=form.first_char_idx.data,
                last_char_idx=form.last_char_idx.data,
                annotation=form.annotation.data, tags=tags, current=True)

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
             book=book, lines=lines, context=context)

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
        if fl < 1:
            fl = 1
        if ll < 1:
            fl = 1
            ll = 1

        # Process all the tags
        raw_tags = form.tags.data.split()
        tags = []
        fail = False
        for tag in raw_tags:
            t = Tag.query.filter_by(tag=tag).first()
            if t:
                tags.append(t)
            else:
                fail = True
                flash(f"tag {tag} does not exist.")

        # In both of these cases we want to retain the form entered so the user
        # can edit it; therefore we re-render the template instead of
        # redirecting
        if fail:
            return render_template("forms/annotation.html",
                    title=annotation.HEAD.book.title, form=form,
                    book=annotation.HEAD.book, lines=lines,
                    annotation=annotation)
        elif len(tags) > 5:
            flash("There is a five tag limit.")
            return render_template("forms/annotation.html",
                    title=annotation.HEAD.book.title, form=form,
                    book=annotation.HEAD.book, lines=lines,
                    annotation=annotation)

        approved = current_user.has_right("immediate_edits") or \
                annotation.author == current_user

        lockchange = False
        if current_user.has_right("lock_annotations"):
            # the lock changes if the annotation's lock value is different from
            # the form's locked data. We have to specify this because this won't
            # show up in edit's hash_id and will fail the uniqueness test.
            lockchange = annotation.locked != form.locked.data
            annotation.locked = form.locked.data

        edit = AnnotationVersion(book=annotation.book,
                editor_id=current_user.id, pointer_id=anno_id,
                previous_id=annotation.HEAD.id,
                approved=approved,
                first_line_num=fl, last_line_num=ll,
                first_char_idx=form.first_char_idx.data,
                last_char_idx=form.last_char_idx.data,
                annotation=form.annotation.data, tags=tags, current=True)

        if edit.hash_id == annotation.HEAD.hash_id and not lockchange:
            flash("Your suggested edit is no different from the previous version.")
            return redirect(url_for("edit", anno_id=annotation.id))
        elif edit.hash_id == annotation.HEAD.hash_id and lockchange:
            db.session.commit()
            flash("Annotation Locked")
        else:
            annotation.edit_pending = not approved
            if approved:
                annotation.HEAD.current = False
                db.session.commit()
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

@app.route("/rollback/edit/<annotation_id>/<edit_id>/")
@login_required
def rollback_edit(annotation_id, edit_id):
    annotation = Annotation.query.get_or_404(annotation_id)
    edit = AnnotationVersion.query.get_or_404(edit_id)
    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = url_for("edit_history", annotation_id=annotation.id)
    if annotation.HEAD == edit:
        flash("You can't roll back an annotation to it's current version.")
        return redirect(next_page)
    if annotation.locked == True and not \
            current_user.has_right("edit_locked_annotations"):
        flash("That annotation is locked from editing.")
        return redirect(next_page)
    approved = current_user.has_right("immediate_edits")
    new_edit = AnnotationVersion(
            editor_id=current_user.id,
            pointer_id=annotation.id,
            book_id=annotation.book_id,
            previous_id=annotation.HEAD.id,
            first_line_num=edit.first_line_num,
            last_line_num=edit.last_line_num,
            first_char_idx=edit.first_char_idx,
            last_char_idx=edit.last_char_idx,
            annotation=edit.annotation,
            modified=datetime.utcnow(),
            approved=approved
            )
    # if the approved is true (i.e., the user has immediate_edit rights),
    # then the value of edit_pending needs to be not true, and vice versa.
    annotation.edit_pending = not approved
    if approved:
        edit.current = False
        new_edit.current = True
        new_edit.approved = True
        annotation.HEAD = new_edit
    db.session.commit()
    if approved:
        flash("Edit complete.")
    else:
        flash("Edit submitted for review.")
    return redirect(next_page)

@app.route("/upvote/<anno_id>/")
@login_required
def upvote(anno_id):
    annotation = Annotation.query.get_or_404(anno_id)

    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = annotation.lines[0].get_url()

    if current_user == annotation.author:
        flash("You cannot vote on your own annotations.")
        return redirect(next_page)
    elif current_user.already_voted(annotation):
        vote = current_user.ballots.filter(Vote.annotation==annotation).first()
        if vote.is_up():
            annotation.rollback(vote)
            db.session.commit()
            return redirect(next_page)
        else:
            annotation.rollback(vote)

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

    if current_user == annotation.author:
        flash("You cannot vote on your own annotation.")
        return redirect(next_page)
    elif current_user.already_voted(annotation):
        vote = current_user.ballots.filter(Vote.annotation==annotation).first()
        if not vote.is_up():
            annotation.rollback(vote)
            db.session.commit()
            return redirect(next_page)
        else:
            annotation.rollback(vote)

    annotation.downvote(current_user)
    db.session.commit()

    return redirect(next_page)

@app.route("/flag/<flag_id>/annotation/<annotation_id>/")
@login_required
def flag_annotation(flag_id, annotation_id):
    annotation = Annotation.query.get_or_404(annotation_id)
    flag = AnnotationFlag.query.get_or_404(flag_id)

    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = url_for("annotation", annotation_id=annotation.id)

    annotation.flag(flag, current_user)
    db.session.commit()
    flash(f"Annotation {annotation.id} flagged \"{flag.flag}\"")
    return redirect(next_page)

#################################
#################################
## ## Administration Routes ## ##
#################################
#################################

@app.route("/admin/lock/user/<user_id>/")
@login_required
def lock_user(user_id):
    current_user.authorize_rights("lock_users")
    user = User.query.get_or_404(user_id)
    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = url_for("user", user_id=user.id)
    user.locked = not user.locked
    db.session.commit()
    flash(f"User account {user.displayname} locked.")
    return redirect(next_page)

#################
## Edit Review ##
#################

@app.route("/admin/queue/edits/")
@login_required
def edit_review_queue():
    if not current_user.has_right("review_edits"):
        current_user.authorize_rep(app.config["AUTHORIZATION"]["EDIT_QUEUE"])
    edits = AnnotationVersion.query.filter_by(approved=False,
            rejected=False).all()
    votes = current_user.edit_votes
    return render_template("indexes/edits.html", title="Edit Queue",
            edits=edits, votes=votes)

@app.route("/admin/approve/edit/<edit_hash>/")
@login_required
def approve(edit_hash):
    if not current_user.has_right("review_edits"):
        current_user.authorize_rep(app.config["AUTHORIZATION"]["EDIT_QUEUE"])
    edit = AnnotationVersion.query.filter_by(hash_id=edit_hash).first_or_404()
    if current_user.get_edit_vote(edit):
        flash(f"You already voted on edit {edit.hash_id}")
        return redirect(url_for("edit_review_queue"))
    elif edit.editor == current_user:
        flash("You cannot approve or reject your own edits")
        return redirect(url_for("edit_review_queue"))
    edit.approve(current_user)
    if edit.weight >= app.config["MIN_APPROVAL_RATING"] or \
            current_user.has_right("approve_edits"):
        edit.approved = True
        edit.pointer.HEAD = edit
        edit.pointer.edit_pending = False
    db.session.commit()
    return redirect(url_for("edit_review_queue"))

@app.route("/admin/reject/edit/<edit_hash>/")
@login_required
def reject(edit_hash):
    if not current_user.has_right("review_edits"):
        current_user.authorize_rep(app.config["AUTHORIZATION"]["EDIT_QUEUE"])
    edit = AnnotationVersion.query.filter_by(hash_id=edit_hash).first_or_404()
    if current_user.get_edit_vote(edit):
        flash(f"You already voted on edit {edit.hash_id}")
        return redirect(url_for("edit_review_queue"))
    elif edit.editor == current_user:
        flash("You cannot approve or reject your own edits")
        return redirect(url_for("edit_review_queue"))
    edit.reject(current_user)
    if edit.weight <= app.config["MIN_REJECTION_RATING"] or \
            current_user.has_right("approve_edits"):
        edit.pointer.edit_pending = False
        edit.rejected = True
    db.session.commit()
    return redirect(url_for("edit_review_queue"))

@app.route("/admin/rescind_vote/edit/<edit_hash>/")
@login_required
def rescind(edit_hash):
    if not current_user.has_right("review_edits"):
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

#####################
## Content Editing ##
#####################

@app.route("/admin/edit/line/<line_id>/", methods=["GET", "POST"])
@login_required
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

@app.route("/admin/edit/author_bio/<author_id>/", methods=["GET", "POST"])
@login_required
def edit_bio(author_id):
    current_user.authorize_rights("edit_bios")
    author = Author.query.get_or_404(author_id)
    form = TextForm()
    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = url_for("author", name=author.url)
    if form.cancel.data:
        return redirect(next_page)
    if form.validate_on_submit():
        if form.text.data != None:
            author.bio = form.text.data
            db.session.commit()
            flash("Bio updated.")
            return redirect(next_page)
    else:
        form.text.data = author.bio

    return render_template("forms/text.html", title="Edit Bio", form=form)

@app.route("/admin/edit/book_summary/<book_id>/", methods=["GET", "POST"])
@login_required
def edit_summary(book_id):
    current_user.authorize_rights("edit_summaries")
    book = Book.query.get_or_404(book_id)
    form = TextForm()
    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = url_for("book", book_url=book.url)
    if form.cancel.data:
        return redirect(next_page)
    if form.validate_on_submit():
        if form.text.data != None:
            book.summary = form.text.data
            db.session.commit()
            flash("Summary updated.")
            return redirect(next_page)
    else:
        form.text.data = book.summary
    return render_template("forms/text.html", title="Edit Summary", form=form)

@app.route("/admin/edit/tag/<tag_id>/", methods=["GET", "POST"])
@login_required
def edit_tag(tag_id):
    current_user.authorize_rights("edit_tags")
    tag = Tag.query.get_or_404(tag_id)
    form = TagForm()
    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = url_for("tag", tag=tag.tag)
    if form.cancel.data:
        return redirect(next_page)
    if form.validate_on_submit():
        if form.tag.data != None and form.description.data != None:
            tag.tag = form.tag.data
            tag.description = form.description.data
            db.session.commit()
            flash("Tag updated.")
            # we have to reinitiate tag url bc tag changed
            next_page = url_for("tag", tag=tag.tag)
            return redirect(next_page)
    else:
        form.tag.data = tag.tag
        form.description.data = tag.description
    return render_template("forms/tag.html", title="Edit Tag", form=form)

###############################
## Annotation Administration ##
###############################

@app.route("/admin/delete/annotation/<anno_id>/")
@login_required
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
@login_required
def view_deleted_annotations():
    sort = request.args.get("sort", "new", type=str)
    page = request.args.get("page", 1, type=int)
    if sort == "new":
        annotations = Annotation.query.filter_by(active=False
                ).order_by(Annotation.added.desc()
                ).paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "weight":
        annotations = Annotation.query.filter_by(active=False
                ).order_by(Annotation.weight.desc()
                ).paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    current_user.authorize_rights("view_deleted_annotations")
    annotations = Annotation.query.filter_by(active=False
            ).paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    next_page = url_for("view_deleted_annotations", page=annotations.next_num) \
            if annotations.has_next else None
    prev_page = url_for("view_deleted_annotations", page=annotations.prev_num) \
            if annotations.has_prev else None
    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None
    return render_template("indexes/deleted_annotations.html",
            title="Deleted Annotations", annotations=annotations.items,
            prev_page=prev_page, next_page=next_page, uservotes=uservotes,
            sort=sort)

###################
## Book Requests ##
###################

@app.route("/list/book_requests/")
def book_request_index():
    page = request.args.get("page", 1, type=int)
    requests = BookRequest.query.order_by(BookRequest.weight.desc()
            ).paginate(page, app.config["CARDS_PER_PAGE"], False)
    next_page = url_for("book_request_index", page=requests.next_num) \
            if requests.has_next else None
    prev_page = url_for("book_request_index", page=requests.prev_num) \
            if requests.has_prev else None
    uservotes = current_user.get_book_request_vote_dict() \
            if current_user.is_authenticated else None
    return render_template("indexes/book_requests.html", title="Book Requests",
            next_page=next_page, prev_page=prev_page, requests=requests.items,
            uservotes=uservotes)

@app.route("/book_request/<book_request_id>/")
def view_book_request(book_request_id):
    book_request = BookRequest.query.get_or_404(book_request_id)
    return render_template("view/book_request.html", book_request=book_request)

@app.route("/request/book/", methods=["GET", "POST"])
@login_required
def book_request():
    current_user.authorize_rep(app.config["AUTHORIZATION"]["BOOK_REQUEST"])
    form = BookRequestForm()
    if form.cancel.data:
        return redirect(url_for("book_request_index"))
    if form.validate_on_submit():
        book_request = BookRequest(title=form.title.data,
                author=form.author.data, notes=form.notes.data,
                description=form.description.data,
                wikipedia=form.wikipedia.data, gutenberg=form.gutenberg.data,
                weight=0)
        db.session.add(book_request)
        book_request.upvote(current_user)
        db.session.commit()
        flash("Book request created and your vote has been applied.")
        return redirect(url_for("book_request_index"))
    return render_template("forms/book_request.html", title="Request Book",
            form=form)

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

##################
## Tag Requests ##
##################

@app.route("/list/tag_requests/")
def tag_request_index():
    page = request.args.get("page", 1, type=int)
    tag_requests = TagRequest.query.order_by(TagRequest.weight.desc()
            ).paginate(page, app.config["CARDS_PER_PAGE"], False)
    next_page = url_for("tag_request_index", page=tag_requests.next_num) \
            if tag_requests.has_next else None
    prev_page = url_for("tag_request_index", page=tag_requests.prev_num) \
            if tag_requests.has_prev else None
    uservotes = current_user.get_tag_request_vote_dict() \
            if current_user.is_authenticated else None
    return render_template("indexes/tag_requests.html", title="Tag Requests",
            next_page=next_page, prev_page=prev_page,
            tag_requests=tag_requests.items, uservotes=uservotes)

@app.route("/tag_request/<tag_request_id>/")
def view_tag_request(tag_request_id):
    tag_request = TagRequest.query.get_or_404(tag_request_id)
    return render_template("view/tag_request.html", tag_request=tag_request)

@app.route("/request/tag/", methods=["GET", "POST"])
@login_required
def tag_request():
    current_user.authorize_rep(app.config["AUTHORIZATION"]["TAG_REQUEST"])
    form = TagRequestForm()
    if form.cancel.data:
        return redirect(url_for("tag_request_index"))
    if form.validate_on_submit():
        tag_request = TagRequest(tag=form.tag.data,
                notes=form.notes.data, description=form.description.data,
                wikipedia=form.wikipedia.data, weight=0)
        db.session.add(tag_request)
        tag_request.upvote(current_user)
        db.session.commit()
        flash("Tag request created and your vote has been applied.")
        return redirect(url_for("tag_request_index"))
    return render_template("forms/tag_request.html", title="Request Tag",
            form=form)

@app.route("/edit/tag_request/<tag_request_id>/", methods=["GET", "POST"])
@login_required
def edit_tag_request(tag_request_id):
    current_user.authorize_rights("edit_tag_requests")
    tag_request = TagRequest.query.get_or_404(tag_request_id)
    form = TagRequestForm()
    if form.cancel.data:
        return redirect(url_for("view_tag_request",
            tag_request_id=tag_request_id))
    if form.validate_on_submit():
        tag_request.title = form.title.data
        tag_request.author = form.author.data
        tag_request.notes = form.notes.data
        tag_request.description = form.description.data
        tag_request.wikipedia = form.wikipedia.data
        tag_request.gutenberg = form.gutenberg.data
        db.session.commit()
        flash("Tag request edit complete.")
        return redirect(url_for("view_tag_request",
            tag_request_id=tag_request_id))
    else:
        form.title.data = tag_request.title
        form.author.data = tag_request.author
        form.notes.data = tag_request.notes
        form.description.data = tag_request.description
        form.wikipedia.data = tag_request.wikipedia
        form.gutenberg.data = tag_request.gutenberg
    return render_template("forms/tag_request.html", title="Edit Tag Request",
            form=form)

@app.route("/upvote/tag_request/<tag_request_id>/")
@login_required
def upvote_tag_request(tag_request_id):
    tag_request = TagRequest.query.get_or_404(tag_request_id)

    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = url_for("tag_request_index")

    if current_user.already_voted_tag_request(tag_request):
        vote = current_user.tag_request_ballots.filter(
                TagRequestVote.tag_request==tag_request).first()
        rd = True if vote.is_up() else False
        tag_request.rollback(vote)
        db.session.commit()
        if rd:
            return redirect(next_page)

    tag_request.upvote(current_user)
    db.session.commit()

    return redirect(next_page)

@app.route("/downvote/tag_request/<tag_request_id>/")
@login_required
def downvote_tag_request(tag_request_id):
    tag_request = TagRequest.query.get_or_404(tag_request_id)

    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = url_for("tag_request_index")

    if current_user.already_voted_tag_request(tag_request):
        vote = current_user.tag_request_ballots.filter(
                TagRequestVote.tag_request==tag_request).first()
        rd = True if not vote.is_up() else False
        tag_request.rollback(vote)
        db.session.commit()
        if rd:
            return redirect(next_page)

    tag_request.downvote(current_user)
    db.session.commit()

    return redirect(next_page)

@app.route("/admin/tags/create/", methods=["GET","POST"],
        defaults={"tag_request_id":None})
@app.route("/admin/tags/create/<tag_request_id>", methods=["GET","POST"])
@login_required
def create_tag(tag_request_id):
    current_user.authorize_rights("create_tags")
    tag_request = None
    if tag_request_id:
        tag_request = TagRequest.query.get_or_404(tag_request_id)
    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = url_for("tag_request_index")
    form = TagForm()
    if form.cancel.data:
        return redirect(next_page)
    if form.validate_on_submit():
        if form.tag.data != None and form.description.data != None:
            tag = Tag(tag=form.tag.data, description=form.description.data)
            db.session.add(tag)
            db.session.commit()
            flash("Tag created.")
            return redirect(next_page)
    elif tag_request:
            tag = Tag(tag=tag_request.tag, description=tag_request.description)
            tag_request.created_tag = tag
            tag_request.approved = True
            db.session.add(tag)
            db.session.commit()
            flash("Tag created.")
            return redirect(next_page)
    return render_template("forms/tag.html", title="Create Tag", form=form)

@app.route("/admin/tags/reject/<tag_request_id>")
@login_required
def reject_tag(tag_request_id):
    current_user.authorize_rights("create_tags")
    tag_request = TagRequest.query.get_or_404(tag_request_id)
    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = url_for("tag_request_index")
    tag_request.rejected = True
    db.session.commit()
    return redirect(next_page)

#######################
#######################
## ## Ajax Routes ## ##
#######################
#######################

@app.route("/autocomplete/tags/", methods=["POST"])
def ajax_tags():
    tagstr = request.form.get("tags")
    tags = tagstr.split()
    results = Tag.query.filter(Tag.tag.startswith(tags[-1])).all()
    if not results:
        return jsonify({"success": False, "tags": []})
    tag_list = {}
    for t in results:
        tag_list[t.tag] = t.description
    
    return jsonify({"success": True, "tags": tag_list})
