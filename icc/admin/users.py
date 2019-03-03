"""Administrative routes for users."""
from flask import (render_template, flash, redirect, url_for, request,
                   current_app)
from flask_login import current_user, login_required

from icc import db
from icc.funky import generate_next, authorize
from icc.forms import AreYouSureForm
from icc.admin import admin

from icc.models.user import User, UserFlag


@admin.route('/user/<user_id>/delete/', methods=['GET', 'POST'])
@login_required
@authorize('anonymize_users')
def anonymize_user(user_id):
    """Anonymize a user account (equivalent to deleting it)."""
    form = AreYouSureForm()
    user = User.query.get_or_404(user_id)
    redirect_url = url_for('user', user_id=user.id)
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
    redirect_url = generate_next(url_for('user', user_id=user.id))
    user.locked = not user.locked
    db.session.commit()
    flash(f"User account {user.displayname} locked.")
    return redirect(redirect_url)


@admin.route('/flags/user/all/')
@login_required
@authorize('resolve_user_flags')
def all_user_flags():
    """Display all user flags for all users."""
    default = 'marked'
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', default, type=str)

    sorts = {
        'marked': UserFlag.query.order_by(UserFlag.time_resolved.desc()),
        'marked_invert': UserFlag.query.order_by(UserFlag.time_resolved.asc()),
        'flag': (UserFlag.query.join(UserFlag.enum_cls)
                 .order_by(UserFlag.enum_cls.enum.asc())),
        'flag_invert': (UserFlag.query.join(UserFlag.enum_cls)
                        .order_by(UserFlag.enum_cls.enum.desc())),
        'time': UserFlag.query.order_by(UserFlag.time_thrown.desc()),
        'time_invert': UserFlag.query.order_by(UserFlag.time_thrown.asc()),
        'thrower': (UserFlag.query.join(User, User.id==UserFlag.user_id)
                    .order_by(User.displayname.asc())),
        'thrower_invert': (UserFlag.query.join(User, User.id==UserFlag.user_id)
                           .order_by(User.displayname.desc())),
        'resolver': (UserFlag.query.join(User, User.id==UserFlag.user_id)
                     .order_by(User.displayname.asc())),
        'resolver_invert': (UserFlag.query.join(User, User.id==UserFlag.user_id)
                            .order_by(User.displayname.desc())),
        'time_resolved': UserFlag.query.order_by(UserFlag.time_resolved.desc()),
        'time_resolved_invert': (UserFlag.query
                                 .order_by(UserFlag.time_resolved.asc())),
        'user': (UserFlag.query.join(User, User.id==UserFlag.user_id)
                 .order_by(User.displayname.asc())),
        'user_invert': (UserFlag.query
                        .join(User, User.id==UserFlag.user_id)
                        .order_by(User.displayname.desc())),
    }

    sort = sort if sort in sorts else default
    flags = sorts[sort]\
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
    default = 'marked'
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', default, type=str)
    user = User.query.get_or_404(user_id)

    sorts = {
        'marked': user.flags.order_by(UserFlag.time_resolved.desc()),
        'marked_invert': (user.flags
                          .order_by(UserFlag.time_resolved.asc())),
        'flag': (user.flags.join(UserFlag.enum_cls)
                .order_by(UserFlag.enum_cls.enum.asc())),
        'flag_invert': (user.flags.join(UserFlag.enum_cls)
                        .order_by(UserFlag.enum_cls.enum.desc())),
        'time': user.flags.order_by(UserFlag.time_thrown.desc()),
        'time_invert': user.flags.order_by(UserFlag.time_thrown.asc()),
        'thrower': (user.flags.join(User, UserFlag.user_id==User.id)
                    .order_by(User.displayname.asc())),
        'thrower_invert': (user.flags.join(User, UserFlag.user_id==User.id)
                        .order_by(User.displayname.desc())),
        'resolver': (user.flags.join(User, UserFlag.user_id==User.id)
                     .order_by(User.displayname.asc())),
        'resolver_invert': (user.flags.join(User, UserFlag.user_id==User.id)
                            .order_by(User.displayname.desc())),
        'time_resolved': (user.flags
                          .order_by(UserFlag.time_resolved.desc())),
        'time_resolved_invert': (user.flags
                             .order_by(UserFlag.time_resolved.asc())),
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
    else:
        flag.resolve(current_user)
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
    db.session.commit()
    return redirect(redirect_url)
