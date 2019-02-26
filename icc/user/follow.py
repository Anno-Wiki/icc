from flask import render_template, flash, redirect, url_for
from flask_login import current_user, login_required

from icc import db
from icc.funky import generate_next
from icc.user import user

from icc.models.annotation import Annotation, Tag
from icc.models.content import Text, Writer
from icc.models.request import TextRequest, TagRequest
from icc.models.user import User


@user.route('/follow/list/users')
@login_required
def users_followed_idx():
    followings = current_user.followed_users.all()
    for f in followings:
        f.url = url_for('user.profile', user_id=f.id)
        f.name = f.displayname
        f.unfollow_url = url_for('user.follow_user', user_id=f.id)

    return render_template(
        'indexes/followings.html', title="Followed Users",
        followings=followings, type='users', column1='Display Name')


@user.route('/follow/list/authors')
@login_required
def authors_followed_idx():
    followings = current_user.followed_authors.all()
    for f in followings:
        f.url = url_for('author', name=f.url)
        f.unfollow_url = url_for('user.follow_author', author_id=f.id)
    return render_template(
        'indexes/followings.html', title="Followed Authors",
        followings=followings, type='authors', column1='Name')


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


@user.route('/follow/writer/<writer_id>')
@login_required
def follow_writer(writer_id):
    writer = Writer.query.get_or_404(writer_id)
    redirect_url = generate_next(url_for('main.writer', writer_url=writer.url))
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
    redirect_url = generate_next(url_for('main.text', text_url=text.url))
    if text in current_user.followed_texts:
        current_user.followed_texts.remove(text)
    else:
        current_user.followed_texts.append(text)
    db.session.commit()
    return redirect(redirect_url)


@user.route('/follow/request/book/<book_request_id>')
@login_required
def follow_book_request(book_request_id):
    book_request = TextRequest.query.get_or_404(book_request_id)
    redirect_url = generate_next(url_for('requests.view_book_request',
                                         book_request_id=book_request.id))
    if book_request.approved:
        flash("You cannot follow a book request that has already been "
              "approved.")
    if book_request in current_user.followed_book_requests:
        current_user.followed_book_requests.remove(book_request)
    else:
        current_user.followed_book_requests.append(book_request)
    db.session.commit()
    return redirect(redirect_url)


@user.route('/follow/request/tag/<tag_request_id>')
@login_required
def follow_tag_request(tag_request_id):
    tag_request = TagRequest.query.get_or_404(tag_request_id)
    redirect_url = generate_next(url_for('requests.view_tag_request',
                                         tag_request_id=tag_request.id))
    if tag_request in current_user.followed_tag_requests:
        current_user.followed_tag_requests.remove(tag_request)
    else:
        current_user.followed_tag_requests.append(tag_request)
    db.session.commit()
    return redirect(redirect_url)


@user.route('/follow/tag/<tag_id>')
@login_required
def follow_tag(tag_id):
    tag = Tag.query.get_or_404(tag_id)
    redirect_url = generate_next(url_for('main.tag', tag=tag.tag))
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

    redirect_url = generate_next(url_for('main.annotation',
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
