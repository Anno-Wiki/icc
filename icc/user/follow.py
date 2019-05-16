"""All the routes to follow a thing. Any thing, really."""
from flask import flash, redirect, request
from flask_login import current_user, login_required

from icc import db
from icc.funky import generate_next
from icc.user import user

from icc.models.annotation import Annotation, Tag
from icc.models.content import Text, Writer, Edition
from icc.models.request import TextRequest, TagRequest
from icc.models.user import User
from icc import classes
from string import ascii_lowercase as lowercase


@user.route('/follow')
@login_required
def follow():
    entity_cls = classes.get(request.args.get('entity'), None)
    entity_id = request.args.get('id').strip(lowercase)
    if not entity_cls:
        abort(404)
    if not issubclass(entity_cls, classes['FollowableMixin']):
        abort(501)
    entity = entity_cls.query.get_or_404(entity_id)
    redirect_url = generate_next(entity.url)
    followings = getattr(current_user,
                         f'followed_{entity_cls.__name__.lower()}s')
    if entity in followings:
        followings.remove(entity)
    else:
        followings.append(entity)
    db.session.commit()
    return redirect(redirect_url)

def follow_entity(entity, followed):
    """A helper function to reduce code duplication. Simply process the
    following abstractly.
    """
    redirect_url = generate_next(entity.url)
    if entity in followed:
        followed.remove(entity)
    else:
        followed.append(entity)
    db.session.commit()
    return redirect(redirect_url)

@user.route('/follow/user/<user_id>')
@login_required
def follow_user(user_id):
    """Follow a user."""
    user = User.query.get_or_404(user_id)
    redirect_url = generate_next(user.url)
    if user == current_user:
        flash("You can't follow yourself.")
        return redirect(redirect_url)
    else:
        return follow_entity(user, current_user.followed_users)
