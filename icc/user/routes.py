from flask import render_template, flash, redirect, url_for, request, abort,\
        current_app
from flask_login import login_user, logout_user, current_user, login_required

from sqlalchemy import and_

from icc import db
from icc.models import User, Text, Writer, Annotation, Edit, Tag, TextRequest,\
    TagRequest, UserFlagEnum, AnnotationFlagEnum
from icc.email.email import send_password_reset_email
from icc.funky import is_filled, generate_next
from icc.forms import AreYouSureForm

from icc.user import user
from icc.user.forms import LoginForm, RegistrationForm, EditProfileForm,\
    ResetPasswordRequestForm, ResetPasswordForm



# flag user
@user.route('/<user_id>/flag/<flag_id>')
@login_required
def flag_user(flag_id, user_id):
    user = User.query.get_or_404(user_id)
    flag = UserFlagEnum.query.get_or_404(flag_id)
    redirect_url = generate_next(url_for('user.profile', user_id=user.id))
    user.flag(flag, current_user)
    db.session.commit()
    flash(f"User {user.displayname} flagged \"{flag.flag}\"")
    return redirect(redirect_url)



###############################
## Login and Register Routes ##
###############################

@user.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.locked:
            flash("That account is locked.")
            return redirect(url_for('user.login'))
        elif user is None or not user.check_password(form.password.data):
            flash("Invalid email or password")
            return redirect(url_for('user.login'))
        login_user(user, remember=form.remember_me.data)

        redirect_url = generate_next(url_for('main.index'))
        return redirect(redirect_url)

    return render_template('login.html', title="Sign In", form=form)


@user.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))


@user.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(displayname=form.displayname.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Congratulations, you are now a registered user!")
        return redirect(url_for('user.login'))
    return render_template('forms/register.html', title="Register", form=form)



####################
## Profile Routes ##
####################

@user.route('/list')
def index():
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'reputation', type=str)
    if sort == 'reputation':
        users = User.query.order_by(User.reputation.desc())\
                .paginate(page, current_app.config['CARDS_PER_PAGE'], False)
    elif sort == 'name':
        users = User.query.order_by(User.displayname.asc())\
                .paginate(page, current_app.config['CARDS_PER_PAGE'], False)
    elif sort == 'annotations':
        users = User.query.outerjoin(Annotation).group_by(User.id)\
                .order_by(db.func.count(Annotation.id).desc())\
                .paginate(page, current_app.config['CARDS_PER_PAGE'], False)
    elif sort == 'edits':
        users = User.query.outerjoin(Edit, and_(Edit.editor_id==User.id,
                        Edit.num>0)).group_by(User.id)\
                    .order_by(db.func.count(Edit.id).desc())\
                    .paginate(page, current_app.config['CARDS_PER_PAGE'], False)
    else:
        users = User.query\
                .order_by(User.reputation.desc())\
                .paginate(page, current_app.config['CARDS_PER_PAGE'], False)

    if not users.items and page > 1:
        abort(404)

    sorts = {
            'reputation': url_for('user.index', page=page, sort='reputation'),
            'name': url_for('user.index', page=page, sort='name'),
            'annotations': url_for('user.index', page=page, sort='annotations'),
            'edits': url_for('user.index', page=page, sort='edits'),
            }

    next_page = url_for('user.index', page=users.next_num, sort=sort) \
            if users.has_next else None
    prev_page = url_for('user.index', page=users.prev_num, sort=sort) \
            if users.has_prev else None

    return render_template('indexes/users.html', title="Users",
            next_page=next_page, prev_page=prev_page, sort=sort, sorts=sorts,
            users=users.items)


@user.route('/<user_id>/profile')
@user.route('/profile', defaults={'user_id': None})
def profile(user_id):
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'newest', type=str)
    user = User.query.get_or_404(user_id) if user_id else current_user
    if not user.is_authenticated:
        redirect(url_for('user.index'))
    if sort == 'weight':
        annotations = user.annotations.order_by(Annotation.weight.desc())\
                .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    elif sort == 'newest':
        annotations = user.annotations.order_by(Annotation.timestamp.desc())\
                .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    elif sort == 'oldest':
        annotations = user.annotations.order_by(Annotation.timestamp.asc())\
                .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    else:
        annotations = user.annotations.order_by(Annotation.timestamp.desc())\
                .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    sorts = {
            'newest': url_for('user.profile', user_id=user_id, sort='newest',
                page=page),
            'oldest': url_for('user.profile', user_id=user_id, sort='oldest',
                page=page),
            'weight': url_for('user.profile', user_id=user_id, sort='weight',
                page=page),
            }

    userflags = UserFlagEnum.query.all()
    annotationflags = AnnotationFlagEnum.query.all()

    next_page = url_for('user.profile', user_id=user.id, page=annotations.next_num,
            sort=sort) if annotations.has_next else None
    prev_page = url_for('user.profile', user_id=user.id, page=annotations.prev_num,
            sort=sort) if annotations.has_prev else None

    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None

    return render_template('view/user.html',
            title=f"User {user.displayname}",
            next_page=next_page, prev_page=prev_page, sort=sort, sorts=sorts,
            userflags=userflags, user=user, annotations=annotations.items,
            uservotes=uservotes, annotationflags=annotationflags)


@user.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()

    if form.validate_on_submit():
        current_user.displayname = form.displayname.data\
                if is_filled(form.displayname.data)\
                else f'user{current_user.id}'
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash("Your changes have been saved.")
        return redirect(url_for('user.profile', user_id=current_user.id))
    elif request.method == 'GET':
        form.displayname.data = current_user.displayname
        form.about_me.data = current_user.about_me

    return render_template('forms/edit_profile.html', title="Edit Profile", form=form)


@user.route('/profile/delete', methods=['GET', 'POST'])
@login_required
def delete_profile_check():
    form = AreYouSureForm()
    redirect_url = generate_next(url_for('user.profile', user_id=current_user.id))
    if form.validate_on_submit():
        current_user.displayname = f'x_user{current_user.id}'
        current_user.email = '{current_user.id}'
        current_user.password_hash = '***'
        current_user.about_me = ''
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
    return render_template('forms/delete_check.html', title="Are you sure?",
            form=form, text=text)


###########################
## Reset Password Routes ##
###########################

@user.route('/password/reset/request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
            flash("Check your email for the instructions to request your "
                    "password.")
            return redirect(url_for('user.login'))
        else:
            flash("Email not found.")
    return render_template('forms/reset_password_request.html',
            title="Reset Password", form=form)


@user.route('/password/reset/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash("Your password has been changed.")
        return redirect(url_for('user.login'))
    return render_template('forms/reset_password.html', form=form)



###################
## follow routes ##
###################

@user.route('/follow/list/users')
@login_required
def users_followed_idx():
    followings = current_user.followed_users.all()
    for f in followings:
        f.url = url_for('user.profile', user_id=f.id)
        f.name = f.displayname
        f.unfollow_url = url_for('user.follow_user', user_id=f.id)

    return render_template('indexes/followings.html', title="Followed Users",
            followings=followings, type='users', column1='Display Name')


@user.route('/follow/list/authors')
@login_required
def authors_followed_idx():
    followings = current_user.followed_authors.all()
    for f in followings:
        f.url = url_for('author', name=f.url)
        f.unfollow_url = url_for('user.follow_author', author_id=f.id)
    return render_template('indexes/followings.html', title="Followed Authors",
            followings=followings, type='authors', column1='Name')


# follow user
@user.route('/follow/user/<user_id>')
@login_required
def follow_user(user_id):
    user = User.query.get_or_404(user_id)
    redirect_url = generate_next(url_for('user.profile', user_id=user.id))
    if user == current_user:
        flash("You can't follow yourself.")
        redirect(redirect_url)
    elif user in current_user.followed_users:
        current_user.followed_users.remove(user)
    else:
        current_user.followed_users.append(user)
    db.session.commit()
    return redirect(redirect_url)


# follow writer
@user.route('/follow/writer/<writer_id>')
@login_required
def follow_writer(writer_id):
    writer = Writer.query.get_or_404(writer_id)
    redirect_url = generate_next(url_for('writer', writer_url=writer.url))
    if author in current_user.followed_writers:
        current_user.followed_writers.remove(writer)
    else:
        current_user.followed_writers.append(writer)
    db.session.commit()
    return redirect(redirect_url)


# follow text
@user.route('/user/follow/text/<text_id>')
@login_required
def follow_text(text_id):
    text = Text.query.get_or_404(text_id)
    redirect_url = generate_next(url_for('text', text_url=text.url))
    if text in current_user.followed_texts:
        current_user.followed_texts.remove(text)
    else:
        current_user.followed_texts.append(text)
    db.session.commit()
    return redirect(redirect_url)


# follow book request
@user.route('/follow/request/book/<book_request_id>')
@login_required
def follow_book_request(book_request_id):
    book_request = TextRequest.query.get_or_404(book_request_id)
    redirect_url = generate_next(url_for('view_book_request',
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
@user.route('/follow/request/tag/<tag_request_id>')
@login_required
def follow_tag_request(tag_request_id):
    tag_request = TagRequest.query.get_or_404(tag_request_id)
    redirect_url = generate_next(url_for('view_tag_request',
        tag_request_id=tag_request.id))
    if tag_request in current_user.followed_tag_requests:
        current_user.followed_tag_requests.remove(tag_request)
    else:
        current_user.followed_tag_requests.append(tag_request)
    db.session.commit()
    return redirect(redirect_url)


# follow tag
@user.route('/follow/tag/<tag_id>')
@login_required
def follow_tag(tag_id):
    tag = Tag.query.get_or_404(tag_id)
    redirect_url = generate_next(url_for('tag', tag=tag.tag))
    if tag in current_user.followed_tags:
        current_user.followed_tags.remove(tag)
    else:
        current_user.followed_tags.append(tag)
    db.session.commit()
    return redirect(redirect_url)


# follow annotation
@user.route('/follow/annotation/<annotation_id>')
@login_required
def follow_annotation(annotation_id):
    annotation = Annotation.query.get_or_404(annotation_id)

    redirect_url = generate_next(url_for('annotation',
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
