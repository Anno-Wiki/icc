from flask import (render_template, flash, redirect, url_for, request,
                   current_app)
from flask_login import current_user, login_required

from icc import db
from icc.funky import generate_next, authorize
from icc.forms import AreYouSureForm
from icc.admin import admin

from icc.models.user import User, UserFlag, UserFlagEnum


@admin.route('/user/<user_id>/delete/', methods=['GET', 'POST'])
@login_required
@authorize('anonymize_users')
def anonymize_user(user_id):
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
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'marked', type=str)

    if sort == 'marked':
        flags = UserFlag.query\
            .order_by(UserFlag.time_resolved.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'marked_invert':
        flags = UserFlag.query\
            .order_by(UserFlag.time_resolved.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'flag':
        flags = UserFlag.query\
            .outerjoin(UserFlagEnum)\
            .order_by(UserFlagEnum.flag.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'flag_invert':
        flags = UserFlag.query\
            .outerjoin(UserFlagEnum)\
            .order_by(UserFlagEnum.flag.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'time':
        flags = UserFlag.query\
            .order_by(UserFlag.time_thrown.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'time_invert':
        flags = UserFlag.query\
            .order_by(UserFlag.time_thrown.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'thrower':
        flags = UserFlag.query\
            .outerjoin(User, User.id == UserFlag.thrower_id)\
            .order_by(User.displayname.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'thrower_invert':
        flags = UserFlag.query\
            .outerjoin(User, User.id == UserFlag.thrower_id)\
            .order_by(User.displayname.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'resolver':
        flags = UserFlag.query\
            .outerjoin(User, User.id == UserFlag.resolver_id)\
            .order_by(User.displayname.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'resolver_invert':
        flags = UserFlag.query\
            .outerjoin(User, User.id == UserFlag.resolver_id)\
            .order_by(User.displayname.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'time_resolved':
        flags = UserFlag.query\
            .order_by(UserFlag.time_resolved.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'time_resolved_invert':
        flags = UserFlag.query\
            .order_by(UserFlag.time_resolved.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'user':
        flags = UserFlag.query\
            .outerjoin(User, User.id == UserFlag.user_id)\
            .order_by(User.displayname.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'user_invert':
        flags = UserFlag.query\
            .outerjoin(User, User.id == UserFlag.user_id)\
            .order_by(User.displayname.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    else:
        flags = UserFlag.query\
            .order_by(UserFlag.time_resolved.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)

    sorts = {
            'marked': url_for(
                'admin.all_user_flags', sort='marked', page=page),
            'marked_invert': url_for(
                'admin.all_user_flags', sort='marked_invert', page=page),
            'flag': url_for(
                'admin.all_user_flags', sort='flag', page=page),
            'flag_invert': url_for(
                'admin.all_user_flags', sort='flag_invert', page=page),
            'time': url_for(
                'admin.all_user_flags', sort='time', page=page),
            'time_invert': url_for(
                'admin.all_user_flags', sort='time_invert', page=page),
            'thrower': url_for(
                'admin.all_user_flags', sort='thrower', page=page),
            'thrower_invert': url_for(
                'admin.all_user_flags', sort='thrower_invert', page=page),
            'resolver': url_for(
                'admin.all_user_flags', sort='resolver', page=page),
            'resolver_invert': url_for(
                'admin.all_user_flags', sort='resolver_invert', page=page),
            'time_resolved': url_for(
                'admin.all_user_flags', sort='time_resolved', page=page),
            'time_resolved_invert': url_for(
                'admin.all_user_flags', sort='time_resolved_invert', page=page),
            'user': url_for(
                'admin.all_user_flags', sort='user', page=page),
            'user_invert': url_for(
                'admin.all_user_flags', sort='user_invert', page=page),
            }

    next_page = url_for('admin.all_user_flags', page=flags.next_num, sort=sort)\
        if flags.has_next else None
    prev_page = url_for('admin.all_user_flags', page=flags.prev_num, sort=sort)\
        if flags.has_prev else None
    return render_template('indexes/all_user_flags.html', title=f"User Flags",
                           next_page=next_page, prev_page=prev_page,
                           flags=flags.items, sort=sort, sorts=sorts)


@admin.route('/flags/user/<user_id>/')
@login_required
@authorize('resolve_user_flags')
def user_flags(user_id):
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'marked', type=str)
    user = User.query.get_or_404(user_id)
    if sort == 'marked':
        flags = user.flag_history\
            .order_by(UserFlag.time_resolved.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'marked_invert':
        flags = user.flag_history\
            .order_by(UserFlag.time_resolved.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'flag':
        flags = user.flag_history\
            .outerjoin(UserFlagEnum)\
            .order_by(UserFlagEnum.flag.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'flag_invert':
        flags = user.flag_history\
            .outerjoin(UserFlagEnum)\
            .order_by(UserFlagEnum.flag.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'time':
        flags = user.flag_history\
            .order_by(UserFlag.time_thrown.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'time_invert':
        flags = user.flag_history\
            .order_by(UserFlag.time_thrown.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'thrower':
        flags = user.flag_history\
            .outerjoin(User, User.id == UserFlag.thrower_id)\
            .order_by(User.displayname.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'thrower_invert':
        flags = user.flag_history\
            .outerjoin(User, User.id == UserFlag.thrower_id)\
            .order_by(User.displayname.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'resolver':
        flags = user.flag_history\
            .outerjoin(User, User.id == UserFlag.resolver_id)\
            .order_by(User.displayname.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'resolver_invert':
        flags = user.flag_history\
            .outerjoin(User, User.id == UserFlag.resolver_id)\
            .order_by(User.displayname.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'time_resolved':
        flags = user.flag_history\
            .order_by(UserFlag.time_resolved.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'time_resolved_invert':
        flags = user.flag_history\
            .order_by(UserFlag.time_resolved.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)

    else:
        flags = user.flag_history\
            .order_by(UserFlag.time_resolved.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)

    sorts = {
            'marked': url_for(
                'admin.user_flags', user_id=user.id, sort='marked', page=page),
            'marked_invert': url_for(
                'admin.user_flags', user_id=user.id, sort='marked_invert',
                page=page),
            'flag': url_for(
                'admin.user_flags', user_id=user.id, sort='flag', page=page),
            'flag_invert': url_for(
                'admin.user_flags', user_id=user.id, sort='flag_invert',
                page=page),
            'time': url_for(
                'admin.user_flags', user_id=user.id, sort='time', page=page),
            'time_invert': url_for(
                'admin.user_flags', user_id=user.id, sort='time_invert',
                page=page),
            'thrower': url_for(
                'admin.user_flags', user_id=user.id, sort='thrower', page=page),
            'thrower_invert': url_for(
                'admin.user_flags', user_id=user.id, sort='thrower_invert',
                page=page),
            'resolver': url_for(
                'admin.user_flags', user_id=user.id, sort='resolver',
                page=page),
            'resolver_invert': url_for(
                'admin.user_flags', user_id=user.id, sort='resolver_invert',
                page=page),
            'time_resolved': url_for(
                'admin.user_flags', user_id=user.id, sort='time_resolved',
                page=page),
            'time_resolved_invert': url_for(
                'admin.user_flags', user_id=user.id,
                sort='time_resolved_invert', page=page),
            }

    next_page = url_for(
        'admin.user_flags', user_id=user.id, page=flags.next_num, sort=sort)\
        if flags.has_next else None
    prev_page = url_for(
        'admin.user_flags', user_id=user.id, page=flags.prev_num, sort=sort)\
        if flags.has_prev else None
    return render_template(
        'indexes/user_flags.html', title=f"{user.displayname} flags",
        next_page=next_page, prev_page=prev_page, sort=sort, sorts=sorts,
        user=user, flags=flags.items)


@admin.route('/flags/mark/user_flag/<flag_id>/')
@login_required
@authorize('resolve_user_flags')
def mark_user_flag(flag_id):
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
def mark_user_flags(user_id):
    user = User.query.get_or_404(user_id)
    redirect_url = generate_next(url_for('admin.user_flags', user_id=user.id))
    for flag in user.active_flags:
        flag.resolve(current_user)
    db.session.commit()
    return redirect(redirect_url)
