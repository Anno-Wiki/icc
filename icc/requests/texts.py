"""All the logic for a text request."""
from flask import (render_template, flash, redirect, url_for, request,
                   current_app, abort)
from flask_login import current_user, login_required

from icc import db
from icc.funky import generate_next
from icc.requests import requests
from icc.requests.forms import TextRequestForm

from icc.models.request import TextRequest


@requests.route('text/list')
def text_request_index():
    """An index of active text requests."""
    default = 'weight'
    sort = request.args.get('sort', default, type=str)
    page = request.args.get('page', 1, type=int)

    sorts = {
        'oldest': TextRequest.query.order_by(TextRequest.timestamp.asc()),
        'newest': TextRequest.query.order_by(TextRequest.timestamp.desc()),
        'weight': TextRequest.query.order_by(TextRequest.weight.desc()),
        'title': TextRequest.query.order_by(TextRequest.title.asc()),
        'authors': TextRequest.query.order_by(TextRequest.authors.asc()),
    }

    sort = sort if sort in sorts else default
    requests = sorts[sort].filter(TextRequest.approved==False,
                                  TextRequest.rejected==False)\
        .paginate(page, current_app.config['CARDS_PER_PAGE'], False)
    if not requests.items and page > 1:
        abort(404)

    sorturls = {key: url_for('requests.text_request_index', sort=key) for key in
                sorts.keys()}
    next_page = (url_for('requests.text_request_index', page=requests.next_num,
                         sort=sort) if requests.has_next else None)
    prev_page = (url_for('requests.text_request_index', page=requests.prev_num,
                         sort=sort) if requests.has_prev else None)
    return render_template('indexes/text_requests.html',
                           title="Text Requests",
                           next_page=next_page, prev_page=prev_page,
                           sort=sort, sorts=sorturls,
                           requests=requests.items)


@requests.route('/text/<request_id>')
def view_text_request(request_id):
    """View a text request."""
    req = TextRequest.query.get_or_404(request_id)
    return render_template('view/text_request.html',
                           title=f"Request for {req.title}",
                           req=req)


@requests.route('/text/create', methods=['GET', 'POST'])
@login_required
def request_text():
    current_user.authorize('request_texts')
    form = TextRequestForm()
    if form.validate_on_submit():
        text_request = TextRequest(title=form.title.data,
                                   authors=form.authors.data,
                                   description=form.description.data,
                                   requester=current_user, weight=0)
        db.session.add(text_request)
        current_user.followed_textrequests.append(text_request)
        db.session.commit()
        flash("Text request created.")
        flash(f"You are now following the request for {text_request.title}.")
        return redirect(url_for('requests.text_request_index'))
    return render_template('forms/text_request.html', title="Request Text",
                           form=form)
