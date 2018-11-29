from collections import defaultdict
from datetime import datetime
import hashlib
from flask import render_template, flash, redirect, url_for, request, Markup, \
        abort, jsonify, g
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from sqlalchemy import or_, and_
from app import app, db
from app.models import User, Book, Author, Line, LineLabel, Annotation, \
        Edit, Tag, EditVote, Right, Vote, BookRequest, BookRequestVote, \
        TagRequest, TagRequestVote, UserFlag, AnnotationFlag, NotificationType,\
        NotificationEvent, tags as tags_table, UserFlagEvent, \
        AnnotationFlagEvent
from app.forms import LoginForm, RegistrationForm, AnnotationForm, \
        LineNumberForm, TagForm, LineForm, BookRequestForm, TagRequestForm, \
        EditProfileForm, ResetPasswordRequestForm, ResetPasswordForm, TextForm,\
        AreYouSureForm, SearchForm
from app.email import send_password_reset_email
from app.funky import preplines, is_filled, generate_next
import difflib
import re
import time

@app.before_request
def before_request():
    if current_user.is_authenticated and current_user.locked:
        logout_user()
    g.search_form = SearchForm()

@app.route("/search")
def search():
    if not g.search_form.validate():
        return redirect(url_for("index"))
    page = request.args.get("page", 1, type=int)
    lines, line_total = Line.search(g.search_form.q.data, page,
            app.config["LINES_PER_SEARCH_PAGE"])
    annotations, annotation_total = Annotation.search(g.search_form.q.data,
            page, app.config["ANNOTATIONS_PER_SEARCH_PAGE"])
    next_page = url_for("search", q=g.search_form.q.data, page=page + 1)\
        if line_total > page * app.config["LINES_PER_SEARCH_PAGE"]\
        or annotation_total > page * app.config["ANNOTATIONS_PER_SEARCH_PAGE"]\
        else None
    prev_page = url_for("search", q=g.search_form.q.data, page=page - 1) \
        if page > 1 else None
    return render_template("indexes/search.html", title="Search", lines=lines,
            line_total=line_total, annotations=annotations,
            annotation_total=annotation_total, next_page=next_page,
            prev_page=prev_page)

###########
## Index ##
###########

@app.route("/")
@app.route("/index/")
def index():
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "newest", type=str)

    if sort == "newest":
        annotations = Annotation.query.filter_by(active=True)\
                .order_by(Annotation.added.desc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "oldest":
        annotations = Annotation.query.filter_by(active=True)\
                .order_by(Annotation.added.asc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "modified":
        annotations = Annotation.query\
                .outerjoin(Edit,
                        and_(Annotation.id==Edit.annotation_id,
                            Edit.current==True))\
                .group_by(Annotation.id)\
                .order_by(Edit.modified.desc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "weight":
        annotations = Annotation.query.filter_by(active=True)\
                .order_by(Annotation.weight.desc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    else:
        annotations = Annotation.query.filter_by(active=True)\
                .order_by(Annotation.added.desc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)

    sorts = {
            "newest": url_for("index", page=page, sort="newest"),
            "oldest": url_for("index", page=page, sort="oldest"),
            "modified": url_for("index", page=page, sort="modified"),
            "weight": url_for("index", page=page, sort="weight"),
            }

    annotationflags = AnnotationFlag.query.all()
    next_page = url_for("index", page=annotations.next_num, sort=sort) \
            if annotations.has_next else None
    prev_page = url_for("index", page=annotations.prev_num, sort=sort) \
            if annotations.has_prev else None
    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None
    return render_template("indexes/annotation_list.html", title="Home",
            annotations=annotations.items, uservotes=uservotes,
            next_page=next_page, prev_page=prev_page,
            annotationflags=annotationflags, sort=sort, sorts=sorts)


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

        redirect_url = generate_next(url_for("index"))
        return redirect(redirect_url)

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
    if form.validate_on_submit():
        current_user.displayname = form.displayname.data\
                if is_filled(form.displayname.data)\
                else f"user{current_user.id}"
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash("Your changes have been saved.")
        return redirect(url_for("user", user_id=current_user.id))
    elif request.method == "GET":
        form.displayname.data = current_user.displayname
        form.about_me.data = current_user.about_me
    return render_template("forms/edit_profile.html", title="Edit Profile",
                           form=form)

@app.route("/user/inbox/")
@login_required
def inbox():
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "read", type=str)
    if sort == "time":
        notifications = current_user.notifications.\
                order_by(NotificationEvent.time.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time_invert":
        notifications = current_user.notifications\
                .order_by(NotificationEvent.time.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "type":
        notifications = current_user.notifications\
                .join(NotificationType).\
                order_by(NotificationType.code.desc(),
                        NotificationEvent.time.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "type_invert":
        notifications = current_user.notifications\
                .join(NotificationType)\
                .order_by(NotificationType.code.asc(),
                        NotificationEvent.time.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "information":
        notifications = current_user.notifications\
                .order_by(NotificationEvent.information.asc(),
                        NotificationEvent.time.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "information_invert":
        notifications = current_user.notifications\
                .order_by(NotificationEvent.information.desc(),
                        NotificationEvent.time.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    else:
        notifications = current_user.notifications\
                .order_by(NotificationEvent.seen.asc(),
                        NotificationEvent.time.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    sorts = {
            "read": url_for("inbox", sort="read", page=page),
            "read_invert": url_for("inbox", sort="read_invert", page=page),
            "time": url_for("inbox", sort="time", page=page),
            "time_invert": url_for("inbox", sort="time_invert", page=page),
            "type": url_for("inbox", sort="type", page=page),
            "type_invert": url_for("inbox", sort="type_invert", page=page),
            "information": url_for("inbox", sort="information", page=page),
            "information_invert": url_for("inbox", sort="information_invert",
                page=page),
            }

    next_page = url_for("inbox", page=notifications.next_num, sort=sort) \
            if notifications.has_next else None
    prev_page = url_for("inbox", page=notifications.prev_num, sort=sort) \
            if notifications.has_prev else None

    return render_template("indexes/inbox.html",
            notifications=notifications.items, page=page, sort=sort,
            sorts=sorts, next_page=next_page, prev_page=prev_page)

@app.route("/user/inbox/mark/<event_id>/")
@login_required
def mark_notification(event_id):
    redirect_url = generate_next(url_for("inbox"))
    notification = NotificationEvent.query.get_or_404(event_id)
    if notification.seen:
        notification.mark_unread()
    else:
        notification.mark_read()
    db.session.commit()
    return redirect(redirect_url)

@app.route("/user/inbox/mark/all/")
@login_required
def mark_all_read():
    redirect_url = generate_next(url_for("inbox"))
    notifications = current_user.new_notifications
    for notification in notifications:
        notification.mark_read()
    db.session.commit()
    return redirect(redirect_url)


@app.route("/user/reset/password/", methods=["GET", "POST"])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = ResetPasswordRequestForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
            flash("Check your email for the instructions to request your "
                    "password.")
            return redirect(url_for("login"))
        else:
            flash("Email not found.")

    return render_template("forms/reset_password_request.html", title="Reset "
            "Password", form=form)

@app.route("/user/reset/password/<token>/", methods=["GET", "POST"])
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

@app.route("/user/<user_id>/flag/<flag_id>/")
@login_required
def flag_user(flag_id, user_id):
    user = User.query.get_or_404(user_id)
    flag = UserFlag.query.get_or_404(flag_id)
    redirect_url = generate_next(url_for("user", user_id=user.id))
    user.flag(flag, current_user)
    db.session.commit()
    flash(f"User {user.displayname} flagged \"{flag.flag}\"")
    return redirect(redirect_url)

@app.route("/user/delete/account/", methods=["GET", "POST"])
@login_required
def delete_account_check():
    form = AreYouSureForm()
    redirect_url = generate_next(url_for("user", user_id=current_user.id))
    if form.validate_on_submit():
        current_user.displayname = f"x_user{current_user.id}"
        current_user.email = "{current_user.id}"
        current_user.password_hash = "***"
        current_user.about_me = ""
        db.session.commit()
        logout_user()
        flash("Account anonymized.")
        return redirect(redirect_url)

    text = f"""
You have clicked the link to delete your account. This page serves as a double
check to make sure that you’re really sure you want to delete your account. You
will not be able to undo this. Annopedia is not like Facebook. We don’t secretly
keep your personal information so you can reactivate your account later on. If
you delete it, it’s done.

Please note, however, that the account itself will not be expunged from our
database. Annopedia is a collaborative effort, and we therefore reserve the
right to retain all of your contributions. This deletion is an anonymization of
your account. Your display name, email address, and about me will all be erased
and anonymized. Every interaction you have ever made with the site will be
associated with an account which cannot be logged into and whose display name
will be `x_user_{current_user.id}` But you will never be able to log back in
and retrieve your account.

If you’re really sure about this, click the button “Yes, I’m sure.” Otherwise,
press back in your browser, or _close_ your browser, or even pull the power cord
from the back of your computer. Because if you click “Yes, I’m sure,” then your
account is gone.
    """
    return render_template("forms/delete_check.html", form=form,
            title="Are you sure?", text=text)

@app.route("/admin/user/<user_id>/delete/", methods=["GET", "POST"])
@login_required
def anonymize_user(user_id):
    form = AreYouSureForm()
    current_user.authorize("anonymize_users")
    user = User.query.get_or_404(user_id)
    redirect_url = url_for("user", user_id=user.id)
    if form.validate_on_submit():
        user.displayname = f"x_user{user.id}"
        user.email = f"{user.id}"
        user.password_hash = "***"
        user.about_me = ""
        db.session.commit()
        flash("Account anonymized.")
        return redirect(redirect_url)

    text = f"""
If you click submit you will forcibly anonymize this user ({user.displayname}).
    """
    return render_template("forms/delete_check.html", form=form,
            title="Are you sure?", text=text)
###################
## follow routes ##
###################

@app.route("/user/follow/book/<book_id>/")
@login_required
def follow_book(book_id):
    book = Book.query.get_or_404(book_id)
    redirect_url = generate_next(url_for("book", book_url=book.url))
    if book in current_user.followed_books:
        current_user.followed_books.remove(book)
    else:
        current_user.followed_books.append(book)
    db.session.commit()
    return redirect(redirect_url)

@app.route("/user/follow/book_request/<book_request_id>/")
@login_required
def follow_book_request(book_request_id):
    book_request = BookRequest.query.get_or_404(book_request_id)
    redirect_url = generate_next(url_for("view_book_request",
        book_request_id=book_request.id))
    if book_request.approved:
        flash("You cannot follow a book request that has already been approved.")
    if book_request in current_user.followed_book_requests:
        current_user.followed_book_requests.remove(book_request)
    else:
        current_user.followed_book_requests.append(book_request)
    db.session.commit()
    return redirect(redirect_url)

@app.route("/user/follow/author/<author_id>/")
@login_required
def follow_author(author_id):
    author = Author.query.get_or_404(author_id)
    redirect_url = generate_next(url_for("author", name=author.url))
    if author in current_user.followed_authors:
        current_user.followed_authors.remove(author)
    else:
        current_user.followed_authors.append(author)
    db.session.commit()
    return redirect(redirect_url)

@app.route("/user/follow/user/<user_id>/")
@login_required
def follow_user(user_id):
    user = User.query.get_or_404(user_id)
    redirect_url = url_for("user", user_id=user.id)
    if user == current_user:
        flash("You can't follow yourself.")
        redirect(redirect_url)
    elif user in current_user.followed_users:
        current_user.followed_users.remove(user)
    else:
        current_user.followed_users.append(user)
    db.session.commit()
    return redirect(redirect_url)

@app.route("/user/follow/tag/<tag_id>/")
@login_required
def follow_tag(tag_id):
    tag = Tag.query.get_or_404(tag_id)
    redirect_url = generate_next(url_for("tag", tag=tag.tag))
    if tag in current_user.followed_tags:
        current_user.followed_tags.remove(tag)
    else:
        current_user.followed_tags.append(tag)
    db.session.commit()
    return redirect(redirect_url)

@app.route("/user/follow/tag_request/<tag_request_id>/")
@login_required
def follow_tag_request(tag_request_id):
    tag_request = TagRequest.query.get_or_404(tag_request_id)
    redirect_url = generate_next(url_for("view_tag_request",
        tag_request_id=tag_request.id))
    if tag_request in current_user.followed_tag_requests:
        current_user.followed_tag_requests.remove(tag_request)
    else:
        current_user.followed_tag_requests.append(tag_request)
    db.session.commit()
    return redirect(redirect_url)

@app.route("/user/follow/annotation/<annotation_id>/")
@login_required
def follow_annotation(annotation_id):
    annotation = Annotation.query.get_or_404(annotation_id)

    redirect_url = generate_next(url_for("annotation",
        annotation_id=annotation.id))

    if not annotation.active:
        flash("You cannot follow deactivated annotations.")
        redirect(redirect_url)

    if annotation.annotator == current_user:
        flash("You cannot follow your own annotation.")
        redirect(redirect_url)
    elif annotation in current_user.followed_annotations:
        current_user.followed_annotations.remove(annotation)
    else:
        current_user.followed_annotations.append(annotation)
    db.session.commit()
    return redirect(redirect_url)

#############
## Indexes ##
#############

@app.route("/list/authors/")
def author_index():
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "last name", type=str)
    if sort == "last name":
        authors = Author.query\
                .order_by(Author.last_name.asc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "full name":
        authors = Author.query\
                .order_by(Author.name.asc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "oldest":
        authors = Author.query\
                .order_by(Author.birth_date.asc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "youngest":
        authors = Author.query\
                .order_by(Author.birth_date.desc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "books":
        authors = Author.query\
                .outerjoin(Book).group_by(Author.id)\
                .order_by(db.func.count(Book.id).desc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    else:
        authors = Author.query\
                .order_by(Author.last_name.asc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    sorts = {
            "last name": url_for("author_index", sort="last name", page=page),
            "name": url_for("author_index", sort="name", page=page),
            "oldest": url_for("author_index", sort="oldest", page=page),
            "youngest": url_for("author_index", sort="youngest", page=page),
            "books": url_for("author_index", sort="books", page=page),
            }

    next_page = url_for("author_index", page=authors.next_num, sort=sort) \
            if authors.has_next else None
    prev_page = url_for("author_index", page=authors.prev_num, sort=sort) \
            if authors.has_prev else None

    return render_template("indexes/authors.html", title="Authors",
            authors=authors.items, next_page=next_page, prev_page=prev_page,
            sorts=sorts, sort=sort)

@app.route("/list/books/")
def book_index():
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "title", type=str)
    if sort == "title":
        books = Book.query\
                .order_by(Book.sort_title.asc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "author":
        books = Book.query\
                .join(Author)\
                .order_by(Author.last_name.asc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "oldest":
        books = Book.query\
                .order_by(Book.published.asc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "newest":
        books = Book.query\
                .order_by(Book.published.desc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "length":
        books = Book.query\
                .outerjoin(Line).group_by(Book.id)\
                .order_by(db.func.count(Line.id).desc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "annotations":
        books = Book.query\
                .outerjoin(Annotation).group_by(Book.id)\
                .order_by(db.func.count(Annotation.id).desc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    else:
        books = Book.query.order_by(Book.sort_title.asc()
                ).paginate(page, app.config["CARDS_PER_PAGE"], False)

    sorts = {
            "title": url_for("book_index", sort="title", page=page),
            "author": url_for("book_index", sort="author", page=page),
            "oldest": url_for("book_index", sort="oldest", page=page),
            "newest": url_for("book_index", sort="newest", page=page),
            "length": url_for("book_index", sort="length", page=page),
            "annotations": url_for("book_index", sort="annotations", page=page),
    }

    next_page = url_for("book_index", page=books.next_num, sort=sort) \
            if books.has_next else None
    prev_page = url_for("book_index", page=books.prev_num, sort=sort) \
            if books.has_prev else None

    return render_template("indexes/books.html", title="Books",
            books=books.items, prev_page=prev_page, next_page=next_page,
            sorts=sorts, sort=sort)

@app.route("/list/tags/")
def tag_index():
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "tag", type=str)
    if sort == "tag":
        tags = Tag.query\
                .order_by(Tag.tag)\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "annotations":
        # This doesn't do anything but the same sort yet
        tags = Tag.query\
                .outerjoin(tags_table)\
                .outerjoin(Edit, and_(
                    Edit.id==tags_table.c.edit_id,
                    Edit.current==True))\
                .group_by(Tag.id)\
                .order_by(db.func.count(Edit.id).desc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    else:
        tags = Tag.query\
                .order_by(Tag.tag)\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)

    sorts = {
            "tag": url_for("tag_index", sort="tag", page=page),
            "annotations": url_for("tag_index", sort="annotations", page=page)
            }

    next_page = url_for("tag_index", page=tags.next_num, sort=sort) \
            if tags.has_next else None
    prev_page = url_for("tag_index", page=tags.prev_num, sort=sort) \
            if tags.has_prev else None
    return render_template("indexes/tags.html", title="Tags",
            tags=tags.items, next_page=next_page, prev_page=prev_page,
            sorts=sorts, sort=sort)

@app.route("/list/users/")
def user_index():
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "reputation", type=str)
    if sort == "reputation":
        users = User.query\
                .order_by(User.reputation.desc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "name":
        users = User.query\
                .order_by(User.displayname.asc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "annotations":
        users = User.query\
                .outerjoin(Annotation).group_by(User.id)\
                .order_by(db.func.count(Annotation.id).desc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "edits":
        users = User.query\
                .outerjoin(Edit,
                    and_(Edit.editor_id==User.id,
                        Edit.edit_num>0))\
                    .group_by(User.id)\
                    .order_by(db.func.count(Edit.id).desc())\
                    .paginate(page, app.config["CARDS_PER_PAGE"], False)
    else:
        users = User.query\
                .order_by(User.reputation.desc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    sorts = {
            "reputation": url_for("user_index", page=page, sort="reputation"),
            "name": url_for("user_index", page=page, sort="name"),
            "annotations": url_for("user_index", page=page, sort="annotations"),
            "edits": url_for("user_index", page=page, sort="edits"),
            }
    next_page = url_for("user_index", page=users.next_num, sort=sort) \
            if users.has_next else None
    prev_page = url_for("user_index", page=users.prev_num, sort=sort) \
            if users.has_prev else None
    return render_template("indexes/users.html", title="Users",
            users=users.items, next_page=next_page, prev_page=prev_page,
            sort=sort, sorts=sorts)


#######################
## Single Item Views ##
#######################

@app.route("/author/<name>/")
def author(name):
    author = Author.query.filter_by(url=name).first_or_404()
    return render_template("view/author.html", title=author.name, author=author)

@app.route("/author/<name>/annotations/")
def author_annotations(name):
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "weight", type=str)
    author = Author.query.filter_by(url=name).first_or_404()
    if sort == "newest":
        annotations = author.annotations\
                .order_by(Annotation.added.desc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "oldest":
        annotations = author.annotations\
                .order_by(Annotation.added.asc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "weight":
        annotations = author.annotations\
                .order_by(Annotation.weight.desc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    # tried to do sort==modified except it's totally buggy and I gotta sort
    # through the problems.
    else:
        annotations = author.annotations\
                .order_by(Annotation.added.desc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
        sort == "newest"

    sorts = {
            "newest": url_for("author_annotations", name=author.url,
                sort="newest", page=page),
            "oldest": url_for("author_annotations", name=author.url,
                sort="oldest", page=page),
            "weight": url_for("author_annotations", name=author.url,
                sort="weight", page=page),
            }

    annotationflags = AnnotationFlag.query.all()
    next_page = url_for("author_annotations", name=author.url, sort=sort,
            page=annotations.next_num) if annotations.has_next else None
    prev_page = url_for("author_annotations", name=author.url, sort=sort,
            page=annotations.prev_num) if annotations.has_prev else None
    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None
    return render_template("indexes/annotation_list.html",
            title=f"{author.name} - Annotations", annotations=annotations.items,
            sorts=sorts, sort=sort, next_page=next_page, prev_page=prev_page,
            annotationflags=annotationflags, uservotes=uservotes)

@app.route("/book/<book_url>/")
def book(book_url):
    book = Book.query.filter_by(url=book_url).first_or_404()

    # get the labels for each heierarchical chapter level
    labels = LineLabel.query.filter(LineLabel.label.startswith("lvl")).all()
    label_ids = [l.id for l in labels]


    # get all the heierarchical chapter lines
    hierarchy = book.lines.filter(Line.label_id.in_(label_ids))\
            .order_by(Line.line_num.asc()).all()

    return render_template("view/book.html", title=book.title, book=book,
            hierarchy=hierarchy)

@app.route("/book/<book_url>/annotations/")
def book_annotations(book_url):
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "weight", type=str)
    book = Book.query.filter_by(url=book_url).first_or_404()
    if sort == "newest":
        annotations = book.annotations\
                .order_by(Annotation.added.desc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "oldest":
        annotations = book.annotations\
                .order_by(Annotation.added.asc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "weight":
        annotations = book.annotations\
                .order_by(Annotation.weight.desc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "line":
        annotations = book.annotations\
                .outerjoin(Edit, and_(
                    Edit.annotation_id==Annotation.id,
                    Edit.current==True))\
                .order_by(Edit.last_line_num.asc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    else:
        annotations = book.annotations\
                .order_by(Annotation.added.desc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
        sort = "newest"
        
    annotationflags = AnnotationFlag.query.all()
    sorts = {
            "newest": url_for("book_annotations", book_url=book.url,
                sort="newest", page=page),
            "oldest": url_for("book_annotations", book_url=book.url,
                sort="oldest", page=page),
            "weight": url_for("book_annotations", book_url=book.url,
                sort="weight", page=page),
            "line": url_for("book_annotations", book_url=book.url, sort="line",
                page=page),
            }
    next_page = url_for("book_annotations", book_url=book.url, sort=sort,
            page=annotations.next_num) if annotations.has_next else None
    prev_page = url_for("book_annotations", book_url=book_url, sort=sort,
            page=annotations.prev_num) if annotations.has_prev else None
    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None
    return render_template("indexes/annotation_list.html",
            title=f"{book.title} - Annotations", annotations=annotations.items,
            sorts=sorts, sort=sort, next_page=next_page, prev_page=prev_page,
            annotationflags=annotationflags, uservotes=uservotes)

@app.route("/tag/<tag>/")
def tag(tag):
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "modified", type=str)
    tag = Tag.query.filter_by(tag=tag).first_or_404()
    if sort == "newest":
        annotations = tag.annotations\
                .order_by(Annotation.added.desc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "weight":
        annotations = tag.annotations\
                .order_by(Annotation.weight.desc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "oldest":
        annotations = tag.annotations\
                .order_by(Annotation.added.asc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "modified":
        annotations = tag.annotations\
                .order_by(Edit.modified.desc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    else:
        annotations = tag.annotations\
                .order_by(Annotation.added.desc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    sorts = {
            "newest": url_for("tag", tag=tag.tag, page=page, sort="newest"),
            "oldest": url_for("tag", tag=tag.tag, page=page, sort="oldest"),
            "weight": url_for("tag", tag=tag.tag, page=page, sort="weight"),
            "modified": url_for("tag", tag=tag.tag, page=page, sort="modified"),
            }
    annotationflags = AnnotationFlag.query.all()

    next_page = url_for("tag", tag=tag.tag, page=annotations.next_num,
            sort=sort) if annotations.has_next else None
    prev_page = url_for("tag", tag=tag.tag, page=annotations.prev_num,
            sort=sort) if annotations.has_prev else None

    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None

    return render_template("view/tag.html", title=tag.tag, tag=tag,
            annotations=annotations.items,
            next_page=next_page, prev_page=prev_page,
            annotationflags=annotationflags, sorts=sorts, sort=sort,
            uservotes=uservotes)

@app.route("/annotation/<annotation_id>/")
def annotation(annotation_id):
    annotation = Annotation.query.get_or_404(annotation_id)
    if not annotation.active:
        current_user.authorize("view_deactivated_annotations")

    annotationflags = AnnotationFlag.query.all()
    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None
    return render_template("view/annotation.html", title=annotation.book.title,
            annotation=annotation, uservotes=uservotes,
            annotationflags=annotationflags)

@app.route("/annotation/<annotation_id>/edit/history/")
def edit_history(annotation_id):
    annotation = Annotation.query.get_or_404(annotation_id)
    annotationflags = AnnotationFlag.query.all()

    if not annotation.active:
        current_user.authorize("view_deactivated_annotations")

    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "edit_num_invert", type=str)

    if sort == "edit_num":
        edits = annotation.history\
                .filter(Edit.approved==True)\
                .order_by(Edit.edit_num.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "edit_num_invert":
        edits = annotation.history\
                .filter(Edit.approved==True)\
                .order_by(Edit.edit_num.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "editor":
        edits = annotation.history.outerjoin(User)\
                .filter(Edit.approved==True)\
                .order_by(User.displayname.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "editor_invert":
        edits = annotation.history.outerjoin(User)\
                .filter(Edit.approved==True)\
                .order_by(User.displayname.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time":
        edits = annotation.history\
                .filter(Edit.approved==True)\
                .order_by(Edit.modified.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time_invert":
        edits = annotation.history\
                .filter(Edit.approved==True)\
                .order_by(Edit.modified.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "reason":
        edits = annotation.history\
                .filter(Edit.approved==True)\
                .order_by(Edit.edit_reason.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "reason_invert":
        edits = annotation.history\
                .filter(Edit.approved==True)\
                .order_by(Edit.edit_reason.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    else:
        edits = annotation.history\
                .outerjoin(EditVote,
                        and_(EditVote.user_id==current_user.id,
                            EditVote.edit_id==Edit.id)
                        )\
                .filter(Edit.approved==True)\
                .order_by(EditVote.delta.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
        sort = "voted"


    next_page = url_for("edit_review_queue", page=edits.next_num, sort=sort)\
            if edits.has_next else None
    prev_page = url_for("edit_review_queue", page=edits.prev_num, sort=sort)\
            if edits.has_prev else None

    return render_template("indexes/edit_history.html", title="Edit History",
            edits=edits.items, sort=sort, next_page=next_page,
            prev_page=prev_page, annotation=annotation, page=page)

@app.route("/annotation/<annotation_id>/edit/<edit_num>/")
def view_edit(annotation_id, edit_num):
    edit = Edit.query.filter(
            Edit.annotation_id==annotation_id,
            Edit.edit_num==edit_num,
            Edit.approved==True
            ).first_or_404()

    if not edit.previous:
        return render_template("view/first_version.html",
                title=f"First Version of [{edit.annotation.id}]", edit=edit)
    # we have to replace single returns with spaces because markdown only
    # recognizes paragraph separation based on two returns. We also have to be
    # careful to do this for both unix and windows return variants (i.e. be
    # careful of \r's).
    diff1 = re.sub(r"(?<!\n)\r?\n(?![\r\n])", " ", edit.previous.body)
    diff2 = re.sub(r"(?<!\n)\r?\n(?![\r\n])", " ", edit.body)

    diff = list(difflib.Differ().compare(diff1.splitlines(),
        diff2.splitlines()))
    tags = [tag for tag in edit.tags]
    for tag in edit.previous.tags:
        if tag not in tags:
            tags.append(tag)
    if edit.first_line_num > edit.previous.first_line_num:
        context = [line for line in edit.previous.context]
        for line in edit.context:
            if line not in context:
                context.append(line)
    else:
        context = [line for line in edit.context]
        for line in edit.previous.context:
            if line not in context:
                context.append(line)

    return render_template("view/edit.html", title=f"Edit number {edit.edit_num}",
            diff=diff, edit=edit, tags=tags, context=context)

@app.route("/user/<user_id>/")
def user(user_id):
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "newest", type=str)
    user = User.query.get_or_404(user_id)
    if sort == "weight":
        annotations = user.annotations.order_by(Annotation.weight.desc()
                ).paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "newest":
        annotations = user.annotations.order_by(Annotation.added.desc()
                ).paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "oldest":
        annotations = user.annotations.order_by(Annotation.added.asc()
                ).paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    else:
        annotations = user.annotations.order_by(Annotation.added.desc()
                ).paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)

    sorts = {
            "newest": url_for("user", user_id=user_id, sort="newest", page=page),
            "oldest": url_for("user", user_id=user_id, sort="oldest", page=page),
            "weight": url_for("user", user_id=user_id, sort="weight", page=page),
            }
    userflags = UserFlag.query.all()
    annotationflags = AnnotationFlag.query.all()

    next_page = url_for("user", user_id=user.id, page=annotations.next_num,
            sort=sort) if annotations.has_next else None
    prev_page = url_for("user", user_id=user.id, page=annotations.prev_num,
            sort=sort) if annotations.has_prev else None
    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None

    return render_template("view/user.html", title=f"User {user.displayname}",
            user=user, annotations=annotations.items, uservotes=uservotes,
            next_page=next_page, prev_page=prev_page, userflags=userflags,
            annotationflags=annotationflags, sort=sort, sorts=sorts)

####################
## Reading Routes ##
####################

@app.route("/read/<book_url>/", methods=["GET", "POST"])
def read(book_url):
    book = Book.query.filter_by(url=book_url).first_or_404()
    tag = request.args.get("tag", None, type=str)
    lvl = [request.args.get("l1", 0, type=int)]
    lvl.append(request.args.get("l2", 0, type=int))
    lvl.append(request.args.get("l3", 0, type=int))
    lvl.append(request.args.get("l4", 0, type=int))

    annotationflags = AnnotationFlag.query.all()

    if lvl[3]:
        lines = book.lines.filter(
                Line.lvl4==lvl[3], Line.lvl3==lvl[2],
                Line.lvl2==lvl[1], Line.lvl1==lvl[0]
                ).order_by(Line.line_num.asc()).all()
    elif lvl[2]:
        lines = book.lines.filter(
                Line.lvl3==lvl[2], Line.lvl2==lvl[1], Line.lvl1==lvl[0]
                ).order_by(Line.line_num.asc()).all()
    elif lvl[1]:
        lines = book.lines.filter(
                Line.lvl2==lvl[1], Line.lvl1==lvl[0]
                ).order_by(Line.line_num.asc()).all()
    elif lvl[0]:
        lines = book.lines.filter(
                Line.lvl1==lvl[0]
                ).order_by(Line.line_num.asc()).all()
    else:
        lines = book.lines.order_by(Line.line_num.asc()).all()

    if len(lines) <= 0:
        abort(404)

    form = LineNumberForm()

    next_page = lines[0].get_next_page()
    prev_page = lines[0].get_prev_page()

    if form.validate_on_submit():
        # line number boiler plate
        if not form.first_line.data and not form.last_line.data:
            flash("Please enter a first and last line number to annotate a selection.")
            return redirect(url_for("read", book_url=book.url, tag=tag,
                lvl1=lvl[0], lvl2=lvl[1], lvl3=lvl[2], lvl4=lvl[3]))
        elif not form.first_line.data:
            ll = int(form.last_line.data)
            fl = ll
        elif not form.last_line.data:
            fl = int(form.first_line.data)
            ll = fl
        else:
            fl = int(form.first_line.data)
            ll = int(form.last_line.data)

        if fl < 1:
            fl = 1
        if ll < 1:
            fl = 1
            ll = 1

        # redirect to annotate page, with next query param being the current
        # page. Multi-layered nested return statement. Read carefully.
        return redirect(url_for("annotate", book_url=book_url, first_line=fl,
            last_line=ll, next=request.full_path))

    # get all the annotations
    if tag:
        tag = Tag.query.filter_by(tag=tag).first_or_404()
        annotations = tag.annotations\
                .filter(Annotation.book_id==book.id,
                        Edit.first_line_num>=lines[0].line_num,
                        Edit.last_line_num<=lines[-1].line_num)\
                .all()
        tags = None
    else:
        annotations = book.annotations.join(Edit,
                and_(Edit.annotation_id==Annotation.id,
                    Edit.current==True))\
                .filter(Edit.last_line_num<=lines[-1].line_num,
                        Edit.first_line_num>=lines[0].line_num)\
                .all()
        # this query is like 5 times faster than the old double-for loop. I am,
        # however, wondering if some of the join conditions should be offloaded
        # into a filter
        tags = Tag.query.outerjoin(tags_table)\
                .join(Edit, and_(
                    Edit.id==tags_table.c.edit_id,
                    Edit.current==True,
                    Edit.book_id==book.id,
                    Edit.first_line_num>=lines[0].line_num,
                    Edit.last_line_num<=lines[-1].line_num)
                    )\
                .all()

    # index the annotations in a dictionary
    annotations_idx = defaultdict(list)
    for a in annotations:
        annotations_idx[a.HEAD.last_line_num].append(a)

    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None

    # I have to query this so I only make a db call once instead of each time
    # for every line to find out if the user has edit_rights
    if current_user.is_authenticated:
        can_edit_lines = current_user.is_authorized("edit_lines")
    else:
        can_edit_lines = False

    # This custom method for replacing underscores with <em> tags is still way
    # faster than the markdown converter. Since I'm not using anything other
    # than underscores for italics in the body of the actual text (e.g., I'm
    # using other methods to indicate blockquotes), I'll just keep using this.
    preplines(lines)

    return render_template("read.html", title=book.title, form=form, book=book,
            lines=lines, annotations_idx=annotations_idx, uservotes=uservotes,
            tags=tags, tag=tag, next_page=next_page, prev_page=prev_page,
            can_edit_lines=can_edit_lines, annotationflags=annotationflags)

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
    lines = book.lines.filter(Line.line_num>=first_line,
            Line.line_num<=last_line).all()
    context = book.lines.filter(Line.line_num>=int(first_line)-5,
            Line.line_num<=int(last_line)+5).all()
    form = AnnotationForm()

    if lines == None:
        abort(404)

    redirect_url = generate_next(lines[0].get_url())

    if form.validate_on_submit():
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

        locked = form.locked.data\
                and current_user.is_authorized("lock_annotations")

        # Create the annotation annotation with HEAD pointing to anno
        head = Annotation(book=book, annotator=current_user, locked=locked)

        # I'll use the language of git
        # Create the inital transient sqlalchemy Edit object
        commit = Edit(
                book=book, approved=True, current=True, editor=current_user,
                first_line_num=fl, last_line_num=ll,
                first_char_idx=form.first_char_idx.data,
                last_char_idx=form.last_char_idx.data,
                body=form.annotation.data, tags=tags, annotation=head,
                edit_reason="Initial version"
                )

        # because of the nature of the indexing system we have to create a
        # temporary attribute to the head of the body of the annotation.
        # Otherwise, since neither are committed to the system yet, the system
        # wants to make a query to the system for the head's HEAD attribute,
        # which isn't in existence yet. Adding this simple attribute eliminates
        # the issue.
        head.body = commit.body

        db.session.add(commit)
        db.session.add(head)
        db.session.commit()

        # notify all the watchers
        head.notify_new()
        db.session.commit()

        flash("Annotation Submitted")

        return redirect(redirect_url)
    else:
        form.first_line.data = first_line
        form.last_line.data = last_line
        form.first_char_idx.data = 0
        form.last_char_idx.data = -1

    return render_template("forms/annotation.html", title=book.title, form=form,
             book=book, lines=lines, context=context)

@app.route("/edit/<annotation_id>/", methods=["GET", "POST"])
@login_required
def edit(annotation_id):
    annotation = Annotation.query.get_or_404(annotation_id)

    redirect_url = generate_next(url_for("annotation",
        annotation_id=annotation_id))

    if annotation.locked == True\
            and not current_user.is_authorized("edit_locked_annotations"):
        flash("That annotation is locked from editing.")
        return redirect(redirect_url)
    elif not annotation.active:
        current_user.authorize("edit_deactivated_annotations")

    lines = annotation.lines
    context = annotation.context
    form = AnnotationForm()

    if form.validate_on_submit():
        # line number boilerplate
        fl = int(form.first_line.data)
        ll = int(form.last_line.data)
        if fl < 1:
            fl = 1
        if ll < 1:
            fl = 1
            ll = 1
        if ll < fl:
            tmp = ll
            ll = fl
            fl = tmp

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

        if len(tags) > 5:
            fail = True
            flash("There is a five tag limit.")


        # approved is true if the user can edit immediately
        approved = current_user.is_authorized("immediate_edits")\
                or annotation.annotator == current_user

        lockchange = False
        if current_user.is_authorized("lock_annotations"):
            # the lock changes if the annotation's lock value is different from
            # the form's locked data. We have to specify this because this won't
            # show up in edit's hash_id and will fail the uniqueness test.
            lockchange = annotation.locked != form.locked.data
            annotation.locked = form.locked.data

        # if a reason isn't provided and there's no lockchange, fail the
        # submission
        if not form.reason.data and not lockchange:
            flash("Please provide a reason for your edit.")
            fail = True


        edit_num = int(annotation.HEAD.edit_num+1) if annotation.HEAD.edit_num\
                else 1
        # both the approved and current variables are based on approved
        edit = Edit(book=annotation.book,
                editor_id=current_user.id, edit_num=edit_num,
                edit_reason=form.reason.data, annotation_id=annotation_id,
                approved=approved, current=approved,
                first_line_num=fl, last_line_num=ll,
                first_char_idx=form.first_char_idx.data,
                last_char_idx=form.last_char_idx.data,
                body=form.annotation.data, tags=tags,
                )

        if edit.hash_id == annotation.HEAD.hash_id and not lockchange:
            flash("Your suggested edit is no different from the previous version.")
            fail = True

        lockchangenotedit = False

        if fail:
            return render_template("forms/annotation.html",
                    title=annotation.HEAD.book.title, form=form,
                    book=annotation.HEAD.book, lines=lines,
                    annotation=annotation)
        elif edit.hash_id == annotation.HEAD.hash_id and lockchange:
            flash("Annotation Locked")
            lockchangenotedit = True
        else:
            annotation.edit_pending = not approved
            if approved:
                annotation.HEAD.current = False
                edit.current = True
                flash("Edit complete.")
            else:
                flash("Edit submitted for review.")
            db.session.add(edit)

        db.session.commit()
        if approved and not lockchangenotedit:
            edit.notify_edit("approved")
        if lockchange:
            annotation.notify_lockchange()
        db.session.commit()

        return redirect(redirect_url)

    elif not annotation.edit_pending:
        tag_strings = []
        for t in annotation.HEAD.tags:
            tag_strings.append(t.tag)
        form.first_line.data = annotation.HEAD.first_line_num
        form.last_line.data = annotation.HEAD.last_line_num
        form.first_char_idx.data = annotation.HEAD.first_char_idx
        form.last_char_idx.data = annotation.HEAD.last_char_idx
        form.annotation.data = annotation.HEAD.body
        form.tags.data = " ".join(tag_strings)
        form.locked.data = annotation.locked

    return render_template("forms/annotation.html",
            title=f"Edit Annotation {annotation.id}", form=form,
            book=annotation.HEAD.book, lines=lines,
            annotation=annotation, context=context)

@app.route("/rollback/<annotation_id>/edit/<edit_id>/", methods=["GET", "POST"])
@login_required
def rollback(annotation_id, edit_id):
    annotation = Annotation.query.get_or_404(annotation_id)
    edit = Edit.query.get_or_404(edit_id)

    redirect_url = generate_next(url_for("edit_history",
        annotation_id=annotation.id))

    if annotation.locked == True\
            and not current_user.is_authorized("edit_locked_annotations"):
        flash("That annotation is locked from editing.")
        return redirect(redirect_url)
    elif not annotation.active:
        current_user.authorize("edit_deactivated_annotations")

    if annotation.HEAD == edit:
        flash("You can't roll back an annotation to its current version.")
        return redirect(redirect_url)

    lines = annotation.lines
    context = annotation.context
    form = AnnotationForm()

    if form.validate_on_submit():
        # line number boilerplate
        fl = int(form.first_line.data)
        ll = int(form.last_line.data)
        if fl < 1:
            fl = 1
        if ll < 1:
            fl = 1
            ll = 1
        if ll < fl:
            tmp = ll
            ll = fl
            fl = tmp

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

        if len(tags) > 5:
            fail = True
            flash("There is a five tag limit.")


        # approved is true if the user can edit immediately
        approved = current_user.is_authorized("immediate_edits")\
                or annotation.annotator == current_user

        lockchange = False
        if current_user.is_authorized("lock_annotations"):
            # the lock changes if the annotation's lock value is different from
            # the form's locked data. We have to specify this because this won't
            # show up in edit's hash_id and will fail the uniqueness test.
            lockchange = annotation.locked != form.locked.data
            annotation.locked = form.locked.data

        # if a reason isn't provided and there's no lockchange, fail the
        # submission
        if not form.reason.data and not lockchange:
            flash("Please provide a reason for your edit.")
            fail = True


        edit_num = int(annotation.HEAD.edit_num+1) if annotation.HEAD.edit_num\
                else 1
        # both the approved and current variables are based on approved
        edit = Edit(book=annotation.book,
                editor_id=current_user.id, edit_num=edit_num,
                edit_reason=form.reason.data, annotation_id=annotation_id,
                approved=approved, current=approved,
                first_line_num=fl, last_line_num=ll,
                first_char_idx=form.first_char_idx.data,
                last_char_idx=form.last_char_idx.data,
                body=form.annotation.data, tags=tags,
                )

        if edit.hash_id == annotation.HEAD.hash_id and not lockchange:
            flash("Your suggested edit is no different from the previous version.")
            fail = True

        lockchangenotedit = False

        if fail:
            return render_template("forms/annotation.html",
                    title=annotation.HEAD.book.title, form=form,
                    book=annotation.HEAD.book, lines=lines,
                    annotation=annotation)
        elif edit.hash_id == annotation.HEAD.hash_id and lockchange:
            flash("Annotation Locked")
            lockchangenotedit = True
        else:
            annotation.edit_pending = not approved
            if approved:
                annotation.HEAD.current = False
                edit.current = True
                flash("Edit complete.")
            else:
                flash("Edit submitted for review.")
            db.session.add(edit)

        db.session.commit()
        if approved and not lockchangenotedit:
            edit.notify_edit("approved")
        if lockchange:
            annotation.notify_lockchange()
        db.session.commit()

        return redirect(redirect_url)

    elif not annotation.edit_pending:
        tag_strings = []
        for t in edit.tags:
            tag_strings.append(t.tag)
        form.first_line.data = edit.first_line_num
        form.last_line.data = edit.last_line_num
        form.first_char_idx.data = edit.first_char_idx
        form.last_char_idx.data = edit.last_char_idx
        form.annotation.data = edit.body
        form.tags.data = " ".join(tag_strings)
        form.locked.data = annotation.locked
        form.reason.data = f"Rollback to edit #{edit.edit_num}"

    return render_template("forms/annotation.html",
            title=f"Edit Annotation {annotation.id}", form=form,
            book=annotation.HEAD.book, lines=lines,
            annotation=annotation, context=context)

@app.route("/upvote/<annotation_id>/")
@login_required
def upvote(annotation_id):
    annotation = Annotation.query.get_or_404(annotation_id)
    redirect_url = generate_next(url_for("annotation",
        annotation_id=annotation_id))
    if not annotation.active:
        flash("You cannot vote on deactivated annotations.")
        return redirect(redirect_url)
    if current_user == annotation.annotator:
        flash("You cannot vote on your own annotations.")
        return redirect(redirect_url)
    elif current_user.already_voted(annotation):
        vote = current_user.ballots.filter(Vote.annotation==annotation).first()
        diff = datetime.utcnow() - vote.time
        if diff.days > 0 and annotation.HEAD.modified < vote.time:
            flash("Your vote is locked until the annotation is modified.")
            return redirect(redirect_url)
        elif vote.is_up():
            annotation.rollback(vote)
            db.session.commit()
            return redirect(redirect_url)
        else:
            annotation.rollback(vote)
    annotation.upvote(current_user)
    db.session.commit()
    return redirect(redirect_url)

@app.route("/downvote/<annotation_id>/")
@login_required
def downvote(annotation_id):
    annotation = Annotation.query.get_or_404(annotation_id)
    redirect_url = generate_next(url_for("annotation",
        annotation_id=annotation_id))
    if not annotation.active:
        flash("You cannot vote on deactivated annotations.")
    if current_user == annotation.annotator:
        flash("You cannot vote on your own annotation.")
        return redirect(redirect_url)
    elif current_user.already_voted(annotation):
        vote = current_user.ballots.filter(Vote.annotation==annotation).first()
        diff = datetime.utcnow() - vote.time
        if diff.days > 0 and annotation.HEAD.modified < vote.time:
            flash("Your vote is locked until the annotation is modified.")
            return redirect(redirect_url)
        elif not vote.is_up():
            annotation.rollback(vote)
            db.session.commit()
            return redirect(redirect_url)
        else:
            annotation.rollback(vote)

    annotation.downvote(current_user)
    db.session.commit()

    return redirect(redirect_url)

@app.route("/annotation/<annotation_id>/flag/<flag_id>/")
@login_required
def flag_annotation(flag_id, annotation_id):
    annotation = Annotation.query.get_or_404(annotation_id)
    if not annotation.active:
        current_user.authorize("view_deactivated_annotations")
    flag = AnnotationFlag.query.get_or_404(flag_id)

    redirect_url = generate_next(url_for("annotation",
        annotation_id=annotation.id))

    annotation.flag(flag, current_user)
    db.session.commit()
    flash(f"Annotation {annotation.id} flagged \"{flag.flag}\"")
    return redirect(redirect_url)

#################################
#################################
## ## Administration Routes ## ##
#################################
#################################

@app.route("/admin/lock/user/<user_id>/")
@login_required
def lock_user(user_id):
    current_user.authorize("lock_users")
    user = User.query.get_or_404(user_id)
    redirect_url = generate_next(url_for("user", user_id=user.id))
    user.locked = not user.locked
    db.session.commit()
    flash(f"User account {user.displayname} locked.")
    return redirect(redirect_url)

# annotation flags
@app.route("/admin/flags/annotation/all/")
@login_required
def all_annotation_flags():
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "marked", type=str)
    current_user.authorize("resolve_annotation_flags")

    if sort == "marked":
        flags = AnnotationFlagEvent.query\
                .order_by(AnnotationFlagEvent.resolved.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "marked_invert":
        flags = AnnotationFlagEvent.query\
                .order_by(AnnotationFlagEvent.resolved.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "flag":
        flags = AnnotationFlagEvent.query\
                .outerjoin(AnnotationFlag)\
                .order_by(AnnotationFlag.flag.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "flag_invert":
        flags = AnnotationFlagEvent.query\
                .outerjoin(AnnotationFlag)\
                .order_by(AnnotationFlag.flag.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time":
        flags = AnnotationFlagEvent.query\
                .order_by(AnnotationFlagEvent.time_thrown.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time_invert":
        flags = AnnotationFlagEvent.query\
                .order_by(AnnotationFlagEvent.time_thrown.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "thrower":
        flags = AnnotationFlagEvent.query\
                .outerjoin(User, User.id==AnnotationFlagEvent.thrower_id)\
                .order_by(User.displayname.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "thrower_invert":
        flags = AnnotationFlagEvent.query\
                .outerjoin(User, User.id==AnnotationFlagEvent.thrower_id)\
                .order_by(User.displayname.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "resolver":
        flags = AnnotationFlagEvent.query\
                .outerjoin(User, User.id==AnnotationFlagEvent.resolved_by)\
                .order_by(User.displayname.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "resolver_invert":
        flags = AnnotationFlagEvent.query\
                .outerjoin(User, User.id==AnnotationFlagEvent.resolved_by)\
                .order_by(User.displayname.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "resolved_at":
        flags = AnnotationFlagEvent.query\
                .order_by(AnnotationFlagEvent.resolved.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "resolved_at_invert":
        flags = AnnotationFlagEvent.query\
                .order_by(AnnotationFlagEvent.resolved.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "annotation":
        flags = AnnotationFlagEvent.query\
                .order_by(AnnotationFlagEvent.annotation_id.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "annotation_invert":
        flags = AnnotationFlagEvent.query\
                .order_by(AnnotationFlagEvent.annotation_id.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "book":
        flags = AnnotationFlagEvent.query\
                .outerjoin(Annotation,
                        Annotation.id==AnnotationFlagEvent.annotation_id)\
                .outerjoin(Book, Book.id==Annotation.book_id)\
                .order_by(Book.sort_title)\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    else:
        flags = AnnotationFlagEvent.query\
                .order_by(AnnotationFlagEvent.resolved.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    sorts = {
            "marked": url_for("all_annotation_flags", sort="marked", page=page),
            "marked_invert": url_for("all_annotation_flags",
                sort="marked_invert", page=page),

            "flag": url_for("all_annotation_flags", sort="flag", page=page),
            "flag_invert": url_for("all_annotation_flags", sort="flag_invert",
                page=page),

            "time": url_for("all_annotation_flags", sort="time", page=page),
            "time_invert": url_for("all_annotation_flags", sort="time_invert",
                page=page),

            "thrower": url_for("all_annotation_flags", sort="thrower",
                page=page),
            "thrower_invert": url_for("all_annotation_flags",
                sort="thrower_invert", page=page),

            "resolver": url_for("all_annotation_flags", sort="resolver",
                page=page),
            "resolver_invert": url_for("all_annotation_flags",
                sort="resolver_invert", page=page),

            "resolved_at": url_for("all_annotation_flags", sort="resolved_at",
                page=page),
            "resolved_at_invert": url_for("all_annotation_flags",
                sort="resolved_at_invert", page=page),

            "annotation": url_for("all_annotation_flags", sort="annotation",
                page=page),
            "annotation_invert": url_for("all_annotation_flags",
                sort="annotation_invert", page=page),

            "book": url_for("all_annotation_flags", sort="book", page=page),
            "book_invert": url_for("all_annotation_flags", sort="book_invert",
                page=page),
            }

    next_page = url_for("annotation_flags", annotation_id=annotation.id,
            page=flags.next_num, sort=sort) if flags.has_next else None
    prev_page = url_for("annotation_flags", annotation_id=annotation.id,
            page=flags.prev_num, sort=sort) if flags.has_prev else None
    return render_template("indexes/all_annotation_flags.html",
            title=f"Annotation Flags", flags=flags.items, sort=sort,
            sorts=sorts, next_page=next_page, prev_page=prev_page)

# annotation flags
@app.route("/admin/flags/annotation/<annotation_id>/")
@login_required
def annotation_flags(annotation_id):
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "marked", type=str)
    current_user.authorize("resolve_annotation_flags")
    if not annotation.active:
        current_user.authorize("resolve_deactivated_annotation_flags")
    annotation = Annotation.query.get_or_404(annotation_id)

    if sort == "marked":
        flags = annotation.flag_history\
                .order_by(AnnotationFlagEvent.resolved.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "marked_invert":
        flags = annotation.flag_history\
                .order_by(AnnotationFlagEvent.resolved.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    elif sort == "flag":
        flags = annotation.flag_history\
                .outerjoin(AnnotationFlag)\
                .order_by(AnnotationFlag.flag.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "flag_invert":
        flags = annotation.flag_history\
                .outerjoin(AnnotationFlag)\
                .order_by(AnnotationFlag.flag.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    elif sort == "time":
        flags = annotation.flag_history\
                .order_by(AnnotationFlagEvent.time_thrown.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time_invert":
        flags = annotation.flag_history\
                .order_by(AnnotationFlagEvent.time_thrown.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    elif sort == "thrower":
        flags = annotation.flag_history\
                .outerjoin(User, User.id==AnnotationFlagEvent.thrower_id)\
                .order_by(User.displayname.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "thrower_invert":
        flags = annotation.flag_history\
                .outerjoin(User, User.id==AnnotationFlagEvent.thrower_id)\
                .order_by(User.displayname.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    elif sort == "resolver":
        flags = annotation.flag_history\
                .outerjoin(User, User.id==AnnotationFlagEvent.resolved_by)\
                .order_by(User.displayname.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "resolver_invert":
        flags = annotation.flag_history\
                .outerjoin(User, User.id==AnnotationFlagEvent.resolved_by)\
                .order_by(User.displayname.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    elif sort == "resolved_at":
        flags = annotation.flag_history\
                .order_by(AnnotationFlagEvent.resolved.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "resolved_at_invert":
        flags = annotation.flag_history\
                .order_by(AnnotationFlagEvent.resolved.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    else:
        flags = annotation.flag_history\
                .order_by(AnnotationFlagEvent.resolved.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    sorts = {
            "marked": url_for("annotation_flags", annotation_id=annotation.id,
                sort="marked", page=page),
            "marked_invert": url_for("annotation_flags",
                annotation_id=annotation.id, sort="marked_invert", page=page),

            "flag": url_for("annotation_flags", annotation_id=annotation.id,
                sort="flag", page=page),
            "flag_invert": url_for("annotation_flags",
                annotation_id=annotation.id, sort="flag_invert", page=page),

            "time": url_for("annotation_flags", annotation_id=annotation.id,
                sort="time", page=page),
            "time_invert": url_for("annotation_flags",
                annotation_id=annotation.id, sort="time_invert", page=page),

            "thrower": url_for("annotation_flags", annotation_id=annotation.id,
                sort="thrower", page=page),
            "thrower_invert": url_for("annotation_flags",
                annotation_id=annotation.id, sort="thrower_invert", page=page),

            "resolver": url_for("annotation_flags", annotation_id=annotation.id,
                sort="resolver", page=page),
            "resolver_invert": url_for("annotation_flags",
                annotation_id=annotation.id, sort="resolver_invert", page=page),

            "resolved_at": url_for("annotation_flags",
                annotation_id=annotation.id, sort="resolved_at", page=page),
            "resolved_at_invert": url_for("annotation_flags",
                annotation_id=annotation.id, sort="resolved_at_invert",
                page=page),
            }

    next_page = url_for("annotation_flags", annotation_id=annotation.id,
            page=flags.next_num, sort=sort) if flags.has_next else None
    prev_page = url_for("annotation_flags", annotation_id=annotation.id,
            page=flags.prev_num, sort=sort) if flags.has_prev else None
    return render_template("indexes/annotation_flags.html",
            title=f"Annotation {annotation.id} flags", annotation=annotation,
            flags=flags.items, sort=sort, sorts=sorts, next_page=next_page,
            prev_page=prev_page)

@app.route("/admin/flags/annotation/mark/<flag_id>/")
@login_required
def mark_annotation_flag(flag_id):
    current_user.authorize("resolve_annotation_flags")
    flag = AnnotationFlagEvent.query.get_or_404(flag_id)
    redirect_url = generate_next(url_for("annotation_flags",
        annotation_id=flag.annotation_id))
    if flag.resolved:
        flag.unresolve()
    else:
        flag.resolve(current_user)
    db.session.commit()
    return redirect(redirect_url)

@app.route("/admin/flags/annotation/<annotation_id>/mark/all/")
@login_required
def mark_annotation_flags(annotation_id):
    current_user.authorize("resolve_annotation_flags")
    annotation = Annotation.query.get_or_404(annotation_id)
    if not annotation.active:
        current_user.authorize("resolve_deactivated_annotation_flags")
    redirect_url = generate_next(url_for("annotation_flags",
        annotation_id=annotation_id))
    for flag in annotation.active_flags:
        flag.resolve(current_user)
    db.session.commit()
    return redirect(redirect_url)

# user flags
@app.route("/admin/flags/user/all/")
@login_required
def all_user_flags():
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "marked", type=str)
    current_user.authorize("resolve_user_flags")

    if sort == "marked":
        flags = UserFlagEvent.query\
                .order_by(UserFlagEvent.resolved.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "marked_invert":
        flags = UserFlagEvent.query\
                .order_by(UserFlagEvent.resolved.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    elif sort == "flag":
        flags = UserFlagEvent.query\
                .outerjoin(UserFlag)\
                .order_by(UserFlag.flag.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "flag_invert":
        flags = UserFlagEvent.query\
                .outerjoin(UserFlag)\
                .order_by(UserFlag.flag.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    elif sort == "time":
        flags = UserFlagEvent.query\
                .order_by(UserFlagEvent.time_thrown.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time_invert":
        flags = UserFlagEvent.query\
                .order_by(UserFlagEvent.time_thrown.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    elif sort == "thrower":
        flags = UserFlagEvent.query\
                .outerjoin(User, User.id==UserFlagEvent.thrower_id)\
                .order_by(User.displayname.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "thrower_invert":
        flags = UserFlagEvent.query\
                .outerjoin(User, User.id==UserFlagEvent.thrower_id)\
                .order_by(User.displayname.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    elif sort == "resolver":
        flags = UserFlagEvent.query\
                .outerjoin(User, User.id==UserFlagEvent.resolved_by)\
                .order_by(User.displayname.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "resolver_invert":
        flags = UserFlagEvent.query\
                .outerjoin(User, User.id==UserFlagEvent.resolved_by)\
                .order_by(User.displayname.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    elif sort == "resolved_at":
        flags = UserFlagEvent.query\
                .order_by(UserFlagEvent.resolved.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "resolved_at_invert":
        flags = UserFlagEvent.query\
                .order_by(UserFlagEvent.resolved.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    elif sort == "user":
        flags = UserFlagEvent.query\
                .outerjoin(User, User.id==UserFlagEvent.user_id)\
                .order_by(User.displayname.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "user_invert":
        flags = UserFlagEvent.query\
                .outerjoin(User, User.id==UserFlagEvent.user_id)\
                .order_by(User.displayname.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    else:
        flags = UserFlagEvent.query\
                .order_by(UserFlagEvent.resolved.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    sorts = {
            "marked": url_for("all_user_flags", sort="marked", page=page),
            "marked_invert": url_for("all_user_flags", sort="marked_invert",
                page=page),

            "flag": url_for("all_user_flags", sort="flag", page=page),
            "flag_invert": url_for("all_user_flags", sort="flag_invert",
                page=page),

            "time": url_for("all_user_flags", sort="time", page=page),
            "time_invert": url_for("all_user_flags", sort="time_invert",
                page=page),

            "thrower": url_for("all_user_flags", sort="thrower", page=page),
            "thrower_invert": url_for("all_user_flags", sort="thrower_invert",
                page=page),

            "resolver": url_for("all_user_flags", sort="resolver", page=page),
            "resolver_invert": url_for("all_user_flags", sort="resolver_invert",
                page=page),

            "resolved_at": url_for("all_user_flags", sort="resolved_at",
                page=page),
            "resolved_at_invert": url_for("all_user_flags",
                sort="resolved_at_invert", page=page),

            "user": url_for("all_user_flags", sort="user", page=page),
            "user_invert": url_for("all_user_flags", sort="user_invert",
                page=page),
            }

    next_page = url_for("all_user_flags", page=flags.next_num, sort=sort) \
            if flags.has_next else None
    prev_page = url_for("all_user_flags", page=flags.prev_num, sort=sort) \
            if flags.has_prev else None
    return render_template("indexes/all_user_flags.html",
            title=f"User Flags", flags=flags.items, sort=sort, sorts=sorts,
            next_page=next_page, prev_page=prev_page)

# user flags
@app.route("/admin/flags/user/<user_id>/")
@login_required
def user_flags(user_id):
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "marked", type=str)
    current_user.authorize("resolve_user_flags")
    user = User.query.get_or_404(user_id)
    if sort == "marked":
        flags = user.flag_history\
                .order_by(UserFlagEvent.resolved.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "marked_invert":
        flags = user.flag_history\
                .order_by(UserFlagEvent.resolved.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    elif sort == "flag":
        flags = user.flag_history\
                .outerjoin(UserFlag)\
                .order_by(UserFlag.flag.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "flag_invert":
        flags = user.flag_history\
                .outerjoin(UserFlag)\
                .order_by(UserFlag.flag.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    elif sort == "time":
        flags = user.flag_history\
                .order_by(UserFlagEvent.time_thrown.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time_invert":
        flags = user.flag_history\
                .order_by(UserFlagEvent.time_thrown.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    elif sort == "thrower":
        flags = user.flag_history\
                .outerjoin(User, User.id==UserFlagEvent.thrower_id)\
                .order_by(User.displayname.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "thrower_invert":
        flags = user.flag_history\
                .outerjoin(User, User.id==UserFlagEvent.thrower_id)\
                .order_by(User.displayname.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    elif sort == "resolver":
        flags = user.flag_history\
                .outerjoin(User, User.id==UserFlagEvent.resolved_by)\
                .order_by(User.displayname.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "resolver_invert":
        flags = user.flag_history\
                .outerjoin(User, User.id==UserFlagEvent.resolved_by)\
                .order_by(User.displayname.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    elif sort == "resolved_at":
        flags = user.flag_history\
                .order_by(UserFlagEvent.resolved.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "resolved_at_invert":
        flags = user.flag_history\
                .order_by(UserFlagEvent.resolved.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    else:
        flags = user.flag_history\
                .order_by(UserFlagEvent.resolved.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    sorts = {
            "marked": url_for("user_flags", user_id=user.id, sort="marked",
                page=page),
            "marked_invert": url_for("user_flags", user_id=user.id,
                sort="marked_invert", page=page),

            "flag": url_for("user_flags", user_id=user.id, sort="flag",
                page=page),
            "flag_invert": url_for("user_flags", user_id=user.id,
                sort="flag_invert", page=page),

            "time": url_for("user_flags", user_id=user.id, sort="time",
                page=page),
            "time_invert": url_for("user_flags", user_id=user.id,
                sort="time_invert", page=page),

            "thrower": url_for("user_flags", user_id=user.id, sort="thrower",
                page=page),
            "thrower_invert": url_for("user_flags", user_id=user.id,
                sort="thrower_invert", page=page),

            "resolver": url_for("user_flags", user_id=user.id, sort="resolver",
                page=page),
            "resolver_invert": url_for("user_flags", user_id=user.id,
                sort="resolver_invert", page=page),

            "resolved_at": url_for("user_flags", user_id=user.id,
                sort="resolved_at", page=page),
            "resolved_at_invert": url_for("user_flags", user_id=user.id,
                sort="resolved_at_invert", page=page),
            }

    next_page = url_for("user_flags", user_id=user.id, page=flags.next_num,
            sort=sort) if flags.has_next else None
    prev_page = url_for("user_flags", user_id=user.id, page=flags.prev_num,
            sort=sort) if flags.has_prev else None
    return render_template("indexes/user_flags.html",
            title=f"{user.displayname} flags", user=user, flags=flags.items,
            sort=sort, sorts=sorts, next_page=next_page, prev_page=prev_page)

@app.route("/admin/flags/mark/user_flag/<flag_id>/")
@login_required
def mark_user_flag(flag_id):
    current_user.authorize("resolve_user_flags")
    flag = UserFlagEvent.query.get_or_404(flag_id)
    redirect_url = generate_next(url_for("user_flags", user_id=flag.user_id))
    if flag.resolved:
        flag.unresolve()
    else:
        flag.resolve(current_user)
    db.session.commit()
    return redirect(redirect_url)

@app.route("/admin/flags/mark_all/<user_id>/")
@login_required
def mark_user_flags(user_id):
    current_user.authorize("resolve_user_flags")
    user = User.query.get_or_404(user_id)
    redirect_url = generate_next(url_for("user_flags", user_id=user.id))
    for flag in user.active_flags:
        flag.resolve(current_user)
    db.session.commit()
    return redirect(redirect_url)

#################
## Edit Review ##
#################

@app.route("/admin/edits/")
@login_required
def edit_review_queue():
    current_user.authorize("review_edits")
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "voted", type=str)

    if sort == "voted":
        edits = Edit.query\
                .outerjoin(EditVote,
                        and_(EditVote.user_id==current_user.id,
                            EditVote.edit_id==Edit.id)
                        )\
                .filter(Edit.approved==False,
                        Edit.rejected==False)\
                .order_by(EditVote.delta.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "voted_invert":
        edits = Edit.query\
                .outerjoin(EditVote,
                        and_(EditVote.user_id==current_user.id,
                            EditVote.edit_id==Edit.id)
                        )\
                .filter(Edit.approved==False,
                        Edit.rejected==False)\
                .order_by(EditVote.delta.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    elif sort == "id":
        edits = Edit.query.outerjoin(Annotation)\
                .filter(Edit.approved==False,
                        Edit.rejected==False)\
                .order_by(Annotation.id.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "id_invert":
        edits = Edit.query.outerjoin(Annotation)\
                .filter(Edit.approved==False,
                        Edit.rejected==False)\
                .order_by(Annotation.id.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    elif sort == "edit_num":
        edits = Edit.query\
                .filter(Edit.approved==False,
                        Edit.rejected==False)\
                .order_by(Edit.edit_num.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "edit_num_invert":
        edits = Edit.query\
                .filter(Edit.approved==False,
                        Edit.rejected==False)\
                .order_by(Edit.edit_num.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    elif sort == "editor":
        edits = Edit.query.outerjoin(User)\
                .filter(Edit.approved==False,
                        Edit.rejected==False)\
                .order_by(User.displayname.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "editor_invert":
        edits = Edit.query.outerjoin(User)\
                .filter(Edit.approved==False,
                        Edit.rejected==False)\
                .order_by(User.displayname.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    elif sort == "time":
        edits = Edit.query\
                .filter(Edit.approved==False,
                        Edit.rejected==False)\
                .order_by(Edit.modified.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time_invert":
        edits = Edit.query\
                .filter(Edit.approved==False,
                        Edit.rejected==False)\
                .order_by(Edit.modified.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    elif sort == "reason":
        edits = Edit.query\
                .filter(Edit.approved==False,
                        Edit.rejected==False)\
                .order_by(Edit.edit_reason.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "reason_invert":
        edits = Edit.query\
                .filter(Edit.approved==False,
                        Edit.rejected==False)\
                .order_by(Edit.edit_reason.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    else:
        edits = Edit.query\
                .outerjoin(EditVote,
                        and_(EditVote.user_id==current_user.id,
                            EditVote.edit_id==Edit.id)
                        )\
                .filter(Edit.approved==False,
                        Edit.rejected==False)\
                .order_by(EditVote.delta.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
        sort = "voted"


    votes = current_user.edit_votes

    next_page = url_for("edit_review_queue", page=edits.next_num, sort=sort)\
            if edits.has_next else None
    prev_page = url_for("edit_review_queue", page=edits.prev_num, sort=sort)\
            if edits.has_prev else None

    return render_template("indexes/edits.html", title="Edit Queue",
            edits=edits.items, votes=votes, sort=sort, next_page=next_page,
            prev_page=prev_page)

@app.route("/admin/edit/<edit_id>/")
@login_required
def review_edit(edit_id):
    current_user.authorize("review_edits")

    edit = Edit.query.get_or_404(edit_id)
    if edit.approved == True:
        return redirect(url_for("view_edit", annotation_id=edit.annotation_id,
            edit_num=edit.edit_num))
    if not edit.annotation.active:
        current_user.authorize("review_deactivated_annotation_edits")

    # we have to replace single returns with spaces because markdown only
    # recognizes paragraph separation based on two returns. We also have to be
    # careful to do this for both unix and windows return variants (i.e. be
    # careful of \r's).
    diff1 = re.sub(r"(?<!\n)\r?\n(?![\r\n])", " ", edit.previous.annotation)
    diff2 = re.sub(r"(?<!\n)\r?\n(?![\r\n])", " ", edit.annotation)

    diff = list(difflib.Differ().compare(diff1.splitlines(),
        diff2.splitlines()))
    tags = [tag for tag in edit.tags]
    for tag in edit.previous.tags:
        if tag not in tags:
            tags.append(tag)
    if edit.first_line_num > edit.previous.first_line_num:
        context = [line for line in edit.previous.context]
        for line in edit.context:
            if line not in context:
                context.append(line)
    else:
        context = [line for line in edit.context]
        for line in edit.previous.context:
            if line not in context:
                context.append(line)

    return render_template("view/edit.html", title=f"Edit number {edit.edit_num}",
            diff=diff, edit=edit, tags=tags, context=context)

@app.route("/admin/approve/edit/<edit_id>/")
@login_required
def approve(edit_id):
    current_user.authorize("review_edits")
    edit = Edit.query.get_or_404(edit_id)
    if not edit.annotation.active:
        current_user.authorize("review_deactivated_annotation_edits")
    if current_user.get_edit_vote(edit):
        flash(f"You already voted on edit {edit.edit_num} of annotation {edit.annotation.id}")
        return redirect(url_for("edit_review_queue"))
    elif edit.editor == current_user:
        flash("You cannot approve or reject your own edits")
        return redirect(url_for("edit_review_queue"))
    edit.approve(current_user)
    if edit.weight >= app.config["MIN_APPROVAL_RATING"] or \
            current_user.is_authorized("approve_edits"):
        edit.approved = True
        edit.annotation.edit_pending = False
        edit.annotation.HEAD.current = False
        edit.current = True
        edit.notify_edit("approved")
        flash(f"Edit {edit.edit_num} approved.")
    db.session.commit()
    return redirect(url_for("edit_review_queue"))

@app.route("/admin/reject/edit/<edit_id>/")
@login_required
def reject(edit_id):
    current_user.authorize("review_edits")
    edit = Edit.query.get_or_404(edit_id)
    if not edit.annotation.active:
        current_user.authorize("review_deactivated_annotation_edits")
    if current_user.get_edit_vote(edit):
        flash(f"You already voted on edit {edit.edit_num} of annotation {edit.annotation.id}")
        return redirect(url_for("edit_review_queue"))
    elif edit.editor == current_user:
        flash("You cannot approve or reject your own edits")
        return redirect(url_for("edit_review_queue"))
    edit.reject(current_user)
    if edit.weight <= app.config["MIN_REJECTION_RATING"] or \
            current_user.is_authorized("approve_edits"):
        edit.annotation.edit_pending = False
        edit.rejected = True
        edit.notify_edit("rejected")
        flash(f"Edit {edit.edit_num} rejected.")
    db.session.commit()
    return redirect(url_for("edit_review_queue"))

@app.route("/admin/rescind_vote/edit/<edit_id>/")
@login_required
def rescind(edit_id):
    current_user.authorize("review_edits")
    edit = Edit.query.get_or_404(edit_id)
    if not edit.annotation.active:
        current_user.authorize("review_deactivated_annotation_edits")
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

@app.route("/admin/annotation/<annotation_id>/delete/", methods=["GET", "POST"])
@login_required
def delete_annotation(annotation_id):
    form = AreYouSureForm()
    current_user.authorize("delete_annotations")
    annotation = Annotation.query.get_or_404(annotation_id)
    redirect_url = url_for("book_annotations", book_url=annotation.book.url)
    if form.validate_on_submit():
        db.session.delete(annotation)
        db.session.commit()
        flash(f"Annotation [{annotation_id}] deleted.")
        return redirect(redirect_url)
    text = """
If you click submit the annotation, all of the edits to the annotation, all of
the votes to the edits, all of the votes to the annotation, and all of the
reputation changes based on the annotation, will be deleted permanently.

This is not something to take lightly. Unless there is illegal content
associated with the annotation, you really ought to simply deactivate it.
    """
    return render_template("forms/delete_check.html", 
            title=f"Delete [{annotation_id}]", form=form, text=text)

@app.route("/admin/edit/<edit_id>/delete/", methods=["GET", "POST"])
@login_required
def delete_edit(edit_id):
    form = AreYouSureForm()
    current_user.authorize("delete_annotations")
    edit = Edit.query.get_or_404(edit_id)
    redirect_url = generate_next(url_for("annotation",
        annotation_id=edit.annotation_id))
    if form.validate_on_submit():
        if edit.current:
            edit.previous.current = True
        else:
            for e in edit.annotation.all_edits.order_by(Edit.edit_num.desc()).all():
                if e.edit_num > edit.edit_num:
                    e.edit_num -= 1
        flash(f"Edit #{edit.edit_num} of [{edit.annotation_id}] deleted.")
        db.session.delete(edit)
        db.session.commit()
        return redirect(redirect_url)
    text = """
If you click submit the edit, all of the votes for the edit, and all of the
reputation changes based on the edit being approved will be deleted. The edit
numbers of all the subsequent edits will be decremented by one. It will
therefore be as though the edit never even existed.

The only reason for this is if there is illegal content in the edit.
    """
    return render_template("forms/delete_check.html", 
            title=f"Delete edit #{edit.edit_num} of [{edit.annotation_id}]",
            form=form, text=text)

#####################
## Content Editing ##
#####################

@app.route("/admin/edit/line/<line_id>/", methods=["GET", "POST"])
@login_required
def edit_line(line_id):
    current_user.authorize("edit_lines")
    line = Line.query.get_or_404(line_id)
    form = LineForm()
    form.line.data = line.line
    redirect_url = generate_next(url_for(line.get_url()))
    if form.validate_on_submit():
        if form.line.data != None and len(form.line.data) <= 200:
            line.line = form.line.data
            db.session.commit()
            flash("Line updated.")
            return redirect(redirect_url)
    return render_template("forms/line.html", title="Edit Line", form=form)

@app.route("/admin/edit/author_bio/<author_id>/", methods=["GET", "POST"])
@login_required
def edit_bio(author_id):
    current_user.authorize("edit_bios")
    author = Author.query.get_or_404(author_id)
    form = TextForm()
    redirect_url = generate_next(url_for("author", name=author.url))
    if form.validate_on_submit():
        if form.text.data != None:
            author.bio = form.text.data
            db.session.commit()
            flash("Bio updated.")
            return redirect(redirect_url)
    else:
        form.text.data = author.bio

    return render_template("forms/text.html", title="Edit Bio", form=form)

@app.route("/admin/edit/book_summary/<book_id>/", methods=["GET", "POST"])
@login_required
def edit_summary(book_id):
    current_user.authorize("edit_summaries")
    book = Book.query.get_or_404(book_id)
    form = TextForm()
    redirect_url = generate_next(url_for("book", book_url=book.url))
    if form.validate_on_submit():
        if form.text.data != None:
            book.summary = form.text.data
            db.session.commit()
            flash("Summary updated.")
            return redirect(redirect_url)
    else:
        form.text.data = book.summary
    return render_template("forms/text.html", title="Edit Summary", form=form)

@app.route("/admin/edit/tag/<tag_id>/", methods=["GET", "POST"])
@login_required
def edit_tag(tag_id):
    current_user.authorize("edit_tags")
    tag = Tag.query.get_or_404(tag_id)
    form = TagForm()
    if form.validate_on_submit():
        if form.tag.data != None and form.description.data != None:
            tag.tag = form.tag.data
            tag.description = form.description.data
            db.session.commit()
            flash("Tag updated.")
            # we have to initiate tag url here bc tag changed
            redirect_url = generate_next(url_for("tag", tag=tag.tag))
            return redirect(redirect_url)
    else:
        form.tag.data = tag.tag
        form.description.data = tag.description
    return render_template("forms/tag.html", title="Edit Tag", form=form)

###############################
## Annotation Administration ##
###############################

@app.route("/admin/deactivate/annotation/<annotation_id>/")
@login_required
def deactivate(annotation_id):
    current_user.authorize("deactivate_annotations")
    annotation = Annotation.query.get_or_404(annotation_id)
    annotation.active = not annotation.active
    db.session.commit()
    if annotation.active:
        flash(f"Annotation {annotation.id} activated")
    else:
        flash(f"Annotation {annotation.id} deactivated.")

    redirect_url = generate_next(url_for("annotation",
        annotation_id=annotation_id))
    return redirect(redirect_url)

@app.route("/admin/list/deactivated/annotations/")
@login_required
def view_deactivated_annotations():
    current_user.authorize("view_deactivated_annotations")
    sort = request.args.get("sort", "added", type=str)
    page = request.args.get("page", 1, type=int)
    if sort == "added":
        annotations = Annotation.query.filter_by(active=False
                ).order_by(Annotation.added.desc()
                ).paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "weight":
        annotations = Annotation.query.filter_by(active=False
                ).order_by(Annotation.weight.desc()
                ).paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    sorts = {
            "added": url_for("view_deactivated_annotations", page=page, sort="added"),
            "weight": url_for("view_deactivated_annotations", page=page, sort="weight")
            }
    next_page = url_for("view_deactivated_annotations", page=annotations.next_num,
            sort=sort) if annotations.has_next else None
    prev_page = url_for("view_deactivated_annotations", page=annotations.prev_num,
            sort=sort) if annotations.has_prev else None
    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None
    return render_template("indexes/annotation_list.html",
            title="Deactivated Annotations", annotations=annotations.items,
            prev_page=prev_page, next_page=next_page, uservotes=uservotes,
            sort=sort, sorts=sorts)

###################
## Book Requests ##
###################

@app.route("/list/book_requests/")
def book_request_index():
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "weight", type=str)
    if sort == "oldest":
        book_requests = BookRequest.query\
                .order_by(BookRequest.requested.asc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "newest":
        book_requests = BookRequest.query\
                .order_by(BookRequest.requested.desc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "weight":
        book_requests = BookRequest.query\
                .order_by(BookRequest.weight.desc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "title":
        requests = BookRequest.query\
                .order_by(BookRequest.title.asc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "author":
        book_requests = BookRequest.query\
                .order_by(BookRequest.author.asc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    else:
        book_requests = BookRequest.query\
                .order_by(BookRequest.weight.desc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)

    sorts = {
            "oldest": url_for("book_request_index", sort="oldest", page=page),
            "newest": url_for("book_request_index", sort="newest", page=page),
            "weight": url_for("book_request_index", sort="weight", page=page),
            "title": url_for("book_request_index", sort="title", page=page),
            "author": url_for("book_request_index", sort="author", page=page)
            }

    next_page = url_for("book_request_index", page=book_requests.next_num,
            sort=sort) if book_requests.has_next else None
    prev_page = url_for("book_request_index", page=book_requests.prev_num,
            sort=sort) if book_requests.has_prev else None
    uservotes = current_user.get_book_request_vote_dict() \
            if current_user.is_authenticated else None
    return render_template("indexes/book_requests.html", title="Book Requests",
            next_page=next_page, prev_page=prev_page,
            book_requests=book_requests.items,
            uservotes=uservotes, sort=sort, sorts=sorts)

@app.route("/book_request/<book_request_id>/")
def view_book_request(book_request_id):
    book_request = BookRequest.query.get_or_404(book_request_id)
    return render_template("view/book_request.html", book_request=book_request)

@app.route("/admin/request/book/<book_request_id>/delete/", methods=["GET", "POST"])
@login_required
def delete_book_request(book_request_id):
    form = AreYouSureForm()
    book_request = BookRequest.query.get_or_404(book_request_id)
    if not current_user == book_request.requester:
        current_user.authorize("delete_book_requests")
    redirect_url = url_for("book_request_index")
    if form.validate_on_submit():
        flash(f"Book Request for {book_request.title} deleted.")
        db.session.delete(book_request)
        db.session.commit()
        return redirect(redirect_url)
    text = """
If you click submit the book request and all of it's votes will be deleted
permanently.
    """
    return render_template("forms/delete_check.html", 
            title=f"Delete Book Request", form=form, text=text)

@app.route("/request/book/", methods=["GET", "POST"])
@login_required
def book_request():
    current_user.authorize("request_books")
    form = BookRequestForm()
    if form.validate_on_submit():
        book_request = BookRequest(title=form.title.data,
                author=form.author.data, notes=form.notes.data,
                description=form.description.data,
                wikipedia=form.wikipedia.data, gutenberg=form.gutenberg.data,
                requester=current_user,
                weight=0)
        db.session.add(book_request)
        book_request.upvote(current_user)
        current_user.followed_book_requests.append(book_request)
        db.session.commit()
        flash("Book request created.")
        flash(f"You have upvoted the request for {book_request.title}.")
        flash("You are now following the request for {book_request.title}.")
        return redirect(url_for("book_request_index"))
    return render_template("forms/book_request.html", title="Request Book",
            form=form)

@app.route("/edit/book_request/<book_request_id>/", methods=["GET", "POST"])
@login_required
def edit_book_request(book_request_id):
    book_request = BookRequest.query.get_or_404(book_request_id)
    if current_user != book_request.requester:
        current_user.authorize("edit_book_requests")
    form = BookRequestForm()
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
    redirect_url = generate_next(url_for("book_request_index"))
    if current_user.already_voted_book_request(book_request):
        vote = current_user.book_request_ballots.filter(
                BookRequestVote.book_request==book_request).first()
        rd = True if vote.is_up() else False
        book_request.rollback(vote)
        db.session.commit()
        if rd:
            return redirect(redirect_url)
    book_request.upvote(current_user)
    db.session.commit()
    return redirect(redirect_url)

@app.route("/downvote/book_request/<book_request_id>/")
@login_required
def downvote_book_request(book_request_id):
    book_request = BookRequest.query.get_or_404(book_request_id)
    redirect_url = generate_next(url_for("book_request_index"))
    if current_user.already_voted_book_request(book_request):
        vote = current_user.book_request_ballots.filter(
                BookRequestVote.book_request==book_request).first()
        rd = True if not vote.is_up() else False
        book_request.rollback(vote)
        db.session.commit()
        if rd:
            return redirect(redirect_url)
    book_request.downvote(current_user)
    db.session.commit()
    return redirect(redirect_url)

##################
## Tag Requests ##
##################

@app.route("/list/tag_requests/")
def tag_request_index():
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "weight", type=str)
    if sort == "tag":
        tag_requests = TagRequest.query\
                .order_by(TagRequest.tag.asc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "weight":
        tag_requests = TagRequest.query\
                .order_by(TagRequest.weight.desc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "oldest":
        tag_requests = TagRequest.query\
                .order_by(TagRequest.requested.asc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "newest":
        tag_requests = TagRequest.query\
                .order_by(TagRequest.requested.desc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    else:
        tag_requests = TagRequest.query\
                .order_by(TagRequest.weight.desc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)

    sorts = {
            "tag": url_for("tag_request_index", sort="tag", page=page),
            "oldest": url_for("tag_request_index", sort="oldest", page=page),
            "newest": url_for("tag_request_index", sort="newest", page=page),
            "weight": url_for("tag_request_index", sort="weight", page=page),
            }

    next_page = url_for("tag_request_index", page=tag_requests.next_num,
            sort=sort) if tag_requests.has_next else None
    prev_page = url_for("tag_request_index", page=tag_requests.prev_num,
            sort=sort) if tag_requests.has_prev else None
    uservotes = current_user.get_tag_request_vote_dict() \
            if current_user.is_authenticated else None
    return render_template("indexes/tag_requests.html", title="Tag Requests",
            next_page=next_page, prev_page=prev_page,
            tag_requests=tag_requests.items, uservotes=uservotes,
            sort=sort, sorts=sorts)

@app.route("/tag_request/<tag_request_id>/")
def view_tag_request(tag_request_id):
    tag_request = TagRequest.query.get_or_404(tag_request_id)
    return render_template("view/tag_request.html", tag_request=tag_request)

@app.route("/admin/request/tag/<tag_request_id>/delete/", methods=["GET", "POST"])
@login_required
def delete_tag_request(tag_request_id):
    form = AreYouSureForm()
    tag_request = TagRequest.query.get_or_404(tag_request_id)
    if not current_user == tag_request.requester:
        current_user.authorize("delete_tag_requests")
    redirect_url = url_for("tag_request_index")
    if form.validate_on_submit():
        flash(f"Tag Request for {tag_request.tag} deleted.")
        db.session.delete(tag_request)
        db.session.commit()
        return redirect(redirect_url)
    text = """
If you click submit the book request and all of it's votes will be deleted
permanently.
    """
    return render_template("forms/delete_check.html", 
            title=f"Delete Tag Request", form=form, text=text)

@app.route("/request/tag/", methods=["GET", "POST"])
@login_required
def tag_request():
    current_user.authorize("request_tags")
    form = TagRequestForm()
    if form.validate_on_submit():
        tag_request = TagRequest(tag=form.tag.data,
                notes=form.notes.data, description=form.description.data,
                wikipedia=form.wikipedia.data, weight=0, requester=current_user)
        db.session.add(tag_request)
        tag_request.upvote(current_user)
        current_user.followed_tag_requests.append(tag_request)
        db.session.commit()
        flash("Tag request created.")
        flash("You have upvoted the request for {tag_request.tag}")
        flash("You are now follow the request for {tag_request.tag}")
        return redirect(url_for("tag_request_index"))
    return render_template("forms/tag_request.html", title="Request Tag",
            form=form)

@app.route("/edit/tag_request/<tag_request_id>/", methods=["GET", "POST"])
@login_required
def edit_tag_request(tag_request_id):
    tag_request = TagRequest.query.get_or_404(tag_request_id)
    if tag_request.requester != current_user:
        current_user.authorize("edit_tag_requests")
    form = TagRequestForm()
    if form.validate_on_submit():
        tag_request.tag = form.tag.data
        tag_request.notes = form.notes.data
        tag_request.description = form.description.data
        tag_request.wikipedia = form.wikipedia.data
        db.session.commit()
        flash("Tag request edit complete.")
        return redirect(url_for("view_tag_request",
            tag_request_id=tag_request_id))
    else:
        form.tag.data = tag_request.tag
        form.notes.data = tag_request.notes
        form.description.data = tag_request.description
        form.wikipedia.data = tag_request.wikipedia
    return render_template("forms/tag_request.html", title="Edit Tag Request",
            form=form)

@app.route("/upvote/tag_request/<tag_request_id>/")
@login_required
def upvote_tag_request(tag_request_id):
    tag_request = TagRequest.query.get_or_404(tag_request_id)

    redirect_url = generate_next(url_for("tag_request_index"))

    if current_user.already_voted_tag_request(tag_request):
        vote = current_user.tag_request_ballots.filter(
                TagRequestVote.tag_request==tag_request).first()
        rd = True if vote.is_up() else False
        tag_request.rollback(vote)
        db.session.commit()
        if rd:
            return redirect(redirect_url)

    tag_request.upvote(current_user)
    db.session.commit()

    return redirect(redirect_url)

@app.route("/downvote/tag_request/<tag_request_id>/")
@login_required
def downvote_tag_request(tag_request_id):
    tag_request = TagRequest.query.get_or_404(tag_request_id)

    redirect_url = generate_next(url_for("tag_request_index"))

    if current_user.already_voted_tag_request(tag_request):
        vote = current_user.tag_request_ballots.filter(
                TagRequestVote.tag_request==tag_request).first()
        rd = True if not vote.is_up() else False
        tag_request.rollback(vote)
        db.session.commit()
        if rd:
            return redirect(redirect_url)

    tag_request.downvote(current_user)
    db.session.commit()

    return redirect(redirect_url)

@app.route("/admin/tags/create/", methods=["GET","POST"],
        defaults={"tag_request_id":None})
@app.route("/admin/tags/create/<tag_request_id>/", methods=["GET","POST"])
@login_required
def create_tag(tag_request_id):
    current_user.authorize("create_tags")
    tag_request = None
    if tag_request_id:
        tag_request = TagRequest.query.get_or_404(tag_request_id)
    redirect_url = generate_next(url_for("tag_request_index"))
    form = TagForm()
    if form.validate_on_submit():
        if form.tag.data != None and form.description.data != None:
            tag = Tag(tag=form.tag.data, description=form.description.data)
            db.session.add(tag)
            db.session.commit()
            flash("Tag created.")
            return redirect(redirect_url)
    elif tag_request:
            tag = Tag(tag=tag_request.tag, description=tag_request.description)
            tag_request.created_tag = tag
            tag_request.approved = True
            tag_request.notify_approval()
            db.session.add(tag)
            db.session.commit()
            flash("Tag created.")
            return redirect(redirect_url)
    return render_template("forms/tag.html", title="Create Tag", form=form)

@app.route("/admin/tags/reject/<tag_request_id>/")
@login_required
def reject_tag(tag_request_id):
    current_user.authorize("create_tags")
    tag_request = TagRequest.query.get_or_404(tag_request_id)
    redirect_url = generate_next(url_for("tag_request_index"))
    tag_request.rejected = True
    tag_request.notify_rejection()
    db.session.commit()
    return redirect(redirect_url)

#######################
#######################
## ## Ajax Routes ## ##
#######################
#######################

@app.route("/autocomplete/tags/", methods=["POST"])
def ajax_tags():
    tagstr = request.form.get("tags")
    tags = tagstr.split()
    results = Tag.query.filter(Tag.tag.startswith(tags[-1]), Tag.admin==False)\
            .limit(6)
    if not results:
        return jsonify({"success": False, "tags": []})
    tag_list = []
    descriptions = []
    for t in results:
        tag_list.append(t.tag)
        descriptions.append(t.description)

    return jsonify({"success": True, "tags": tag_list,
        "descriptions": descriptions })
