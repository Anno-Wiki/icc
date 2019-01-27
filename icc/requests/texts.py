from flask import (render_template, flash, redirect, url_for, request,
                   current_app)
from flask_login import current_user, login_required

from icc import db
from icc.funky import generate_next
from icc.requests import requests
from icc.requests.forms import TextRequestForm

from icc.models.request import TextRequest, TextRequestVote


@requests.route('text/list')
def text_request_index():
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'weight', type=str)
    if sort == 'oldest':
        text_requests = TextRequest.query\
            .order_by(TextRequest.requested.asc())\
            .paginate(page, current_app.config['CARDS_PER_PAGE'], False)
    elif sort == 'newest':
        text_requests = TextRequest.query\
            .order_by(TextRequest.requested.desc())\
            .paginate(page, current_app.config['CARDS_PER_PAGE'], False)
    elif sort == 'weight':
        text_requests = TextRequest.query\
            .order_by(TextRequest.weight.desc())\
            .paginate(page, current_app.config['CARDS_PER_PAGE'], False)
    elif sort == 'title':
        text_requests = TextRequest.query\
            .order_by(TextRequest.title.asc())\
            .paginate(page, current_app.config['CARDS_PER_PAGE'], False)
    elif sort == 'author':
        text_requests = TextRequest.query\
            .order_by(TextRequest.author.asc())\
            .paginate(page, current_app.config['CARDS_PER_PAGE'], False)
    else:
        text_requests = TextRequest.query\
            .order_by(TextRequest.weight.desc())\
            .paginate(page, current_app.config['CARDS_PER_PAGE'], False)

    sorts = {
        'oldest': url_for('requests.text_request_index', sort='oldest',
                          page=page),
        'newest': url_for('requests.text_request_index', sort='newest',
                          page=page),
        'weight': url_for('requests.text_request_index', sort='weight',
                          page=page),
        'title': url_for('requests.text_request_index', sort='title',
                         page=page),
        'author': url_for('requests.text_request_index', sort='author',
                          page=page)
    }

    next_page = url_for(
        'requests.text_request_index', page=text_requests.next_num, sort=sort)\
        if text_requests.has_next else None
    prev_page = url_for(
        'requests.text_request_index', page=text_requests.prev_num, sort=sort)\
        if text_requests.has_prev else None
    uservotes = current_user.get_text_request_vote_dict()\
        if current_user.is_authenticated else None
    return render_template(
        'indexes/text_requests.html', title="Book Requests",
        next_page=next_page, prev_page=prev_page,
        text_requests=text_requests.items, uservotes=uservotes, sort=sort,
        sorts=sorts)


@requests.route('/text/<text_request_id>')
def view_text_request(text_request_id):
    text_request = TextRequest.query.get_or_404(text_request_id)
    return render_template('view/text_request.html', text_request=text_request)


@requests.route('/text/create', methods=['GET', 'POST'])
@login_required
def text_request():
    current_user.authorize('request_texts')
    form = TextRequestForm()
    if form.validate_on_submit():
        text_request = TextRequest(
            title=form.title.data, author=form.author.data,
            notes=form.notes.data, description=form.description.data,
            wikipedia=form.wikipedia.data, gutenberg=form.gutenberg.data,
            requester=current_user, weight=0)
        db.session.add(text_request)
        text_request.upvote(current_user)
        current_user.followed_text_requests.append(text_request)
        db.session.commit()
        flash('Book request created.')
        flash(f'You have upvoted the request for {text_request.title}.')
        flash('You are now following the request for {text_request.title}.')
        return redirect(url_for('text_request_index'))
    return render_template('forms/text_request.html', title="Request Book",
                           form=form)


@requests.route('/text/<text_request_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_text_request(text_request_id):
    text_request = TextRequest.query.get_or_404(text_request_id)
    if current_user != text_request.requester:
        current_user.authorize('edit_text_requests')
    form = TextRequestForm()
    if form.validate_on_submit():
        text_request.title = form.title.data
        text_request.author = form.author.data
        text_request.notes = form.notes.data
        text_request.description = form.description.data
        text_request.wikipedia = form.wikipedia.data
        text_request.gutenberg = form.gutenberg.data
        db.session.commit()
        flash('Book request edit complete.')
        return redirect(url_for('requests.view_text_request',
                                text_request_id=text_request_id))
    else:
        form.title.data = text_request.title
        form.author.data = text_request.author
        form.notes.data = text_request.notes
        form.description.data = text_request.description
        form.wikipedia.data = text_request.wikipedia
        form.gutenberg.data = text_request.gutenberg
    return render_template('forms/text_request.html', title="Edit Book Request",
                           form=form)


@requests.route('/text/<text_request_id>/upvote')
@login_required
def upvote_text_request(text_request_id):
    text_request = TextRequest.query.get_or_404(text_request_id)
    redirect_url = generate_next(url_for('requests.text_request_index'))
    if current_user.already_voted_text_request(text_request):
        vote = current_user.text_request_ballots.filter(
            TextRequestVote.text_request == text_request).first()
        rd = True if vote.is_up() else False
        text_request.rollback(vote)
        db.session.commit()
        if rd:
            return redirect(redirect_url)
    text_request.upvote(current_user)
    db.session.commit()
    return redirect(redirect_url)


@requests.route('/text/<text_request_id>/downvote')
@login_required
def downvote_text_request(text_request_id):
    text_request = TextRequest.query.get_or_404(text_request_id)
    redirect_url = generate_next(url_for('requests.text_request_index'))
    if current_user.already_voted_text_request(text_request):
        vote = current_user.text_request_ballots.filter(
            TextRequestVote.text_request == text_request).first()
        rd = True if not vote.is_up() else False
        text_request.rollback(vote)
        db.session.commit()
        if rd:
            return redirect(redirect_url)
    text_request.downvote(current_user)
    db.session.commit()
    return redirect(redirect_url)
