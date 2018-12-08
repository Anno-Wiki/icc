from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required

from app import app, db
from app.models import User, Text, Writer, Annotation, Edit, Tag, BookRequest,\
        TagRequest, UserFlagEnum, Notification, NotificationObject,\
        AnnotationFlagEnum
from app.email.email import send_password_reset_email
from app.funky import is_filled, generate_next
from app.forms import AreYouSureForm

from app.user import user
from app.user.forms import LoginForm, RegistrationForm, EditProfileForm,\
        ResetPasswordRequestForm, ResetPasswordForm

# flag user
@user.route("/<user_id>/flag/<flag_id>/")
@login_required
def flag_user(flag_id, user_id):
    user = User.query.get_or_404(user_id)
    flag = UserFlagEnum.query.get_or_404(flag_id)
    redirect_url = generate_next(url_for("user.profile", user_id=user.id))
    user.flag(flag, current_user)
    db.session.commit()
    flash(f"User {user.displayname} flagged \"{flag.flag}\"")
    return redirect(redirect_url)

###############################
## Login and Register Routes ##
###############################

@user.route("/login", methods=["GET", "POST"])
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

@user.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))

@user.route("/register", methods=["GET", "POST"])
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

####################
## Profile Routes ##
####################

@user.route("/list/")
def index():
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
            "reputation": url_for("user.index", page=page, sort="reputation"),
            "name": url_for("user.index", page=page, sort="name"),
            "annotations": url_for("user.index", page=page, sort="annotations"),
            "edits": url_for("user.index", page=page, sort="edits"),
            }
    next_page = url_for("user.index", page=users.next_num, sort=sort) \
            if users.has_next else None
    prev_page = url_for("user.index", page=users.prev_num, sort=sort) \
            if users.has_prev else None
    return render_template("indexes/users.html", title="Users",
            users=users.items, next_page=next_page, prev_page=prev_page,
            sort=sort, sorts=sorts)

@user.route("/<user_id>/profile")
@user.route("/profile", defaults={"user_id":None})
def profile(user_id):
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "newest", type=str)
    user = User.query.get_or_404(user_id) if user_id else current_user
    if not user.is_authenticated:
        redirect(url_for("user.index"))
    if sort == "weight":
        annotations = user.annotations.order_by(Annotation.weight.desc()
                ).paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "newest":
        annotations = user.annotations.order_by(Annotation.timestamp.desc()
                ).paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "oldest":
        annotations = user.annotations.order_by(Annotation.timestamp.asc()
                ).paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    else:
        annotations = user.annotations.order_by(Annotation.timestamp.desc()
                ).paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    sorts = {
            "newest": url_for("user.profile", user_id=user_id, sort="newest", page=page),
            "oldest": url_for("user.profile", user_id=user_id, sort="oldest", page=page),
            "weight": url_for("user.profile", user_id=user_id, sort="weight", page=page),
            }
    userflags = UserFlagEnum.query.all()
    annotationflags = AnnotationFlagEnum.query.all()

    next_page = url_for("user.profile", user_id=user.id, page=annotations.next_num,
            sort=sort) if annotations.has_next else None
    prev_page = url_for("user.profile", user_id=user.id, page=annotations.prev_num,
            sort=sort) if annotations.has_prev else None
    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None

    return render_template("view/user.html", title=f"User {user.displayname}",
            user=user, annotations=annotations.items, uservotes=uservotes,
            next_page=next_page, prev_page=prev_page, userflags=userflags,
            annotationflags=annotationflags, sort=sort, sorts=sorts)

@user.route("/profile/edit", methods=["GET", "POST"])
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
        return redirect(url_for("user.profile", user_id=current_user.id))
    elif request.method == "GET":
        form.displayname.data = current_user.displayname
        form.about_me.data = current_user.about_me
    return render_template("forms/edit_profile.html", title="Edit Profile",
                           form=form)

@user.route("/profile/delete", methods=["GET", "POST"])
@login_required
def delete_profile_check():
    form = AreYouSureForm()
    redirect_url = generate_next(url_for("user.profile", user_id=current_user.id))
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

###########
## Inbox ##
###########

@user.route("/inbox")
@login_required
def inbox():
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "seen", type=str)
    if sort == "time":
        notifications = current_user.notifications\
                .outerjoin(NotificationObject)\
                .order_by(NotificationObject.timestamp.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time_invert":
        notifications = current_user.notifications\
                .outerjoin(NotificationObject)\
                .order_by(NotificationObject.timestamp.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "type":
        notifications = current_user.notifications\
                .join(NotificationObject)\
                .join(NotificationEnum)\
                .order_by(NotificationEnum.public_code.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "type_invert":
        notifications = current_user.notifications\
                .join(NotificationObject)\
                .join(NotificationEnum)\
                .order_by(NotificationEnum.public_code.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "read":
        notifications = current_user.notifications\
                .order_by(Notification.seen.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "read_invert":
        notifications = current_user.notifications\
                .order_by(Notification.seen.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    else:
        notifications = current_user.notifications\
                .order_by(Notification.seen.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    sorts = {
            "read": url_for("user.inbox", sort="read", page=page),
            "read_invert": url_for("user.inbox", sort="read_invert", page=page),
            "time": url_for("user.inbox", sort="time", page=page),
            "time_invert": url_for("user.inbox", sort="time_invert", page=page),
            "type": url_for("user.inbox", sort="type", page=page),
            "type_invert": url_for("user.inbox", sort="type_invert", page=page),
            "information": url_for("user.inbox", sort="information", page=page),
            "information_invert": url_for("user.inbox", sort="information_invert",
                page=page),
            }

    next_page = url_for("user.inbox", page=notifications.next_num, sort=sort) \
            if notifications.has_next else None
    prev_page = url_for("user.inbox", page=notifications.prev_num, sort=sort) \
            if notifications.has_prev else None

    return render_template("indexes/inbox.html",
            notifications=notifications.items, page=page, sort=sort,
            sorts=sorts, next_page=next_page, prev_page=prev_page)

@user.route("/inbox/mark/<notification_id>")
@login_required
def mark_notification(notification_id):
    redirect_url = generate_next(url_for("user.inbox"))
    notification = Notification.query.get_or_404(notification_id)
    if notification.seen:
        notification.mark_unread()
    else:
        notification.mark_read()
    db.session.commit()
    return redirect(redirect_url)

@user.route("/inbox/mark/all")
@login_required
def mark_all_read():
    redirect_url = generate_next(url_for("user.inbox"))
    notifications = current_user.notifications.filter_by(seen=False).all()
    for notification in notifications:
        notification.mark_read()
    db.session.commit()
    return redirect(redirect_url)

###########################
## Reset Password Routes ##
###########################

@user.route("/password/reset/request", methods=["GET", "POST"])
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
            return redirect(url_for("user.login"))
        else:
            flash("Email not found.")
    return render_template("forms/reset_password_request.html",
            title="Reset Password", form=form)

@user.route("/password/reset/<token>", methods=["GET", "POST"])
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
        return redirect(url_for("user.login"))
    return render_template("forms/reset_password.html", form=form)


###################
## follow routes ##
###################

@user.route("/follow/list/users")
@login_required
def users_followed_idx():
    followings = current_user.followed_users.all()
    for f in followings:
        f.url = url_for("user.profile", user_id=f.id)
        f.name = f.displayname
        f.unfollow_url = url_for("user.follow_user", user_id=f.id)
    return render_template("indexes/followings.html", title="Followed Users",
            followings=followings, type="users", column1="Display Name")

@user.route("/follow/list/authors")
@login_required
def authors_followed_idx():
    followings = current_user.followed_authors.all()
    for f in followings:
        f.url = url_for("author", name=f.url)
        f.unfollow_url = url_for("user.follow_author", author_id=f.id)
    return render_template("indexes/followings.html", title="Followed Authors",
            followings=followings, type="authors", column1="Name")

# follow user
@user.route("/follow/user/<user_id>/")
@login_required
def follow_user(user_id):
    user = User.query.get_or_404(user_id)
    redirect_url = generate_next(url_for("user.profile", user_id=user.id))
    if user == current_user:
        flash("You can't follow yourself.")
        redirect(redirect_url)
    elif user in current_user.followed_users:
        current_user.followed_users.remove(user)
    else:
        current_user.followed_users.append(user)
    db.session.commit()
    return redirect(redirect_url)

# follow author
@user.route("/follow/author/<author_id>")
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

# follow book
@user.route("/user/follow/book/<book_id>")
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

# follow book request
@user.route("/follow/request/book/<book_request_id>")
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

# follow tag request
@user.route("/follow/request/tag/<tag_request_id>/")
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

# follow tag
@user.route("/follow/tag/<tag_id>/")
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

# follow annotation
@user.route("/follow/annotation/<annotation_id>/")
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
