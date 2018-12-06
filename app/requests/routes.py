from flask import render_template, flash, redirect, url_for, request
from flask_login import current_user, login_required

from app import app, db
from app.models import BookRequest, BookRequestVote, TagRequest, TagRequestVote

from app.requests import requests
from app.requests.forms import BookRequestForm, TagRequestForm

#################
## List Routes ##
#################

@requests.route("book/list")
def book_request_index():
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "weight", type=str)
    if sort == "oldest":
        book_requests = BookRequest.query\
                .order_by(BookRequest.requested.asc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "newest":
        book_requests = BookRequest.query\
                .order_by(BookRequest.requested.desc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "weight":
        book_requests = BookRequest.query\
                .order_by(BookRequest.weight.desc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "title":
        requests = BookRequest.query\
                .order_by(BookRequest.title.asc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "author":
        book_requests = BookRequest.query\
                .order_by(BookRequest.author.asc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    else:
        book_requests = BookRequest.query\
                .order_by(BookRequest.weight.desc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)

    sorts = {
            "oldest": url_for("requests.book_request_index", sort="oldest", page=page),
            "newest": url_for("requests.book_request_index", sort="newest", page=page),
            "weight": url_for("requests.book_request_index", sort="weight", page=page),
            "title": url_for("requests.book_request_index", sort="title", page=page),
            "author": url_for("requests.book_request_index", sort="author", page=page)
            }

    next_page = url_for("requests.book_request_index", page=book_requests.next_num,
            sort=sort) if book_requests.has_next else None
    prev_page = url_for("requests.book_request_index", page=book_requests.prev_num,
            sort=sort) if book_requests.has_prev else None
    uservotes = current_user.get_book_request_vote_dict() \
            if current_user.is_authenticated else None
    return render_template("indexes/book_requests.html", title="Book Requests",
            next_page=next_page, prev_page=prev_page,
            book_requests=book_requests.items,
            uservotes=uservotes, sort=sort, sorts=sorts)

@requests.route("/book/<book_request_id>")
def view_book_request(book_request_id):
    book_request = BookRequest.query.get_or_404(book_request_id)
    return render_template("view/book_request.html", book_request=book_request)

@requests.route("/book/create", methods=["GET", "POST"])
@login_required
def book_request():
    current_user.authorize("request_books")
    form = BookRequestForm()
    if form.validate_on_submit():
        book_request = BookRequest(title=form.title.data,
                author=form.author.data, notes=form.notes.data,
                description=form.description.data,
                wikipedia=form.wikipedia.data, gutenberg=form.gutenberg.data,
                requester=current_user,
                weight=0)
        db.session.add(book_request)
        book_request.upvote(current_user)
        current_user.followed_book_requests.append(book_request)
        db.session.commit()
        flash("Book request created.")
        flash(f"You have upvoted the request for {book_request.title}.")
        flash("You are now following the request for {book_request.title}.")
        return redirect(url_for("book_request_index"))
    return render_template("forms/book_request.html", title="Request Book",
            form=form)

@requests.route("/book/<book_request_id>/edit", methods=["GET", "POST"])
@login_required
def edit_book_request(book_request_id):
    book_request = BookRequest.query.get_or_404(book_request_id)
    if current_user != book_request.requester:
        current_user.authorize("edit_book_requests")
    form = BookRequestForm()
    if form.validate_on_submit():
        book_request.title = form.title.data
        book_request.author = form.author.data
        book_request.notes = form.notes.data
        book_request.description = form.description.data
        book_request.wikipedia = form.wikipedia.data
        book_request.gutenberg = form.gutenberg.data
        db.session.commit()
        flash("Book request edit complete.")
        return redirect(url_for("requests.view_book_request",
            book_request_id=book_request_id))
    else:
        form.title.data = book_request.title
        form.author.data = book_request.author
        form.notes.data = book_request.notes
        form.description.data = book_request.description
        form.wikipedia.data = book_request.wikipedia
        form.gutenberg.data = book_request.gutenberg
    return render_template("forms/book_request.html", title="Edit Book Request",
            form=form)

@requests.route("/book/<book_request_id>/upvote")
@login_required
def upvote_book_request(book_request_id):
    book_request = BookRequest.query.get_or_404(book_request_id)
    redirect_url = generate_next(url_for("requests.book_request_index"))
    if current_user.already_voted_book_request(book_request):
        vote = current_user.book_request_ballots.filter(
                BookRequestVote.book_request==book_request).first()
        rd = True if vote.is_up() else False
        book_request.rollback(vote)
        db.session.commit()
        if rd:
            return redirect(redirect_url)
    book_request.upvote(current_user)
    db.session.commit()
    return redirect(redirect_url)

@requests.route("/book/<book_request_id>/downvote")
@login_required
def downvote_book_request(book_request_id):
    book_request = BookRequest.query.get_or_404(book_request_id)
    redirect_url = generate_next(url_for("requests.book_request_index"))
    if current_user.already_voted_book_request(book_request):
        vote = current_user.book_request_ballots.filter(
                BookRequestVote.book_request==book_request).first()
        rd = True if not vote.is_up() else False
        book_request.rollback(vote)
        db.session.commit()
        if rd:
            return redirect(redirect_url)
    book_request.downvote(current_user)
    db.session.commit()
    return redirect(redirect_url)

##################
## Tag Requests ##
##################

@requests.route("/tag/list")
def tag_request_index():
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "weight", type=str)
    if sort == "tag":
        tag_requests = TagRequest.query\
                .order_by(TagRequest.tag.asc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "weight":
        tag_requests = TagRequest.query\
                .order_by(TagRequest.weight.desc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "oldest":
        tag_requests = TagRequest.query\
                .order_by(TagRequest.requested.asc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "newest":
        tag_requests = TagRequest.query\
                .order_by(TagRequest.requested.desc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    else:
        tag_requests = TagRequest.query\
                .order_by(TagRequest.weight.desc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)

    sorts = {
            "tag": url_for("requests.tag_request_index", sort="tag", page=page),
            "oldest": url_for("requests.tag_request_index", sort="oldest", page=page),
            "newest": url_for("requests.tag_request_index", sort="newest", page=page),
            "weight": url_for("requests.tag_request_index", sort="weight", page=page),
            }

    next_page = url_for("requests.tag_request_index", page=tag_requests.next_num,
            sort=sort) if tag_requests.has_next else None
    prev_page = url_for("requests.tag_request_index", page=tag_requests.prev_num,
            sort=sort) if tag_requests.has_prev else None
    uservotes = current_user.get_tag_request_vote_dict() \
            if current_user.is_authenticated else None
    return render_template("indexes/tag_requests.html", title="Tag Requests",
            next_page=next_page, prev_page=prev_page,
            tag_requests=tag_requests.items, uservotes=uservotes,
            sort=sort, sorts=sorts)

@requests.route("/tag/<tag_request_id>")
def view_tag_request(tag_request_id):
    tag_request = TagRequest.query.get_or_404(tag_request_id)
    return render_template("view/tag_request.html", tag_request=tag_request)

@requests.route("/tag/create", methods=["GET", "POST"])
@login_required
def tag_request():
    current_user.authorize("request_tags")
    form = TagRequestForm()
    if form.validate_on_submit():
        tag_request = TagRequest(tag=form.tag.data,
                notes=form.notes.data, description=form.description.data,
                wikipedia=form.wikipedia.data, weight=0, requester=current_user)
        db.session.add(tag_request)
        tag_request.upvote(current_user)
        current_user.followed_tag_requests.append(tag_request)
        db.session.commit()
        flash("Tag request created.")
        flash("You have upvoted the request for {tag_request.tag}")
        flash("You are now follow the request for {tag_request.tag}")
        return redirect(url_for("requests.tag_request_index"))
    return render_template("forms/tag_request.html", title="Request Tag",
            form=form)

@requests.route("/tag/request/<tag_request_id>/edit", methods=["GET", "POST"])
@login_required
def edit_tag_request(tag_request_id):
    tag_request = TagRequest.query.get_or_404(tag_request_id)
    if tag_request.requester != current_user:
        current_user.authorize("edit_tag_requests")
    form = TagRequestForm()
    if form.validate_on_submit():
        tag_request.tag = form.tag.data
        tag_request.notes = form.notes.data
        tag_request.description = form.description.data
        tag_request.wikipedia = form.wikipedia.data
        db.session.commit()
        flash("Tag request edit complete.")
        return redirect(url_for("requests.view_tag_request",
            tag_request_id=tag_request_id))
    else:
        form.tag.data = tag_request.tag
        form.notes.data = tag_request.notes
        form.description.data = tag_request.description
        form.wikipedia.data = tag_request.wikipedia
    return render_template("forms/tag_request.html", title="Edit Tag Request",
            form=form)

@requests.route("/tag/<tag_request_id>/upvote")
@login_required
def upvote_tag_request(tag_request_id):
    tag_request = TagRequest.query.get_or_404(tag_request_id)

    redirect_url = generate_next(url_for("requests.tag_request_index"))

    if current_user.already_voted_tag_request(tag_request):
        vote = current_user.tag_request_ballots.filter(
                TagRequestVote.tag_request==tag_request).first()
        rd = True if vote.is_up() else False
        tag_request.rollback(vote)
        db.session.commit()
        if rd:
            return redirect(redirect_url)

    tag_request.upvote(current_user)
    db.session.commit()

    return redirect(redirect_url)

@requests.route("/tag/<tag_request_id>/downvote")
@login_required
def downvote_tag_request(tag_request_id):
    tag_request = TagRequest.query.get_or_404(tag_request_id)

    redirect_url = generate_next(url_for("requests.tag_request_index"))

    if current_user.already_voted_tag_request(tag_request):
        vote = current_user.tag_request_ballots.filter(
                TagRequestVote.tag_request==tag_request).first()
        rd = True if not vote.is_up() else False
        tag_request.rollback(vote)
        db.session.commit()
        if rd:
            return redirect(redirect_url)

    tag_request.downvote(current_user)
    db.session.commit()

    return redirect(redirect_url)
