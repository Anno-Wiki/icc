from flask import render_template, flash, redirect, url_for
from flask_login import current_user, login_required

from icc import db
from icc.funky import generate_next
from icc.user import user

from icc.models.annotation import Annotation, Tag
from icc.models.content import Text, Writer, Edition
from icc.models.request import TextRequest, TagRequest
from icc.models.user import User


@user.route('/follow/user/<user_id>')
@login_required
def follow_user(user_id):
    user = User.query.get_or_404(user_id)
    redirect_url = generate_next(user.url)
    if user == current_user:
        flash("You can't follow yourself.")
        redirect(redirect_url)
    elif user in current_user.followed_users:
        current_user.followed_users.remove(user)
    else:
        current_user.followed_users.append(user)
    db.session.commit()
    return redirect(redirect_url)


@user.route('/follow/writer/<writer_id>')
@login_required
def follow_writer(writer_id):
    writer = Writer.query.get_or_404(writer_id)
    redirect_url = generate_next(writer.url)
    if writer in current_user.followed_writers:
        current_user.followed_writers.remove(writer)
    else:
        current_user.followed_writers.append(writer)
    db.session.commit()
    return redirect(redirect_url)


@user.route('/follow/text/<text_id>')
@login_required
def follow_text(text_id):
    text = Text.query.get_or_404(text_id)
    redirect_url = generate_next(text.url)
    if text in current_user.followed_texts:
        current_user.followed_texts.remove(text)
    else:
        current_user.followed_texts.append(text)
    db.session.commit()
    return redirect(redirect_url)


@user.route('/follow/edition/<edition_id>')
@login_required
def follow_edition(edition_id):
    edition = Edition.query.get_or_404(edition_id)
    redirect_url = generate_next(edition.url)
    if edition in current_user.followed_editions:
        current_user.followed_editions.remove(edition)
    else:
        current_user.followed_editions.append(edition)
    db.session.commit()
    return redirect(redirect_url)


@user.route('/follow/request/text/<request_id>')
@login_required
def follow_text_request(request_id):
    text_request = TextRequest.query.get_or_404(request_id)
    redirect_url = generate_next(text_request.url)
    if text_request.approved or text_request.rejected:
        flash("You cannot follow a text request that has already been approved "
              "or rejected.")
    if request in current_user.followed_textrequests:
        current_user.followed_textrequests.remove(request)
    else:
        current_user.followed_textrequests.append(request)
    db.session.commit()
    return redirect(redirect_url)


@user.route('/follow/request/tag/<request_id>')
@login_required
def follow_tag_request(request_id):
    tag_request = TagRequest.query.get_or_404(request_id)
    redirect_url = generate_next(tag_request.url)
    if tag_request.approved or tag_request.rejected:
        flash("You cannot follow a tag request that has already been approved "
              "or rejected.")
    if tag_request in current_user.followed_tagrequests:
        current_user.followed_tagrequests.remove(tag_request)
    else:
        current_user.followed_tagrequests.append(tag_request)
    db.session.commit()
    return redirect(redirect_url)


@user.route('/follow/tag/<tag_id>')
@login_required
def follow_tag(tag_id):
    tag = Tag.query.get_or_404(tag_id)
    redirect_url = generate_next(tag.url)
    if tag in current_user.followed_tags:
        current_user.followed_tags.remove(tag)
    else:
        current_user.followed_tags.append(tag)
    db.session.commit()
    return redirect(redirect_url)


@user.route('/follow/annotation/<annotation_id>')
@login_required
def follow_annotation(annotation_id):
    annotation = Annotation.query.get_or_404(annotation_id)
    redirect_url = generate_next(annotation.url)
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
