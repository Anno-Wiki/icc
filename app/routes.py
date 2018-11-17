from collections import defaultdict
from datetime import datetime
import hashlib
from flask import render_template, flash, redirect, url_for, request, Markup, \
        abort, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from sqlalchemy import or_, and_
from app import app, db
from app.models import User, Book, Author, Line, Kind, Annotation, \
        AnnotationVersion, Tag, EditVote, AdminRight, Vote, BookRequest, \
        BookRequestVote, TagRequest, TagRequestVote, UserFlag, AnnotationFlag, \
        NotificationType, NotificationEvent, tags as tags_table, UserFlagEvent,\
        AnnotationFlagEvent
from app.forms import LoginForm, RegistrationForm, AnnotationForm, \
        LineNumberForm, TagForm, LineForm, BookRequestForm, TagRequestForm, \
        EditProfileForm, ResetPasswordRequestForm, ResetPasswordForm, TextForm,\
        AreYouSureForm
from app.email import send_password_reset_email
from app.funky import preplines, is_filled
import difflib
import re
import time

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
    sort = request.args.get("sort", "newest", type=str)
    if sort == "newest":
        annotations = Annotation.query.filter_by(active=True)\
                .order_by(Annotation.added.desc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "weight":
        annotations = Annotation.query.filter_by(active=True)\
                .order_by(Annotation.weight.desc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "oldest":
        annotations = Annotation.query.filter_by(active=True)\
                .order_by(Annotation.added.asc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "modified":
        annotations = Annotation.query.outerjoin(AnnotationVersion,
                and_(Annotation.id==AnnotationVersion.pointer_id,
                    AnnotationVersion.current==True))\
                .group_by(Annotation.id)\
                .order_by(AnnotationVersion.modified.desc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    else:
        annotations = Annotation.query.filter_by(active=True)\
                .order_by(Annotation.added.desc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    sorts = {
            "newest": url_for("index", page=page, sort="newest"),
            "oldest": url_for("index", page=page, sort="oldest"),
            "weight": url_for("index", page=page, sort="weight"),
            "modified": url_for("index", page=page, sort="modified"),
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

@app.route("/user/inbox/")
@login_required
def inbox():
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "read", type=str)
    if sort == "time":
        notifications = current_user.notifications.order_by(
                NotificationEvent.time.desc()
                ).paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time_invert":
        notifications = current_user.notifications.order_by(
                NotificationEvent.time.asc()
                ).paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "type":
        notifications = current_user.notifications.join(NotificationType
                ).order_by(
                NotificationType.code.desc(),
                NotificationEvent.time.desc()
                ).paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "type_invert":
        notifications = current_user.notifications.join(NotificationType
                ).order_by(
                NotificationType.code.asc(),
                NotificationEvent.time.desc()
                ).paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "information":
        notifications = current_user.notifications.order_by(
                NotificationEvent.information.asc(),
                NotificationEvent.time.desc()
                ).paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "information_invert":
        notifications = current_user.notifications.order_by(
                NotificationEvent.information.desc(),
                NotificationEvent.time.desc()
                ).paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    else:
        notifications = current_user.notifications.order_by(
                NotificationEvent.seen.asc(),
                NotificationEvent.time.desc()
                ).paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    sorts = {
            "read": url_for("inbox", sort="read", page=page),
            "read_invert": url_for("inbox", sort="read_invert", page=page),
            "time": url_for("inbox", sort="time", page=page),
            "time_invert": url_for("inbox", sort="time_invert", page=page),
            "type": url_for("inbox", sort="type", page=page),
            "type_invert": url_for("inbox", sort="type_invert", page=page),
            "information": url_for("inbox", sort="information", page=page),
            "information_invert": url_for("inbox", sort="information_invert", page=page),
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
    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = url_for("inbox")
    notification = NotificationEvent.query.get_or_404(event_id)
    if notification.seen:
        notification.mark_unread()
    else:
        notification.mark_read()
    db.session.commit()
    return redirect(next_page)

@app.route("/user/inbox/mark/read/all/")
@login_required
def mark_all_read():
    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = url_for("inbox")
    notifications = current_user.new_notifications
    for notification in notifications:
        notification.mark_read()
    db.session.commit()
    return redirect(next_page)


@app.route("/reset_password_request", methods=["GET", "POST"])
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

    if form.validate_on_submit():
        return redirect(url_for("delete_account"))

    return render_template("forms/delete_account_check.html", form=form,
            title="Are you sure?")

###################
## follow routes ##
###################

@app.route("/user/follow/book/<book_id>/")
@login_required
def follow_book(book_id):
    book = Book.query.get_or_404(book_id)
    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = url_for("book", book_url=book.url)
    if book in current_user.followed_books:
        current_user.followed_books.remove(book)
    else:
        current_user.followed_books.append(book)
    db.session.commit()
    return redirect(next_page)

@app.route("/user/follow/book_request/<book_request_id>/")
@login_required
def follow_book_request(book_request_id):
    book_request = BookRequest.query.get_or_404(book_request_id)
    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = url_for("view_book_request", book_request_id=book_request.id)
    if book_request.approved:
        flash("You cannot follow a book request that has already been approved.")
    if book_request in current_user.followed_book_requests:
        current_user.followed_book_requests.remove(book_request)
    else:
        current_user.followed_book_requests.append(book_request)
    db.session.commit()
    return redirect(next_page)

@app.route("/user/follow/author/<author_id>/")
@login_required
def follow_author(author_id):
    author = Author.query.get_or_404(author_id)
    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = url_for("author", name=author.url)
    if author in current_user.followed_authors:
        current_user.followed_authors.remove(author)
    else:
        current_user.followed_authors.append(author)
    db.session.commit()
    return redirect(next_page)

@app.route("/user/follow/user/<user_id>/")
@login_required
def follow_user(user_id):
    user = User.query.get_or_404(user_id)
    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = url_for("user", user_id=user.id)
    if user == current_user:
        flash("You can't follow yourself.")
        redirect(next_page)
    elif user in current_user.followed_users:
        current_user.followed_users.remove(user)
    else:
        current_user.followed_users.append(user)
    db.session.commit()
    return redirect(next_page)

@app.route("/user/follow/tag/<tag_id>/")
@login_required
def follow_tag(tag_id):
    tag = Tag.query.get_or_404(tag_id)
    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = url_for("tag", tag=tag.tag)
    if tag in current_user.followed_tags:
        current_user.followed_tags.remove(tag)
    else:
        current_user.followed_tags.append(tag)
    db.session.commit()
    return redirect(next_page)

@app.route("/user/follow/tag_request/<tag_request_id>/")
@login_required
def follow_tag_request(tag_request_id):
    tag_request = TagRequest.query.get_or_404(tag_request_id)
    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = url_for("view_tag_request", tag_request_id=tag_request.id)
    if tag_request in current_user.followed_tag_requests:
        current_user.followed_tag_requests.remove(tag_request)
    else:
        current_user.followed_tag_requests.append(tag_request)
    db.session.commit()
    return redirect(next_page)

@app.route("/user/follow/annotation/<annotation_id>")
@login_required
def follow_annotation(annotation_id):
    annotation = Annotation.query.get_or_404(annotation_id)
    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = url_for("annotation", annotation_id=annotation.id)
    if annotation.author == current_user:
        flash("You cannot follow your own annotation.")
        redirect(next_page)
    elif annotation in current_user.followed_annotations:
        current_user.followed_annotations.remove(annotation)
    else:
        current_user.followed_annotations.append(annotation)
    db.session.commit()
    return redirect(next_page)

#############
## Indexes ##
#############

@app.route("/list/authors/")
def author_index():
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "last name", type=str)
    if sort == "last name":
        authors = Author.query.order_by(Author.last_name.asc()
                ).paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "name":
        authors = Author.query.order_by(Author.name.asc()
                ).paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "oldest":
        authors = Author.query.order_by(Author.birth_date.asc()
                ).paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "youngest":
        authors = Author.query.order_by(Author.birth_date.desc()
                ).paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "books":
        authors = Author.query.outerjoin(Book).group_by(Author.id)\
                .order_by(db.func.count(Book.id).desc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    else:
        authors = Author.query.order_by(Author.last_name.asc()
                ).paginate(page, app.config["CARDS_PER_PAGE"], False)
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
        books = Book.query.order_by(Book.sort_title.asc()
                ).paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "author":
        books = Book.query.join(Author).order_by(Author.last_name.asc()
                ).paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "oldest":
        books = Book.query.order_by(Book.published.asc()
                ).paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "newest":
        books = Book.query.order_by(Book.published.desc()
                ).paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "length":
        books = Book.query.outerjoin(Line).group_by(Book.id)\
                .order_by(db.func.count(Line.id).desc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "annotations":
        books = Book.query.outerjoin(Annotation).group_by(Book.id)\
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
        tags = Tag.query.order_by(Tag.tag
                ).paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "annotations":
        # This doesn't do anything but the same sort yet
        tags = Tag.query.outerjoin(tags_table)\
                .outerjoin(AnnotationVersion, and_(
                    AnnotationVersion.id==tags_table.c.annotation_version_id,
                    AnnotationVersion.current==True))\
                .group_by(Tag.id)\
                .order_by(db.func.count(AnnotationVersion.id).desc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    else:
        tags = Tag.query.order_by(Tag.tag
                ).paginate(page, app.config["CARDS_PER_PAGE"], False)

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
        users = User.query.order_by(User.reputation.desc()
                ).paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "name":
        users = User.query.order_by(User.displayname.asc()
                ).paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "annotations":
        users = User.query.outerjoin(Annotation).group_by(User.id)\
                .order_by(db.func.count(Annotation.id).desc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    else:
        users = User.query.order_by(User.reputation.desc()
                ).paginate(page, app.config["CARDS_PER_PAGE"], False)
    sorts = {
            "reputation": url_for("user_index", page=page, sort="reputation"),
            "name": url_for("user_index", page=page, sort="name"),
            "annotations": url_for("user_index", page=page, sort="annotations"),
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
    if sort == "date":
        annotations = author.annotations.order_by(Annotation.added.desc()
                ).paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "weight":
        annotations = author.annotations.order_by(Annotation.weight.desc()
                ).paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    annotationflags = AnnotationFlag.query.all()
    sorts = {
            "date": url_for("author_annotations", name=author.url,
                sort="date", page=page),
            "weight": url_for("author_annotations", name=author.url,
                sort="weight", page=page)
            }
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

@app.route("/book/<book_url>/annotations/")
def book_annotations(book_url):
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "weight", type=str)
    book = Book.query.filter_by(url=book_url).first_or_404()
    if sort == "date":
        annotations = Annotation.query.filter_by(book_id=book.id
                ).order_by(Annotation.added.desc()
                ).paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "weight":
        annotations = Annotation.query.filter_by(book_id=book.id
                ).order_by(Annotation.weight.desc()
                ).paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    annotationflags = AnnotationFlag.query.all()
    sorts = {
            "date": url_for("book_annotations", book_url=book.url,
                sort="date", page=page),
            "weight": url_for("book_annotations", book_url=book.url,
                sort="weight", page=page)
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
                .order_by(AnnotationVersion.modified.desc())\
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

@app.route("/annotation/<annotation_id>")
def annotation(annotation_id):
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

    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "edit_num_invert", type=str)

    if sort == "edit_num":
        edits = annotation.history\
                .filter(AnnotationVersion.approved==True)\
                .order_by(AnnotationVersion.edit_num.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "edit_num_invert":
        edits = annotation.history\
                .filter(AnnotationVersion.approved==True)\
                .order_by(AnnotationVersion.edit_num.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "editor":
        edits = annotation.history.outerjoin(User)\
                .filter(AnnotationVersion.approved==True)\
                .order_by(User.displayname.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "editor_invert":
        edits = annotation.history.outerjoin(User)\
                .filter(AnnotationVersion.approved==True)\
                .order_by(User.displayname.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time":
        edits = annotation.history\
                .filter(AnnotationVersion.approved==True)\
                .order_by(AnnotationVersion.modified.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time_invert":
        edits = annotation.history\
                .filter(AnnotationVersion.approved==True)\
                .order_by(AnnotationVersion.modified.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "reason":
        edits = annotation.history\
                .filter(AnnotationVersion.approved==True)\
                .order_by(AnnotationVersion.edit_reason.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "reason_invert":
        edits = annotation.history\
                .filter(AnnotationVersion.approved==True)\
                .order_by(AnnotationVersion.edit_reason.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    else:
        edits = annotation.history\
                .outerjoin(EditVote, 
                        and_(EditVote.user_id==current_user.id, 
                            EditVote.edit_id==AnnotationVersion.id)
                        )\
                .filter(AnnotationVersion.approved==True)\
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

@app.route("/annotation/<annotation_id>/edit/<edit_num>")
def view_edit(annotation_id, edit_num):
    edit = AnnotationVersion.query.filter(
            AnnotationVersion.pointer_id==annotation_id,
            AnnotationVersion.edit_num==edit_num,
            AnnotationVersion.approved==True
            ).first_or_404()

    if not edit.previous:
        return render_template("view/first_version.html", 
                title=f"First Version of [{edit.pointer.id}]", edit=edit)
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
            "weight": url_for("user", user_id=user_id, sort="weight", page=page),
            "newest": url_for("user", user_id=user_id, sort="newest", page=page),
            "oldest": url_for("user", user_id=user_id, sort="oldest", page=page)
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
        annotations = tag.annotations\
                .filter(Annotation.book_id==book.id,
                        AnnotationVersion.last_line_num<=lines[-1].l_num)\
                .all()
        tags = None
    else:
        annotations = book.annotations\
                .filter(AnnotationVersion.last_line_num<=lines[-1].l_num)\
                .all()
        # this query is like 5 times faster than the old double-for loop
        tags = Tag.query.outerjoin(tags_table)\
                .join(AnnotationVersion, and_(
                    AnnotationVersion.id==tags_table.c.annotation_version_id,
                    AnnotationVersion.current==True,
                    AnnotationVersion.first_line_num>=lines[0].l_num,
                    AnnotationVersion.last_line_num<=lines[-1].l_num)
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
    edit_right = AdminRight.query.filter_by(right="edit_lines").first()

    # This custom method for replacing underscores with <em> tags is still way
    # faster than the markdown converter. Since I'm not using anything other
    # than underscores for italics in the body of the actual text (e.g., I'm
    # using other methods to indicate blockquotes), I'll just keep using this.
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

    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = lines[0].get_url()

    book = Book.query.filter_by(url=book_url).first_or_404()
    lines = book.lines.filter(Line.l_num>=first_line,
            Line.l_num<=last_line).all()
    context = book.lines.filter(Line.l_num>=int(first_line)-5,
            Line.l_num<=int(last_line)+5).all()
    form = AnnotationForm()

    if lines == None:
        abort(404)

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

        locked = form.locked.data and current_user.has_right("lock_annotations")

        # Create the annotation pointer with HEAD pointing to anno
        head = Annotation(book=book, author=current_user, locked=locked)

        # I'll use the language of git
        # Create the inital transient sqlalchemy AnnotationVersion object
        commit = AnnotationVersion(
                book=book, approved=True, current=True, editor=current_user,
                first_line_num=fl, last_line_num=ll,
                first_char_idx=form.first_char_idx.data,
                last_char_idx=form.last_char_idx.data,
                annotation=form.annotation.data, tags=tags, pointer=head,
                edit_reason="Initial version"
                )


        # add anno, commit it
        db.session.add(commit)
        db.session.add(head)
        db.session.commit()

        # notify all the watchers
        head.notify_new()
        db.session.commit()

        flash("Annotation Submitted")

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

    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = lines[0].get_url()

    if annotation.locked == True\
            and not current_user.has_right("edit_locked_annotations"):
        flash("That annotation is locked from editing.")
        return redirect(next_page)

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

        # if a reason isn't provided, fail the submission
        if not form.reason.data:
            flash("Please provide a reason for your edit.")
            fail = True

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
            return render_template("forms/annotation.html", form=form,
                    lines=lines, annotation=annotation,
                    title=annotation.HEAD.book.title, book=annotation.HEAD.book)
        # approved is true if the user can edit immediately
        approved = current_user.has_right("immediate_edits")\
                or annotation.author == current_user

        lockchange = False
        if current_user.has_right("lock_annotations"):
            # the lock changes if the annotation's lock value is different from
            # the form's locked data. We have to specify this because this won't
            # show up in edit's hash_id and will fail the uniqueness test.
            lockchange = annotation.locked != form.locked.data
            annotation.locked = form.locked.data

        edit_num = int(annotation.HEAD.edit_num+1) if annotation.HEAD.edit_num\
                else 1

        # both the approved and current variables are based on approved
        edit = AnnotationVersion(book=annotation.book,
                editor_id=current_user.id, edit_num=edit_num,
                edit_reason=form.reason.data, pointer_id=anno_id,
                previous_id=annotation.HEAD.id,
                approved=approved, current=approved,
                first_line_num=fl, last_line_num=ll,
                first_char_idx=form.first_char_idx.data,
                last_char_idx=form.last_char_idx.data,
                annotation=form.annotation.data, tags=tags,
                )

        if edit.hash_id == annotation.HEAD.hash_id and not lockchange:
            flash("Your suggested edit is no different from the previous version.")
            return render_template("forms/annotation.html", form=form,
                    lines=lines, annotation=annotation,
                    title=annotation.HEAD.book.title, book=annotation.HEAD.book)
        elif edit.hash_id == annotation.HEAD.hash_id and lockchange:
            db.session.commit()
            flash("Annotation Locked")
        else:
            annotation.edit_pending = not approved
            if approved:
                annotation.HEAD.current = False
                db.session.commit()
            db.session.add(edit)
            db.session.commit()

        if approved:
            edit.notify_edit("approved")
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

    return render_template("forms/annotation.html",
            title=f"Edit Annotation {annotation.id}", form=form,
            book=annotation.HEAD.book, lines=lines,
            annotation=annotation, context=context)

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
        edit.notify_edit("approved")
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

# annotation flags
@app.route("/admin/flags/annotation/<annotation_id>/")
@login_required
def annotation_flags(annotation_id):
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "marked", type=str)
    current_user.authorize_rights("resolve_annotation_flags")
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
            "marked": url_for("annotation_flags", annotation_id=annotation.id, sort="marked", page=page),
            "flag": url_for("annotation_flags", annotation_id=annotation.id, sort="flag", page=page),
            "time": url_for("annotation_flags", annotation_id=annotation.id, sort="time", page=page),
            "thrower": url_for("annotation_flags", annotation_id=annotation.id, sort="thrower", page=page),
            "resolver": url_for("annotation_flags", annotation_id=annotation.id, sort="resolver", page=page),
            "resolved_at": url_for("annotation_flags", annotation_id=annotation.id, sort="resolved_at", page=page),
            "marked_invert": url_for("annotation_flags", annotation_id=annotation.id, sort="marked_invert", page=page),
            "flag_invert": url_for("annotation_flags", annotation_id=annotation.id, sort="flag_invert", page=page),
            "time_invert": url_for("annotation_flags", annotation_id=annotation.id, sort="time_invert", page=page),
            "thrower_invert": url_for("annotation_flags", annotation_id=annotation.id, sort="thrower_invert", page=page),
            "resolver_invert": url_for("annotation_flags", annotation_id=annotation.id, sort="resolver_invert", page=page),
            "resolved_at_invert": url_for("annotation_flags", annotation_id=annotation.id, sort="resolved_at_invert", page=page),
            }

    next_page = url_for("annotation_flags", annotation_id=annotation.id,
            page=flags.next_num, sort=sort) if flags.has_next else None
    prev_page = url_for("annotation_flags", annotation_id=annotation.id,
            page=flags.prev_num, sort=sort) if flags.has_prev else None
    return render_template("indexes/annotation_flags.html", 
            title=f"Annotation {annotation.id} flags", annotation=annotation,
            flags=flags.items, sort=sort, sorts=sorts, next_page=next_page,
            prev_page=prev_page)

@app.route("/admin/flags/mark/annotation_flag/<flag_id>/")
@login_required
def mark_annotation_flag(flag_id):
    current_user.authorize_rights("resolve_annotation_flags")
    flag = AnnotationFlagEvent.query.get_or_404(flag_id)
    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = url_for("annotation_flags", annotation_id=flag.annotation_id)
    if flag.resolved:
        flag.unresolve()
    else:
        flag.resolve(current_user)
    db.session.commit()
    return redirect(next_page)

@app.route("/admin/flags/annotation/mark_all/<annotation_id>")
@login_required
def mark_annotation_flags(annotation_id):
    current_user.authorize_rights("resolve_annotation_flags")
    annotation = Annotation.query.get_or_404(annotation_id)
    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = url_for("annotation_flags", annotation_id=annotation.id)
    for flag in annotation.active_flags:
        flag.resolve(current_user)
    db.session.commit()
    return redirect(next_page)

# user flags
@app.route("/admin/flags/user/<user_id>/")
@login_required
def user_flags(user_id):
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "marked", type=str)
    current_user.authorize_rights("resolve_user_flags")
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
            "marked": url_for("user_flags", user_id=user.id, sort="marked", page=page),
            "flag": url_for("user_flags", user_id=user.id, sort="flag", page=page),
            "time": url_for("user_flags", user_id=user.id, sort="time", page=page),
            "thrower": url_for("user_flags", user_id=user.id, sort="thrower", page=page),
            "resolver": url_for("user_flags", user_id=user.id, sort="resolver", page=page),
            "resolved_at": url_for("user_flags", user_id=user.id, sort="resolved_at", page=page),
            "marked_invert": url_for("user_flags", user_id=user.id, sort="marked_invert", page=page),
            "flag_invert": url_for("user_flags", user_id=user.id, sort="flag_invert", page=page),
            "time_invert": url_for("user_flags", user_id=user.id, sort="time_invert", page=page),
            "thrower_invert": url_for("user_flags", user_id=user.id, sort="thrower_invert", page=page),
            "resolver_invert": url_for("user_flags", user_id=user.id, sort="resolver_invert", page=page),
            "resolved_at_invert": url_for("user_flags", user_id=user.id, sort="resolved_at_invert", page=page),
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
    current_user.authorize_rights("resolve_user_flags")
    flag = UserFlagEvent.query.get_or_404(flag_id)
    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = url_for("user_flags", user_id=flag.user_id)
    if flag.resolved:
        flag.unresolve()
    else:
        flag.resolve(current_user)
    db.session.commit()
    return redirect(next_page)

@app.route("/admin/flags/mark_all/<user_id>/")
@login_required
def mark_user_flags(user_id):
    current_user.authorize_rights("resolve_user_flags")
    user = User.query.get_or_404(user_id)
    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = url_for("user_flags", user_id=user.id)
    for flag in user.active_flags:
        flag.resolve(current_user)
    db.session.commit()
    return redirect(next_page)

#################
## Edit Review ##
#################

@app.route("/admin/queue/edits/")
@login_required
def edit_review_queue():
    if not current_user.has_right("review_edits"):
        current_user.authorize_rep(app.config["AUTHORIZATION"]["EDIT_QUEUE"])

    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "voted", type=str)

    if sort == "voted":
        edits = AnnotationVersion.query\
                .outerjoin(EditVote, 
                        and_(EditVote.user_id==current_user.id, 
                            EditVote.edit_id==AnnotationVersion.id)
                        )\
                .filter(AnnotationVersion.approved==False,
                        AnnotationVersion.rejected==False)\
                .order_by(EditVote.delta.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "voted_invert":
        edits = AnnotationVersion.query\
                .outerjoin(EditVote, 
                        and_(EditVote.user_id==current_user.id, 
                            EditVote.edit_id==AnnotationVersion.id)
                        )\
                .filter(AnnotationVersion.approved==False,
                        AnnotationVersion.rejected==False)\
                .order_by(EditVote.delta.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "id":
        edits = AnnotationVersion.query.outerjoin(Annotation)\
                .filter(AnnotationVersion.approved==False,
                        AnnotationVersion.rejected==False)\
                .order_by(Annotation.id.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "id_invert":
        edits = AnnotationVersion.query.outerjoin(Annotation)\
                .filter(AnnotationVersion.approved==False,
                        AnnotationVersion.rejected==False)\
                .order_by(Annotation.id.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "edit_num":
        edits = AnnotationVersion.query\
                .filter(AnnotationVersion.approved==False,
                        AnnotationVersion.rejected==False)\
                .order_by(AnnotationVersion.edit_num.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "edit_num_invert":
        edits = AnnotationVersion.query\
                .filter(AnnotationVersion.approved==False,
                        AnnotationVersion.rejected==False)\
                .order_by(AnnotationVersion.edit_num.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "editor":
        edits = AnnotationVersion.query.outerjoin(User)\
                .filter(AnnotationVersion.approved==False,
                        AnnotationVersion.rejected==False)\
                .order_by(User.displayname.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "editor_invert":
        edits = AnnotationVersion.query.outerjoin(User)\
                .filter(AnnotationVersion.approved==False,
                        AnnotationVersion.rejected==False)\
                .order_by(User.displayname.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time":
        edits = AnnotationVersion.query\
                .filter(AnnotationVersion.approved==False,
                        AnnotationVersion.rejected==False)\
                .order_by(AnnotationVersion.modified.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time_invert":
        edits = AnnotationVersion.query\
                .filter(AnnotationVersion.approved==False,
                        AnnotationVersion.rejected==False)\
                .order_by(AnnotationVersion.modified.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "reason":
        edits = AnnotationVersion.query\
                .filter(AnnotationVersion.approved==False,
                        AnnotationVersion.rejected==False)\
                .order_by(AnnotationVersion.edit_reason.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "reason_invert":
        edits = AnnotationVersion.query\
                .filter(AnnotationVersion.approved==False,
                        AnnotationVersion.rejected==False)\
                .order_by(AnnotationVersion.edit_reason.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    else:
        edits = AnnotationVersion.query\
                .outerjoin(EditVote, 
                        and_(EditVote.user_id==current_user.id, 
                            EditVote.edit_id==AnnotationVersion.id)
                        )\
                .filter(AnnotationVersion.approved==False,
                        AnnotationVersion.rejected==False)\
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

@app.route("/admin/review/edit/<edit_id>")
@login_required
def review_edit(edit_id):
    if not current_user.has_right("review_edits"):
        current_user.authorize_rep(app.config["AUTHORIZATION"]["EDIT_QUEUE"])
    edit = AnnotationVersion.query.get_or_404(edit_id)
    if edit.approved == True:
        return redirect(url_for("view_edit", annotation_id=edit.pointer_id,
            edit_num=edit.edit_num))

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
    if not current_user.has_right("review_edits"):
        current_user.authorize_rep(app.config["AUTHORIZATION"]["EDIT_QUEUE"])
    edit = AnnotationVersion.query.get_or_404(edit_id)
    if current_user.get_edit_vote(edit):
        flash(f"You already voted on edit {edit.edit_num} of annotation {edit.pointer.id}")
        return redirect(url_for("edit_review_queue"))
    elif edit.editor == current_user:
        flash("You cannot approve or reject your own edits")
        return redirect(url_for("edit_review_queue"))
    edit.approve(current_user)
    if edit.weight >= app.config["MIN_APPROVAL_RATING"] or \
            current_user.has_right("approve_edits"):
        edit.approved = True
        edit.pointer.edit_pending = False
        edit.pointer.HEAD.current = False
        edit.current = True
        edit.notify_edit("approved")
        flash(f"Edit {edit.edit_num} approved.")
    db.session.commit()
    return redirect(url_for("edit_review_queue"))

@app.route("/admin/reject/edit/<edit_id>/")
@login_required
def reject(edit_id):
    if not current_user.has_right("review_edits"):
        current_user.authorize_rep(app.config["AUTHORIZATION"]["EDIT_QUEUE"])
    edit = AnnotationVersion.query.get_or_404(edit_id)
    if current_user.get_edit_vote(edit):
        flash(f"You already voted on edit {edit.edit_num} of annotation {edit.pointer.id}")
        return redirect(url_for("edit_review_queue"))
    elif edit.editor == current_user:
        flash("You cannot approve or reject your own edits")
        return redirect(url_for("edit_review_queue"))
    edit.reject(current_user)
    if edit.weight <= app.config["MIN_REJECTION_RATING"] or \
            current_user.has_right("approve_edits"):
        edit.pointer.edit_pending = False
        edit.rejected = True
        edit.notify_edit("rejected")
        flash(f"Edit {edit.edit_num} rejected.")
    db.session.commit()
    return redirect(url_for("edit_review_queue"))

@app.route("/admin/rescind_vote/edit/<edit_id>/")
@login_required
def rescind(edit_id):
    if not current_user.has_right("review_edits"):
        current_user.authorize_rep(app.config["AUTHORIZATION"]["EDIT_QUEUE"])
    edit = AnnotationVersion.query.get_or_404(edit_id)
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

@app.route("/admin/deactivate/annotation/<anno_id>/")
@login_required
def deactivate(anno_id):
    current_user.authorize_rights("deactivate_annotations")
    annotation = Annotation.query.get_or_404(anno_id)
    annotation.active = not annotation.active
    db.session.commit()
    if annotation.active:
        flash(f"Annotation {annotation.id} activated")
    else:
        flash(f"Annotation {annotation.id} deactivated.")

    next_page = request.args.get("next")
    if not next_page or url_parse(next_page).netloc != "":
        next_page = url_for("index")
    return redirect(next_page)

@app.route("/admin/list/deactivated_annotations/")
@login_required
def view_deactivated_annotations():
    current_user.authorize_rights("view_deactivated_annotations")
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
        book_requests = BookRequest.query.order_by(BookRequest.requested.asc()
                ).paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "newest":
        book_requests = BookRequest.query.order_by(BookRequest.requested.desc()
                ).paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "weight":
        book_requests = BookRequest.query.order_by(BookRequest.weight.desc()
                ).paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "title":
        requests = BookRequest.query.order_by(BookRequest.title.asc()
                ).paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "author":
        book_requests = BookRequest.query.order_by(BookRequest.author.asc()
                ).paginate(page, app.config["CARDS_PER_PAGE"], False)
    else:
        book_requests = BookRequest.query.order_by(BookRequest.weight.desc()
                ).paginate(page, app.config["CARDS_PER_PAGE"], False)

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

@app.route("/request/book/", methods=["GET", "POST"])
@login_required
def book_request():
    if not current_user.has_right("request_books"):
        current_user.authorize_rep(app.config["AUTHORIZATION"]["BOOK_REQUEST"])
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
        current_user.authorize_rights("edit_book_requests")
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
    sort = request.args.get("sort", "weight", type=str)
    if sort == "tag":
        tag_requests = TagRequest.query.order_by(TagRequest.tag.asc()
                ).paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "weight":
        tag_requests = TagRequest.query.order_by(TagRequest.weight.desc()
                ).paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "oldest":
        tag_requests = TagRequest.query.order_by(TagRequest.requested.asc()
                ).paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "newest":
        tag_requests = TagRequest.query.order_by(TagRequest.requested.desc()
                ).paginate(page, app.config["CARDS_PER_PAGE"], False)
    else:
        tag_requests = TagRequest.query.order_by(TagRequest.weight.desc()
                ).paginate(page, app.config["CARDS_PER_PAGE"], False)

    sorts = {
            "tag": url_for("tag_request_index", sort="tag", page=page),
            "weight": url_for("tag_request_index", sort="weight", page=page),
            "oldest": url_for("tag_request_index", sort="oldest", page=page),
            "newest": url_for("tag_request_index", sort="newest", page=page),
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

@app.route("/request/tag/", methods=["GET", "POST"])
@login_required
def tag_request():
    if not current_user.has_right("create_tags"):
        current_user.authorize_rep(app.config["AUTHORIZATION"]["TAG_REQUEST"])
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
        current_user.authorize_rights("edit_tag_requests")
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
            tag_request.notify_approval()
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
    tag_request.notify_rejection()
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
