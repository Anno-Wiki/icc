from flask import (render_template, flash, redirect, url_for, request,
                   current_app)
from flask_login import current_user, login_required

from icc import db
from icc.funky import generate_next
from icc.requests import requests
from icc.requests.forms import TagRequestForm

from icc.models.request import TagRequest, TagRequestVote


@requests.route('/tag/list')
def tag_request_index():
    default = 'weight'
    sort = request.args.get('sort', default, type=str)
    page = request.args.get('page', 1, type=int)

    sorts = {
        'tag': TagRequest.query.order_by(TagRequest.tag.asc()),
        'weight': TagRequest.query.order_by(TagRequest.weight.desc()),
        'oldest': TagRequest.query.order_by(TagRequest.timestamp.asc()),
        'newest': TagRequest.query.order_by(TagRequest.timestamp.desc()),
    }

    sort = sort if sort in sorts else default
    requests = sorts[sort].filter(TagRequest.approved==False,
                                  TagRequest.rejected==False)\
        .paginate(page, current_app.config['CARDS_PER_PAGE'], False)
    if not requests.items and page > 1:
        abort(404)

    sorturls = {key: url_for('requests.tag_request_index', page=page, sort=key) for
                key in sorts.keys()}
    next_page = (url_for('requests.tag_request_index',
                         page=tag_requests.next_num, sort=sort) if
                 requests.has_next else None)
    prev_page = (url_for('requests.tag_request_index',
                         page=tag_requests.prev_num, sort=sort) if
                 requests.has_prev else None)
    return render_template('indexes/tag_requests.html', title="Tag Requests",
                           next_page=next_page, prev_page=prev_page,
                           sort=sort, sorts=sorturls,
                           tag_requests=requests.items)


@requests.route('/tag/<request_id>')
def view_tag_request(request_id):
    tag_request = TagRequest.query.get_or_404(request_id)
    return render_template('view/tag_request.html', tag_request=tag_request)


@requests.route('/tag/create', methods=['GET', 'POST'])
@login_required
def request_tag():
    current_user.authorize('request_tags')
    form = TagRequestForm()
    if form.validate_on_submit():
        tag_request = TagRequest(tag=form.tag.data,
                                 description=form.description.data, weight=0,
                                 requester=current_user)
        db.session.add(tag_request)
        tag_request.upvote(current_user)
        current_user.followed_tagrequests.append(tag_request)
        db.session.commit()
        flash("Tag request created.")
        flash(f"You have upvoted the request for {tag_request.tag}")
        flash(f"You are now follow the request for {tag_request.tag}")
        return redirect(url_for('requests.tag_request_index'))
    return render_template('forms/tag_request.html', title="Request Tag",
                           form=form)


@requests.route('/tag/<request_id>/upvote')
@login_required
def upvote_tag_request(request_id):
    tag_request = TagRequest.query.get_or_404(request_id)
    redirect_url = generate_next(url_for('requests.tag_request_index'))
    vote = current_user.get_vote(tag_request)
    if vote:
        rd = vote.is_up
        tag_request.rollback(vote)
        db.session.commit()
        if rd:
            return redirect(redirect_url)
    tag_request.upvote(current_user)
    db.session.commit()
    return redirect(redirect_url)


@requests.route('/tag/<request_id>/downvote')
@login_required
def downvote_tag_request(request_id):
    tag_request = TagRequest.query.get_or_404(request_id)
    redirect_url = generate_next(url_for('requests.tag_request_index'))
    vote = current_user.get_vote(tag_request)
    if vote:
        rd = not vote.is_up
        tag_request.rollback(vote)
        db.session.commit()
        if rd:
            return redirect(redirect_url)
    tag_request.downvote(current_user)
    db.session.commit()
    return redirect(redirect_url)
