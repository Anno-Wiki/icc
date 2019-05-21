"""Administrative routes for users."""
import jwt
from time import time

from flask import (render_template, flash, redirect, url_for, request,
                   current_app)
from flask_login import current_user, login_required

from icc import db
from icc.email.email import send_beta_invite_email
from icc.funky import generate_next, authorize
from icc.forms import AreYouSureForm
from icc.admin.forms import InviteForm
from icc.admin import admin

from icc.models.user import User, UserFlag

# expires in seven days
expires_in = 604800

@admin.route('/user/invite', methods=['GET', 'POST'])
@login_required
@authorize('invite_beta')
def invite():
    if not current_app.config['HASH_REGISTRATION']:
        flash("The app is open to registration, dude, what are you thinking?")
        return url_for('main.index')
    form = InviteForm()
    if form.validate_on_submit():
        email = form.email.data
        token = jwt.encode(
            {'email': email, 'exp': time() + expires_in},
            current_app.config['SECRET_KEY'], algorithm='HS256').decode('utf-8')
        print(token)

        send_beta_invite_email(email, token)
        flash(f"Invited {email}.")
    return render_template('forms/invite.html', form=form)


@admin.route('/user/<user_id>/delete/', methods=['GET', 'POST'])
@login_required
@authorize('anonymize_users')
def anonymize_user(user_id):
    """Anonymize a user account (equivalent to deleting it)."""
    form = AreYouSureForm()
    user = User.query.get_or_404(user_id)
    redirect_url = url_for('user.profile', user_id=user.id)
    if form.validate_on_submit():
        user.displayname = f'x_user{user.id}'
        user.email = f'{user.id}'
        user.password_hash = '***'
        user.about_me = ''
        db.session.commit()
        flash("Account anonymized.")
        return redirect(redirect_url)

    text = f"""If you click submit you will forcibly anonymize this user
    ({user.displayname})."""
    return render_template('forms/delete_check.html', title="Are you sure?",
                           form=form, text=text)


@admin.route('/lock/user/<user_id>/')
@login_required
@authorize('lock_users')
def lock_user(user_id):
    """Lock a user account."""
    user = User.query.get_or_404(user_id)
    redirect_url = generate_next(url_for('user.profile', user_id=user.id))
    user.locked = not user.locked
    db.session.commit()
    if user.locked:
        flash(f"User account {user.displayname} locked.")
    else:
        flash(f"User account {user.displayname} unlocked.")
    return redirect(redirect_url)


@admin.route('/flags/user/all/')
@login_required
@authorize('resolve_user_flags')
def all_user_flags():
    """Display all user flags for all users."""
    default = 'flag'
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', default, type=str)

    sorts = {
        'user': (UserFlag.query.join(User, User.id==UserFlag.user_id)
                 .order_by(User.displayname.asc())),
        'flag': (UserFlag.query.join(UserFlag.enum_cls)
                 .order_by(UserFlag.enum_cls.enum.asc())),
        'time-thrown': UserFlag.query.order_by(UserFlag.time_thrown.desc()),
        'thrower': (UserFlag.query.join(User, User.id==UserFlag.user_id)
                    .order_by(User.displayname.asc())),
    }

    sort = sort if sort in sorts else default
    flags = sorts[sort].filter(UserFlag.time_resolved==None)\
        .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    if not flags.items and page > 1:
        abort(404)

    sorturls = {key: url_for('admin.all_user_flags', page=page, sort=key) for
                key in sorts.keys()}
    next_page = (url_for('admin.all_user_flags', page=flags.next_num, sort=sort)
                 if flags.has_next else None)
    prev_page = (url_for('admin.all_user_flags', page=flags.prev_num, sort=sort)
                 if flags.has_prev else None)
    return render_template('indexes/all_user_flags.html',
                           title=f"User Flags",
                           next_page=next_page, prev_page=prev_page,
                           sort=sort, sorts=sorturls,
                           flags=flags.items)


@admin.route('/flags/user/<user_id>/')
@login_required
@authorize('resolve_user_flags')
def user_flags(user_id):
    """Display all flags for a given user."""
    default = 'unresolved'
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', default, type=str)
    user = User.query.get_or_404(user_id)

    sorts = {
        'unresolved': user.flags.order_by(UserFlag.time_resolved.desc()),
        'flag': (user.flags.join(UserFlag.enum_cls)
                .order_by(UserFlag.enum_cls.enum.asc())),
        'time-thrown': user.flags.order_by(UserFlag.time_thrown.desc()),
        'thrower': (user.flags.join(User, UserFlag.user_id==User.id)
                    .order_by(User.displayname.asc())),
        'resolver': (user.flags.join(User, UserFlag.user_id==User.id)
                     .order_by(User.displayname.asc())),
        'time-resolved': (user.flags
                          .order_by(UserFlag.time_resolved.desc())),
    }

    sort = sort if sort in sorts else default
    flags = sorts[sort]\
        .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    if not flags.items and page > 1:
        abort(404)

    sorturls = {key: url_for('admin.user_flags', user_id=user_id, page=page,
                             sort=key) for key in sorts.keys()}
    next_page = (url_for('admin.user_flags', user_id=user.id,
                         page=flags.next_num, sort=sort) if flags.has_next else
                 None)
    prev_page = (url_for('admin.user_flags', user_id=user.id,
                         page=flags.prev_num, sort=sort) if flags.has_prev else
                 None)
    return render_template('indexes/user_flags.html',
                           title=f"{user.displayname} flags",
                           next_page=next_page, prev_page=prev_page,
                           sort=sort, sorts=sorturls,
                           user=user, flags=flags.items)


@admin.route('/flags/mark/user_flag/<flag_id>/')
@login_required
@authorize('resolve_user_flags')
def mark_user_flag(flag_id):
    """Mark a specific user flag resolved or unresolved."""
    flag = UserFlag.query.get_or_404(flag_id)
    redirect_url = generate_next(url_for('admin.user_flags',
                                         user_id=flag.user_id))
    if flag.time_resolved:
        flag.unresolve()
        flash("Flag unresolved.")
    else:
        flag.resolve(current_user)
        flash("Flag resolved.")
    db.session.commit()
    return redirect(redirect_url)


@admin.route('/flags/mark_all/<user_id>/')
@login_required
@authorize('resolve_user_flags')
def mark_all_user_flags(user_id):
    """Mark all user flags resolved or unresolved."""
    user = User.query.get_or_404(user_id)
    redirect_url = generate_next(url_for('admin.user_flags', user_id=user.id))
    for flag in user.active_flags:
        flag.resolve(current_user)
    flash("All active user flags resolved.")
    db.session.commit()
    return redirect(redirect_url)
