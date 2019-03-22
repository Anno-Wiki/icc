"""All the routes to follow a thing. Any thing, really."""
from flask import flash, redirect
from flask_login import current_user, login_required

from icc import db
from icc.funky import generate_next
from icc.user import user

from icc.models.annotation import Annotation, Tag
from icc.models.content import Text, Writer, Edition
from icc.models.request import TextRequest, TagRequest
from icc.models.user import User


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


@user.route('/follow/tag/<tag_id>')
@login_required
def follow_tag(tag_id):
    """Follow a tag."""
    entity = Tag.query.get_or_404(tag_id)
    followed = current_user.followed_tags
    return follow_entity(entity, followed)


@user.route('/follow/writer/<writer_id>')
@login_required
def follow_writer(writer_id):
    """Follow a writer."""
    entity = Writer.query.get_or_404(writer_id)
    followed = current_user.followed_writers
    return follow_entity(entity, followed)


@user.route('/follow/text/<text_id>')
@login_required
def follow_text(text_id):
    """Follow a text."""
    entity = Text.query.get_or_404(text_id)
    followed = current_user.followed_texts
    return follow_entity(entity, followed)


@user.route('/follow/edition/<edition_id>')
@login_required
def follow_edition(edition_id):
    """Follow a edition."""
    entity = Edition.query.get_or_404(edition_id)
    followed = current_user.followed_editions
    return follow_entity(entity, followed)


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


@user.route('/follow/request/text/<request_id>')
@login_required
def follow_text_request(request_id):
    """Follow a text request."""
    text_request = TextRequest.query.get_or_404(request_id)
    redirect_url = generate_next(text_request.url)
    if text_request.approved or text_request.rejected:
        flash("You cannot follow a text request that has already been approved "
              "or rejected.")
        return redirect(redirect_url)
    else:
        return follow_entity(text_request, current_user.followed_textrequests)


@user.route('/follow/request/tag/<request_id>')
@login_required
def follow_tag_request(request_id):
    """Follow a tag request."""
    tag_request = TagRequest.query.get_or_404(request_id)
    redirect_url = generate_next(tag_request.url)
    if tag_request.approved or tag_request.rejected:
        flash("You cannot follow a tag request that has already been approved "
              "or rejected.")
        return redirect(redirect_url)
    else:
        return follow_entity(tag_request, current_user.followed_tagrequests)


@user.route('/follow/annotation/<annotation_id>')
@login_required
def follow_annotation(annotation_id):
    """Follow an annotation."""
    annotation = Annotation.query.get_or_404(annotation_id)
    redirect_url = generate_next(annotation.url)
    if not annotation.active:
        flash("You cannot follow deactivated annotations.")
        return redirect(redirect_url)
    elif annotation.annotator == current_user:
        flash("You cannot follow your own annotation.")
        return redirect(redirect_url)
    else:
        return follow_entity(annotation, current_user.followed_annotations)
