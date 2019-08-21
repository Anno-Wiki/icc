"""The main methods for users."""
from flask import (render_template, flash, redirect, url_for, request, abort,
                   current_app)
from flask_login import current_user, login_required

from sqlalchemy import and_

from icc import db
from icc.funky import generate_next
from icc.user import user

from icc.models.annotation import Annotation, Edit
from icc.models.user import User, UserFlag, ReputationChange


@user.route('/list')
def index():
    """An index of all users."""
    default = 'reputation'
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', default, type=str)

    sorts = {
        'reputation': User.query.order_by(User.reputation.desc()),
        'displayname': User.query.order_by(User.displayname.asc()),
        'annotations': (User.query.join(Annotation).group_by(User.id)
                        .order_by(db.func.count(Annotation.id).desc())),
        'edits': (User.query .join(Edit, and_(Edit.editor_id==User.id,
                                              Edit.num>0))
                  .group_by(User.id).order_by(db.func.count(Edit.id).desc())),
    }

    sort = sort if sort in sorts else default
    users = sorts[sort].paginate(page, current_app.config['CARDS_PER_PAGE'],
                                 False)
    if not users.items and page > 1:
        abort(404)

    sorturls = {key: url_for('user.index', page=page, sort=key) for key in
                sorts.keys()}
    next_page = (url_for('user.index', page=users.next_num, sort=sort) if
                 users.has_next else None)
    prev_page = (url_for('user.index', page=users.prev_num, sort=sort) if
                 users.has_prev else None)
    return render_template('indexes/users.html', title="Users",
                           next_page=next_page, prev_page=prev_page,
                           sort=sort, sorts=sorturls,
                           users=users.items)


@user.route('/<user_id>/profile')
def profile(user_id):
    """A user profile."""
    user = User.query.get_or_404(user_id)
    userflags = UserFlag.enum_cls.query.all()
    return render_template('view/user.html', title=f"User {user.displayname}",
                           userflags=userflags, user=user)


@user.route('/<user_id>/flag/<flag_id>')
@login_required
def flag_user(flag_id, user_id):
    """To flag a user."""
    user = User.query.get_or_404(user_id)
    flag = UserFlag.enum_cls.query.get_or_404(flag_id)
    redirect_url = generate_next(url_for('user.profile', user_id=user.id))
    UserFlag.flag(user, flag, current_user)
    db.session.commit()
    flash(f"User {user.displayname} flagged \"{flag.enum}\"")
    return redirect(redirect_url)


@user.route('/<user_id>/annotations')
def user_annotations(user_id):
    """The annotations for the edition."""
    default = 'newest'
    sort = request.args.get('sort', default, type=str)
    page = request.args.get('page', 1, type=int)
    user = User.query.get_or_404(user_id)

    sorts = {
        'newest': user.annotations.order_by(Annotation.timestamp.desc()),
        'oldest': user.annotations.order_by(Annotation.timestamp.asc()),
        'modified': (user.annotations.join(Edit)
                     .filter(Edit.current==True)
                     .order_by(Edit.timestamp.desc())),
        'weight': user.annotations.order_by(Annotation.weight.desc()),
    }

    sort = sort if sort in sorts else default
    annotations = sorts[sort].filter(Annotation.active==True)\
        .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    if not annotations.items and page > 1:
        abort(404)

    sorturls = {key: url_for('user.user_annotations', user_id=user_id,
                             page=page, sort=key) for key in sorts.keys()}
    next_page = (url_for('user.user_annotations', user_id=user_id, sort=sort,
                         page=annotations.next_num) if annotations.has_next else
                 None)
    prev_page = (url_for('user.user_annotations', user_id=user_id, sort=sort,
                         page=annotations.prev_num) if annotations.has_prev else
                 None)
    return render_template('indexes/annotation_list.html',
                           title=f"{user.displayname} - Annotations",
                           next_page=next_page, prev_page=prev_page,
                           sorts=sorturls, sort=sort,
                           annotations=annotations.items)


@user.route('/<user_id>/reputation')
def reputation(user_id):
    user = User.query.get_or_404(user_id)
    page = request.args.get('page', 1, type=int)

    changes = user.reputation_changes \
        .order_by(ReputationChange.timestamp.desc()) \
        .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)


    next_page = (url_for('user.reputation', user_id=user_id,
                         page=changes.next_num) if changes.has_next else None)
    prev_page = (url_for('user.reputation', user_id=user_id,
                         page=changes.prev_num) if changes.has_prev else None)
    return render_template('indexes/reputation.html',
                           title=f"{user.displayname} - Reputation",
                           next_page=next_page, prev_page=prev_page,
                           changes=changes.items)
