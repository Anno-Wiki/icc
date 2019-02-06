from flask import render_template, flash, redirect, url_for, request, abort,\
        current_app
from flask_login import login_user, logout_user, current_user, login_required

from sqlalchemy import and_

from icc import db
from icc.funky import generate_next
from icc.user import user
from icc.user.forms import LoginForm, RegistrationForm

from icc.models.annotation import Annotation, Edit,  AnnotationFlagEnum
from icc.models.user import User, UserFlagEnum


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


@user.route('/list')
def index():
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'reputation', type=str)
    if sort == 'reputation':
        users = User.query\
            .order_by(User.reputation.desc())\
            .paginate(page, current_app.config['CARDS_PER_PAGE'], False)
    elif sort == 'name':
        users = User.query\
            .order_by(User.displayname.asc())\
            .paginate(page, current_app.config['CARDS_PER_PAGE'], False)
    elif sort == 'annotations':
        users = User.query\
            .outerjoin(Annotation)\
            .group_by(User.id)\
            .order_by(db.func.count(Annotation.id).desc())\
            .paginate(page, current_app.config['CARDS_PER_PAGE'], False)
    elif sort == 'edits':
        users = User.query\
            .outerjoin(Edit, and_(Edit.editor_id == User.id, Edit.num > 0))\
            .group_by(User.id)\
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

    next_page = url_for('user.index', page=users.next_num, sort=sort)\
        if users.has_next else None
    prev_page = url_for('user.index', page=users.prev_num, sort=sort)\
        if users.has_prev else None

    return render_template(
        'indexes/users.html', title="Users", next_page=next_page,
        prev_page=prev_page, sort=sort, sorts=sorts, users=users.items)


@user.route('/<user_id>/profile')
@user.route('/profile', defaults={'user_id': None})
def profile(user_id):
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'newest', type=str)
    user = User.query.get_or_404(user_id) if user_id else current_user
    if not user.is_authenticated:
        redirect(url_for('user.index'))
    if sort == 'weight':
        annotations = user.annotations\
            .order_by(Annotation.weight.desc())\
            .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    elif sort == 'newest':
        annotations = user.annotations\
            .order_by(Annotation.timestamp.desc())\
            .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    elif sort == 'oldest':
        annotations = user.annotations\
            .order_by(Annotation.timestamp.asc())\
            .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    else:
        annotations = user.annotations\
            .order_by(Annotation.timestamp.desc())\
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

    next_page = url_for(
        'user.profile', user_id=user.id, page=annotations.next_num, sort=sort)\
        if annotations.has_next else None
    prev_page = url_for(
        'user.profile', user_id=user.id, page=annotations.prev_num, sort=sort)\
        if annotations.has_prev else None


    return render_template(
        'view/user.html', title=f"User {user.displayname}", next_page=next_page,
        prev_page=prev_page, sort=sort, sorts=sorts, userflags=userflags,
        user=user, annotations=annotations.items,
        annotationflags=annotationflags)


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
