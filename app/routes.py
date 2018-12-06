import re
import difflib
from collections import defaultdict
from datetime import datetime

from flask import render_template, flash, redirect, url_for, request, abort, g
from flask_login import current_user, login_required
from sqlalchemy import and_

from app import app, db
from app.models import User, Book, Author, Line, LineEnum, Annotation, Edit,\
        Tag, EditVote, Vote, AnnotationFlag, AnnotationFlagEnum,\
        tags as tags_table
from app.forms import AnnotationForm, LineNumberForm, SearchForm
from app.funky import preplines, generate_next, line_check

@app.before_request
def before_request():
    if current_user.is_authenticated and current_user.locked:
        logout_user()
    g.search_form = SearchForm()

@app.route("/search")
def search():
    if not g.search_form.validate():
        return redirect(url_for("index"))
    page = request.args.get("page", 1, type=int)
    lines, line_total = Line.search(g.search_form.q.data, page,
            app.config["LINES_PER_SEARCH_PAGE"])
    annotations, annotation_total = Annotation.search(g.search_form.q.data,
            page, app.config["ANNOTATIONS_PER_SEARCH_PAGE"])
    next_page = url_for("search", q=g.search_form.q.data, page=page + 1)\
        if line_total > page * app.config["LINES_PER_SEARCH_PAGE"]\
        or annotation_total > page * app.config["ANNOTATIONS_PER_SEARCH_PAGE"]\
        else None
    prev_page = url_for("search", q=g.search_form.q.data, page=page - 1) \
        if page > 1 else None
    return render_template("indexes/search.html", title="Search", lines=lines,
            line_total=line_total, annotations=annotations,
            annotation_total=annotation_total, next_page=next_page,
            prev_page=prev_page)

###########
## Index ##
###########

@app.route("/")
@app.route("/index/")
def index():
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "newest", type=str)

    if sort == "newest":
        annotations = Annotation.query.filter_by(active=True)\
                .order_by(Annotation.timestamp.desc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "oldest":
        annotations = Annotation.query.filter_by(active=True)\
                .order_by(Annotation.timestamp.asc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "modified":
        annotations = Annotation.query\
                .outerjoin(Edit, and_(Annotation.id==Edit.annotation_id,
                            Edit.current==True))\
                .group_by(Annotation.id)\
                .order_by(Edit.timestamp.desc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "weight":
        annotations = Annotation.query.filter_by(active=True)\
                .order_by(Annotation.weight.desc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    else:
        annotations = Annotation.query.filter_by(active=True)\
                .order_by(Annotation.timestamp.desc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)

    sorts = {
            "newest": url_for("index", page=page, sort="newest"),
            "oldest": url_for("index", page=page, sort="oldest"),
            "modified": url_for("index", page=page, sort="modified"),
            "weight": url_for("index", page=page, sort="weight"),
            }

    annotationflags = AnnotationFlagEnum.query.all()
    next_page = url_for("index", page=annotations.next_num, sort=sort) \
            if annotations.has_next else None
    prev_page = url_for("index", page=annotations.prev_num, sort=sort) \
            if annotations.has_prev else None
    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None
    return render_template("indexes/annotation_list.html", title="Home",
            annotations=annotations.items, uservotes=uservotes,
            next_page=next_page, prev_page=prev_page,
            annotationflags=annotationflags, sort=sort, sorts=sorts)

#############
## Indexes ##
#############

@app.route("/list/authors/")
def author_index():
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "last name", type=str)
    if sort == "last name":
        authors = Author.query\
                .order_by(Author.last_name.asc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "full name":
        authors = Author.query\
                .order_by(Author.name.asc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "oldest":
        authors = Author.query\
                .order_by(Author.birth_date.asc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "youngest":
        authors = Author.query\
                .order_by(Author.birth_date.desc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "books":
        authors = Author.query\
                .outerjoin(Book).group_by(Author.id)\
                .order_by(db.func.count(Book.id).desc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    else:
        authors = Author.query\
                .order_by(Author.last_name.asc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    sorts = {
            "last name": url_for("author_index", sort="last name", page=page),
            "name": url_for("author_index", sort="name", page=page),
            "oldest": url_for("author_index", sort="oldest", page=page),
            "youngest": url_for("author_index", sort="youngest", page=page),
            "books": url_for("author_index", sort="books", page=page),
            }

    next_page = url_for("author_index", page=authors.next_num, sort=sort) \
            if authors.has_next else None
    prev_page = url_for("author_index", page=authors.prev_num, sort=sort) \
            if authors.has_prev else None

    return render_template("indexes/authors.html", title="Authors",
            authors=authors.items, next_page=next_page, prev_page=prev_page,
            sorts=sorts, sort=sort)

@app.route("/list/books/")
def book_index():
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "title", type=str)
    if sort == "title":
        books = Book.query\
                .order_by(Book.sort_title.asc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "author":
        books = Book.query\
                .join(Author)\
                .order_by(Author.last_name.asc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "oldest":
        books = Book.query\
                .order_by(Book.published.asc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "newest":
        books = Book.query\
                .order_by(Book.published.desc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "length":
        books = Book.query\
                .outerjoin(Line).group_by(Book.id)\
                .order_by(db.func.count(Line.id).desc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "annotations":
        books = Book.query\
                .outerjoin(Annotation).group_by(Book.id)\
                .order_by(db.func.count(Annotation.id).desc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    else:
        books = Book.query.order_by(Book.sort_title.asc()
                ).paginate(page, app.config["CARDS_PER_PAGE"], False)

    sorts = {
            "title": url_for("book_index", sort="title", page=page),
            "author": url_for("book_index", sort="author", page=page),
            "oldest": url_for("book_index", sort="oldest", page=page),
            "newest": url_for("book_index", sort="newest", page=page),
            "length": url_for("book_index", sort="length", page=page),
            "annotations": url_for("book_index", sort="annotations", page=page),
    }

    next_page = url_for("book_index", page=books.next_num, sort=sort) \
            if books.has_next else None
    prev_page = url_for("book_index", page=books.prev_num, sort=sort) \
            if books.has_prev else None

    return render_template("indexes/books.html", title="Books",
            books=books.items, prev_page=prev_page, next_page=next_page,
            sorts=sorts, sort=sort)

@app.route("/list/tags/")
def tag_index():
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "tag", type=str)
    if sort == "tag":
        tags = Tag.query\
                .order_by(Tag.tag)\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    elif sort == "annotations":
        # This doesn't do anything but the same sort yet
        tags = Tag.query\
                .outerjoin(tags_table)\
                .outerjoin(Edit, and_(
                    Edit.id==tags_table.c.edit_id,
                    Edit.current==True))\
                .group_by(Tag.id)\
                .order_by(db.func.count(Edit.id).desc())\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)
    else:
        tags = Tag.query\
                .order_by(Tag.tag)\
                .paginate(page, app.config["CARDS_PER_PAGE"], False)

    sorts = {
            "tag": url_for("tag_index", sort="tag", page=page),
            "annotations": url_for("tag_index", sort="annotations", page=page)
            }

    next_page = url_for("tag_index", page=tags.next_num, sort=sort) \
            if tags.has_next else None
    prev_page = url_for("tag_index", page=tags.prev_num, sort=sort) \
            if tags.has_prev else None
    return render_template("indexes/tags.html", title="Tags",
            tags=tags.items, next_page=next_page, prev_page=prev_page,
            sorts=sorts, sort=sort)

#######################
## Single Item Views ##
#######################

@app.route("/author/<name>/")
def author(name):
    author = Author.query.filter_by(url=name).first_or_404()
    return render_template("view/author.html", title=author.name, author=author)

@app.route("/author/<name>/annotations/")
def author_annotations(name):
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "weight", type=str)
    author = Author.query.filter_by(url=name).first_or_404()
    if sort == "newest":
        annotations = author.annotations\
                .order_by(Annotation.timestamp.desc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "oldest":
        annotations = author.annotations\
                .order_by(Annotation.timestamp.asc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "weight":
        annotations = author.annotations\
                .order_by(Annotation.weight.desc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    # tried to do sort==modified except it's totally buggy and I gotta sort
    # through the problems.
    else:
        annotations = author.annotations\
                .order_by(Annotation.timestamp.desc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
        sort == "newest"

    sorts = {
            "newest": url_for("author_annotations", name=author.url,
                sort="newest", page=page),
            "oldest": url_for("author_annotations", name=author.url,
                sort="oldest", page=page),
            "weight": url_for("author_annotations", name=author.url,
                sort="weight", page=page),
            }

    annotationflags = AnnotationFlagEnum.query.all()
    next_page = url_for("author_annotations", name=author.url, sort=sort,
            page=annotations.next_num) if annotations.has_next else None
    prev_page = url_for("author_annotations", name=author.url, sort=sort,
            page=annotations.prev_num) if annotations.has_prev else None
    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None
    return render_template("indexes/annotation_list.html",
            title=f"{author.name} - Annotations", annotations=annotations.items,
            sorts=sorts, sort=sort, next_page=next_page, prev_page=prev_page,
            annotationflags=annotationflags, uservotes=uservotes)

@app.route("/book/<book_url>/")
def book(book_url):
    book = Book.query.filter_by(url=book_url).first_or_404()

    # get the labels for each heierarchical chapter level
    labels = LineEnum.query.filter(LineEnum.label.startswith("lvl")).all()
    label_ids = [l.id for l in labels]


    # get all the heierarchical chapter lines
    hierarchy = book.lines.filter(Line.label_id.in_(label_ids))\
            .order_by(Line.line_num.asc()).all()

    return render_template("view/book.html", title=book.title, book=book,
            hierarchy=hierarchy)

@app.route("/book/<book_url>/annotations/")
def book_annotations(book_url):
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "weight", type=str)
    book = Book.query.filter_by(url=book_url).first_or_404()
    if sort == "newest":
        annotations = book.annotations\
                .order_by(Annotation.timestamp.desc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "oldest":
        annotations = book.annotations\
                .order_by(Annotation.timestamp.asc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "weight":
        annotations = book.annotations\
                .order_by(Annotation.weight.desc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "line":
        annotations = book.annotations\
                .outerjoin(Edit, and_(
                    Edit.annotation_id==Annotation.id,
                    Edit.current==True))\
                .order_by(Edit.last_line_num.asc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    else:
        annotations = book.annotations\
                .order_by(Annotation.timestamp.desc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
        sort = "newest"
        
    annotationflags = AnnotationFlagEnum.query.all()
    sorts = {
            "newest": url_for("book_annotations", book_url=book.url,
                sort="newest", page=page),
            "oldest": url_for("book_annotations", book_url=book.url,
                sort="oldest", page=page),
            "weight": url_for("book_annotations", book_url=book.url,
                sort="weight", page=page),
            "line": url_for("book_annotations", book_url=book.url, sort="line",
                page=page),
            }
    next_page = url_for("book_annotations", book_url=book.url, sort=sort,
            page=annotations.next_num) if annotations.has_next else None
    prev_page = url_for("book_annotations", book_url=book_url, sort=sort,
            page=annotations.prev_num) if annotations.has_prev else None
    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None
    return render_template("indexes/annotation_list.html",
            title=f"{book.title} - Annotations", annotations=annotations.items,
            sorts=sorts, sort=sort, next_page=next_page, prev_page=prev_page,
            annotationflags=annotationflags, uservotes=uservotes)

@app.route("/tag/<tag>/")
def tag(tag):
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "modified", type=str)
    tag = Tag.query.filter_by(tag=tag).first_or_404()
    if sort == "newest":
        annotations = tag.annotations\
                .order_by(Annotation.timestamp.desc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "weight":
        annotations = tag.annotations\
                .order_by(Annotation.weight.desc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "oldest":
        annotations = tag.annotations\
                .order_by(Annotation.timestamp.asc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "modified":
        annotations = tag.annotations\
                .order_by(Edit.timestamp.desc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    else:
        annotations = tag.annotations\
                .order_by(Annotation.timestamp.desc())\
                .paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    sorts = {
            "newest": url_for("tag", tag=tag.tag, page=page, sort="newest"),
            "oldest": url_for("tag", tag=tag.tag, page=page, sort="oldest"),
            "weight": url_for("tag", tag=tag.tag, page=page, sort="weight"),
            "modified": url_for("tag", tag=tag.tag, page=page, sort="modified"),
            }
    annotationflags = AnnotationFlagEnum.query.all()

    next_page = url_for("tag", tag=tag.tag, page=annotations.next_num,
            sort=sort) if annotations.has_next else None
    prev_page = url_for("tag", tag=tag.tag, page=annotations.prev_num,
            sort=sort) if annotations.has_prev else None

    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None

    return render_template("view/tag.html", title=tag.tag, tag=tag,
            annotations=annotations.items,
            next_page=next_page, prev_page=prev_page,
            annotationflags=annotationflags, sorts=sorts, sort=sort,
            uservotes=uservotes)

@app.route("/annotation/<annotation_id>/")
def annotation(annotation_id):
    annotation = Annotation.query.get_or_404(annotation_id)
    if not annotation.active:
        current_user.authorize("view_deactivated_annotations")

    annotationflags = AnnotationFlagEnum.query.all()
    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None
    return render_template("view/annotation.html",
            title=f"Annotation [{annotation.id}]", annotation=annotation,
            uservotes=uservotes, annotationflags=annotationflags)

@app.route("/annotation/<annotation_id>/edit/history/")
def edit_history(annotation_id):
    annotation = Annotation.query.get_or_404(annotation_id)
    annotationflags = AnnotationFlagEnum.query.all()

    if not annotation.active:
        current_user.authorize("view_deactivated_annotations")

    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "edit_num_invert", type=str)

    if sort == "edit_num":
        edits = annotation.history\
                .filter(Edit.approved==True)\
                .order_by(Edit.edit_num.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "edit_num_invert":
        edits = annotation.history\
                .filter(Edit.approved==True)\
                .order_by(Edit.edit_num.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "editor":
        edits = annotation.history.outerjoin(User)\
                .filter(Edit.approved==True)\
                .order_by(User.displayname.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "editor_invert":
        edits = annotation.history.outerjoin(User)\
                .filter(Edit.approved==True)\
                .order_by(User.displayname.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time":
        edits = annotation.history\
                .filter(Edit.approved==True)\
                .order_by(Edit.timestamp.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time_invert":
        edits = annotation.history\
                .filter(Edit.approved==True)\
                .order_by(Edit.timestamp.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "reason":
        edits = annotation.history\
                .filter(Edit.approved==True)\
                .order_by(Edit.edit_reason.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "reason_invert":
        edits = annotation.history\
                .filter(Edit.approved==True)\
                .order_by(Edit.edit_reason.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    else:
        edits = annotation.history\
                .outerjoin(EditVote,
                        and_(EditVote.user_id==current_user.id,
                            EditVote.edit_id==Edit.id)
                        )\
                .filter(Edit.approved==True)\
                .order_by(EditVote.delta.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
        sort = "voted"


    next_page = url_for("edit_review_queue", page=edits.next_num, sort=sort)\
            if edits.has_next else None
    prev_page = url_for("edit_review_queue", page=edits.prev_num, sort=sort)\
            if edits.has_prev else None

    return render_template("indexes/edit_history.html", title="Edit History",
            edits=edits.items, sort=sort, next_page=next_page,
            prev_page=prev_page, annotation=annotation, page=page)

@app.route("/annotation/<annotation_id>/edit/<edit_num>/")
def view_edit(annotation_id, edit_num):
    edit = Edit.query.filter(
            Edit.annotation_id==annotation_id,
            Edit.edit_num==edit_num,
            Edit.approved==True
            ).first_or_404()

    if not edit.previous:
        return render_template("view/first_version.html",
                title=f"First Version of [{edit.annotation.id}]", edit=edit)
    # we have to replace single returns with spaces because markdown only
    # recognizes paragraph separation based on two returns. We also have to be
    # careful to do this for both unix and windows return variants (i.e. be
    # careful of \r's).
    diff1 = re.sub(r"(?<!\n)\r?\n(?![\r\n])", " ", edit.previous.body)
    diff2 = re.sub(r"(?<!\n)\r?\n(?![\r\n])", " ", edit.body)

    diff = list(difflib.Differ().compare(diff1.splitlines(),
        diff2.splitlines()))
    tags = [tag for tag in edit.tags]
    for tag in edit.previous.tags:
        if tag not in tags:
            tags.append(tag)
    if edit.first_line_num > edit.previous.first_line_num:
        context = [line for line in edit.previous.context]
        for line in edit.context:
            if line not in context:
                context.append(line)
    else:
        context = [line for line in edit.context]
        for line in edit.previous.context:
            if line not in context:
                context.append(line)

    return render_template("view/edit.html", title=f"Edit number {edit.edit_num}",
            diff=diff, edit=edit, tags=tags, context=context)

####################
## Reading Routes ##
####################

@app.route("/read/<book_url>/", methods=["GET", "POST"])
def read(book_url):
    book = Book.query.filter_by(url=book_url).first_or_404()
    tag = request.args.get("tag", None, type=str)
    lvl = [request.args.get("l1", 0, type=int)]
    lvl.append(request.args.get("l2", 0, type=int))
    lvl.append(request.args.get("l3", 0, type=int))
    lvl.append(request.args.get("l4", 0, type=int))

    annotationflags = AnnotationFlagEnum.query.all()

    if lvl[3]:
        lines = book.lines.filter(
                Line.lvl4==lvl[3], Line.lvl3==lvl[2],
                Line.lvl2==lvl[1], Line.lvl1==lvl[0]
                ).order_by(Line.line_num.asc()).all()
    elif lvl[2]:
        lines = book.lines.filter(
                Line.lvl3==lvl[2], Line.lvl2==lvl[1], Line.lvl1==lvl[0]
                ).order_by(Line.line_num.asc()).all()
    elif lvl[1]:
        lines = book.lines.filter(
                Line.lvl2==lvl[1], Line.lvl1==lvl[0]
                ).order_by(Line.line_num.asc()).all()
    elif lvl[0]:
        lines = book.lines.filter(
                Line.lvl1==lvl[0]
                ).order_by(Line.line_num.asc()).all()
    else:
        lines = book.lines.order_by(Line.line_num.asc()).all()

    if len(lines) <= 0:
        abort(404)

    form = LineNumberForm()

    next_page = lines[0].get_next_page()
    prev_page = lines[0].get_prev_page()

    if form.validate_on_submit():
        # line number boiler plate
        if not form.first_line.data and not form.last_line.data:
            flash("Please enter a first and last line number to annotate a selection.")
            return redirect(url_for("read", book_url=book.url, tag=tag,
                lvl1=lvl[0], lvl2=lvl[1], lvl3=lvl[2], lvl4=lvl[3]))
        elif not form.first_line.data:
            ll = int(form.last_line.data)
            fl = ll
        elif not form.last_line.data:
            fl = int(form.first_line.data)
            ll = fl
        else:
            fl = int(form.first_line.data)
            ll = int(form.last_line.data)

        if fl < 1:
            fl = 1
        if ll < 1:
            fl = 1
            ll = 1

        # redirect to annotate page, with next query param being the current
        # page. Multi-layered nested return statement. Read carefully.
        return redirect(url_for("annotate", book_url=book_url, first_line=fl,
            last_line=ll, next=request.full_path))

    # get all the annotations
    if tag:
        tag = Tag.query.filter_by(tag=tag).first_or_404()
        annotations = tag.annotations\
                .filter(Annotation.book_id==book.id,
                        Edit.first_line_num>=lines[0].line_num,
                        Edit.last_line_num<=lines[-1].line_num)\
                .all()
        tags = None
    else:
        annotations = book.annotations.join(Edit,
                and_(Edit.annotation_id==Annotation.id,
                    Edit.current==True))\
                .filter(Edit.last_line_num<=lines[-1].line_num,
                        Edit.first_line_num>=lines[0].line_num)\
                .all()
        # this query is like 5 times faster than the old double-for loop. I am,
        # however, wondering if some of the join conditions should be offloaded
        # into a filter
        tags = Tag.query.outerjoin(tags_table)\
                .join(Edit, and_(
                    Edit.id==tags_table.c.edit_id,
                    Edit.current==True,
                    Edit.book_id==book.id,
                    Edit.first_line_num>=lines[0].line_num,
                    Edit.last_line_num<=lines[-1].line_num)
                    )\
                .all()

    # index the annotations in a dictionary
    annotations_idx = defaultdict(list)
    for a in annotations:
        annotations_idx[a.HEAD.last_line_num].append(a)

    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None

    # I have to query this so I only make a db call once instead of each time
    # for every line to find out if the user has edit_rights
    if current_user.is_authenticated:
        can_edit_lines = current_user.is_authorized("edit_lines")
    else:
        can_edit_lines = False

    # This custom method for replacing underscores with <em> tags is still way
    # faster than the markdown converter. Since I'm not using anything other
    # than underscores for italics in the body of the actual text (e.g., I'm
    # using other methods to indicate blockquotes), I'll just keep using this.
    preplines(lines)

    return render_template("read.html", title=book.title, form=form, book=book,
            lines=lines, annotations_idx=annotations_idx, uservotes=uservotes,
            tags=tags, tag=tag, next_page=next_page, prev_page=prev_page,
            can_edit_lines=can_edit_lines, annotationflags=annotationflags)

#######################
## Annotation System ##
#######################

@app.route("/annotate/<book_url>/<first_line>/<last_line>/",
        methods=["GET", "POST"])
@login_required
def annotate(book_url, first_line, last_line):
    if int(first_line) > int(last_line):
        tmp = first_line
        first_line = last_line
        last_line = tmp
    if int(first_line) < 1:
        first_line = 1
    if int(last_line) < 1:
        first_line = 1
        last_line = 1


    book = Book.query.filter_by(url=book_url).first_or_404()
    lines = book.lines.filter(Line.line_num>=first_line,
            Line.line_num<=last_line).all()
    context = book.lines.filter(Line.line_num>=int(first_line)-5,
            Line.line_num<=int(last_line)+5).all()
    form = AnnotationForm()

    if lines == None:
        abort(404)

    redirect_url = generate_next(lines[0].get_url())

    if form.validate_on_submit():
        # line number boiler plate
        fl, ll = line_check(int(form.first_line.data), int(form.last_line.data))

        # Process all the tags
        raw_tags = form.tags.data.split()
        tags = []
        fail = False
        for tag in raw_tags:
            t = Tag.query.filter_by(tag=tag).first()
            if t:
                tags.append(t)
            else:
                flash(f"tag {tag} does not exist.")
                fail = True

        if fail:
            return render_template("forms/annotation.html", title=book.title,
                    form=form, book=book, lines=lines, context=context)
        elif len(tags) > 5:
            flash("There is a five tag limit.")
            return render_template("forms/annotation.html", title=book.title,
                    form=form, book=book, lines=lines, context=context)

        locked = form.locked.data\
                and current_user.is_authorized("lock_annotations")

        # Create the annotation annotation with HEAD pointing to anno
        head = Annotation(book=book, annotator=current_user, locked=locked)

        # I'll use the language of git
        # Create the inital transient sqlalchemy Edit object
        commit = Edit(
                book=book, approved=True, current=True, editor=current_user,
                first_line_num=fl, last_line_num=ll,
                first_char_idx=form.first_char_idx.data,
                last_char_idx=form.last_char_idx.data,
                body=form.annotation.data, tags=tags, annotation=head,
                edit_reason="Initial version"
                )

        # because of the nature of the indexing system we have to create a
        # temporary attribute to the head of the body of the annotation.
        # Otherwise, since neither are committed to the system yet, the system
        # wants to make a query to the system for the head's HEAD attribute,
        # which isn't in existence yet. Adding this simple attribute eliminates
        # the issue.
        head.body = commit.body

        db.session.add(commit)
        db.session.add(head)
        db.session.commit()

        flash("Annotation Submitted")

        return redirect(redirect_url)
    else:
        form.first_line.data = first_line
        form.last_line.data = last_line
        form.first_char_idx.data = 0
        form.last_char_idx.data = -1

    return render_template("forms/annotation.html", title=book.title, form=form,
             book=book, lines=lines, context=context)

@app.route("/edit/<annotation_id>/", methods=["GET", "POST"])
@login_required
def edit(annotation_id):
    annotation = Annotation.query.get_or_404(annotation_id)
    redirect_url = generate_next(url_for("annotation",
        annotation_id=annotation_id))
    if annotation.locked == True\
            and not current_user.is_authorized("edit_locked_annotations"):
        flash("That annotation is locked from editing.")
        return redirect(redirect_url)
    elif not annotation.active:
        current_user.authorize("edit_deactivated_annotations")
    lines = annotation.lines
    context = annotation.context
    form = AnnotationForm()
    if form.validate_on_submit():
        # line number boilerplate
        fl, ll = line_check(int(form.first_line.data), int(form.last_line.data))
        fail = False # if at any point we run into problems, flip this var
        raw_tags = form.tags.data.split()
        tags = []
        for tag in raw_tags:
            t = Tag.query.filter_by(tag=tag).first()
            if t:
                tags.append(t)
            else:
                fail = True
                flash(f"tag {tag} does not exist.")
        if len(tags) > 5:
            fail = True
            flash("There is a five tag limit.")
        lockchange = False
        if current_user.is_authorized("lock_annotations")\
                and annotation.locked != form.locked.data:
            lockchange = True
            annotation.locked = form.locked.data
        # if a reason isn't provided and there's no lockchange, fail the
        # submission
        if not form.reason.data and not lockchange:
            flash("Please provide a reason for your edit.")
            fail = True

        edit_num = int(annotation.HEAD.edit_num+1) if annotation.HEAD.edit_num\
                else 1
        edit = Edit(book=annotation.book,
                editor=current_user, edit_num=edit_num,
                edit_reason=form.reason.data, annotation=annotation,
                first_line_num=fl, last_line_num=ll,
                first_char_idx=form.first_char_idx.data,
                last_char_idx=form.last_char_idx.data,
                body=form.annotation.data, tags=tags,
                weight=0
                )

        if edit.hash_id == annotation.HEAD.hash_id and not lockchange:
            flash("Your suggested edit is no different from the previous version.")
            fail = True
        # approved is true if the user can edit immediately
        approved = current_user.is_authorized("immediate_edits")\
                or annotation.annotator == current_user
        if fail: # rerender the template with the work already filled
            return render_template("forms/annotation.html", form=form,
                    title=annotation.HEAD.book.title, lines=lines, 
                    book=annotation.HEAD.book, annotation=annotation)
        elif edit.hash_id == annotation.HEAD.hash_id and lockchange:
            # Don't add the edit, but flash lock message
            if annotation.locked:
                flash("Annotation Locked")
            else:
                flash("Annotation Unlocked")
        else:
            # The edit is valid
            if lockchange:
                if annotation.locked:
                    flash("Annotation Locked")
                else:
                    flash("Annotation Unlocked")
            if approved:
                edit.approve(current_user)
                flash("Edit completed.")
            else:
                flash("Edit submitted for review.")
            db.session.add(edit)
        db.session.commit()
        return redirect(redirect_url)
    elif not annotation.edit_pending:
        tag_strings = []
        for t in annotation.HEAD.tags:
            tag_strings.append(t.tag)
        form.first_line.data = annotation.HEAD.first_line_num
        form.last_line.data = annotation.HEAD.last_line_num
        form.first_char_idx.data = annotation.HEAD.first_char_idx
        form.last_char_idx.data = annotation.HEAD.last_char_idx
        form.annotation.data = annotation.HEAD.body
        form.tags.data = " ".join(tag_strings)
        form.locked.data = annotation.locked
    return render_template("forms/annotation.html", form=form,
            title=f"Edit Annotation {annotation.id}", book=annotation.HEAD.book,
            lines=lines, annotation=annotation, context=context)

@app.route("/rollback/<annotation_id>/edit/<edit_id>/", methods=["GET", "POST"])
@login_required
def rollback(annotation_id, edit_id):
    annotation = Annotation.query.get_or_404(annotation_id)
    edit = Edit.query.get_or_404(edit_id)

    redirect_url = generate_next(url_for("edit_history",
        annotation_id=annotation.id))

    if annotation.locked == True\
            and not current_user.is_authorized("edit_locked_annotations"):
        flash("That annotation is locked from editing.")
        return redirect(redirect_url)
    elif not annotation.active:
        current_user.authorize("edit_deactivated_annotations")

    if annotation.HEAD == edit:
        flash("You can't roll back an annotation to its current version.")
        return redirect(redirect_url)

    lines = annotation.lines
    context = annotation.context
    form = AnnotationForm()

    if form.validate_on_submit():
        # line number boilerplate
        fl = int(form.first_line.data)
        ll = int(form.last_line.data)
        if fl < 1:
            fl = 1
        if ll < 1:
            fl = 1
            ll = 1
        if ll < fl:
            tmp = ll
            ll = fl
            fl = tmp

        # Process all the tags
        raw_tags = form.tags.data.split()
        tags = []
        fail = False
        for tag in raw_tags:
            t = Tag.query.filter_by(tag=tag).first()
            if t:
                tags.append(t)
            else:
                fail = True
                flash(f"tag {tag} does not exist.")

        if len(tags) > 5:
            fail = True
            flash("There is a five tag limit.")


        # approved is true if the user can edit immediately
        approved = current_user.is_authorized("immediate_edits")\
                or annotation.annotator == current_user

        lockchange = False
        if current_user.is_authorized("lock_annotations"):
            # the lock changes if the annotation's lock value is different from
            # the form's locked data. We have to specify this because this won't
            # show up in edit's hash_id and will fail the uniqueness test.
            lockchange = annotation.locked != form.locked.data
            annotation.locked = form.locked.data

        # if a reason isn't provided and there's no lockchange, fail the
        # submission
        if not form.reason.data and not lockchange:
            flash("Please provide a reason for your edit.")
            fail = True


        edit_num = int(annotation.HEAD.edit_num+1) if annotation.HEAD.edit_num\
                else 1
        # both the approved and current variables are based on approved
        edit = Edit(book=annotation.book,
                editor_id=current_user.id, edit_num=edit_num,
                edit_reason=form.reason.data, annotation_id=annotation_id,
                approved=approved, current=approved,
                first_line_num=fl, last_line_num=ll,
                first_char_idx=form.first_char_idx.data,
                last_char_idx=form.last_char_idx.data,
                body=form.annotation.data, tags=tags,
                )

        if edit.hash_id == annotation.HEAD.hash_id and not lockchange:
            flash("Your suggested edit is no different from the previous version.")
            fail = True

        lockchangenotedit = False

        if fail:
            return render_template("forms/annotation.html",
                    title=annotation.HEAD.book.title, form=form,
                    book=annotation.HEAD.book, lines=lines,
                    annotation=annotation)
        elif edit.hash_id == annotation.HEAD.hash_id and lockchange:
            flash("Annotation Locked")
            lockchangenotedit = True
        else:
            annotation.edit_pending = not approved
            if approved:
                annotation.HEAD.current = False
                edit.current = True
                flash("Edit complete.")
            else:
                flash("Edit submitted for review.")
            db.session.add(edit)

        db.session.commit()
        if approved and not lockchangenotedit:
            pass
        if lockchange:
            pass
        db.session.commit()

        return redirect(redirect_url)

    elif not annotation.edit_pending:
        tag_strings = []
        for t in edit.tags:
            tag_strings.append(t.tag)
        form.first_line.data = edit.first_line_num
        form.last_line.data = edit.last_line_num
        form.first_char_idx.data = edit.first_char_idx
        form.last_char_idx.data = edit.last_char_idx
        form.annotation.data = edit.body
        form.tags.data = " ".join(tag_strings)
        form.locked.data = annotation.locked
        form.reason.data = f"Rollback to edit #{edit.edit_num}"

    return render_template("forms/annotation.html",
            title=f"Edit Annotation {annotation.id}", form=form,
            book=annotation.HEAD.book, lines=lines,
            annotation=annotation, context=context)

@app.route("/upvote/<annotation_id>/")
@login_required
def upvote(annotation_id):
    annotation = Annotation.query.get_or_404(annotation_id)
    redirect_url = generate_next(url_for("annotation",
        annotation_id=annotation_id))
    if not annotation.active:
        flash("You cannot vote on deactivated annotations.")
        return redirect(redirect_url)
    if current_user == annotation.annotator:
        flash("You cannot vote on your own annotations.")
        return redirect(redirect_url)
    elif current_user.already_voted(annotation):
        vote = current_user.ballots.filter(Vote.annotation==annotation).first()
        diff = datetime.utcnow() - vote.timestamp
        if diff.days > 0 and annotation.HEAD.modified < vote.timestamp:
            flash("Your vote is locked until the annotation is modified.")
            return redirect(redirect_url)
        elif vote.is_up():
            annotation.rollback(vote)
            db.session.commit()
            return redirect(redirect_url)
        else:
            annotation.rollback(vote)
    annotation.upvote(current_user)
    db.session.commit()
    return redirect(redirect_url)

@app.route("/downvote/<annotation_id>/")
@login_required
def downvote(annotation_id):
    annotation = Annotation.query.get_or_404(annotation_id)
    redirect_url = generate_next(url_for("annotation",
        annotation_id=annotation_id))
    if not annotation.active:
        flash("You cannot vote on deactivated annotations.")
    if current_user == annotation.annotator:
        flash("You cannot vote on your own annotation.")
        return redirect(redirect_url)
    elif current_user.already_voted(annotation):
        vote = current_user.ballots.filter(Vote.annotation==annotation).first()
        diff = datetime.utcnow() - vote.timestamp
        if diff.days > 0 and annotation.HEAD.modified < vote.timestamp:
            flash("Your vote is locked until the annotation is modified.")
            return redirect(redirect_url)
        elif not vote.is_up():
            annotation.rollback(vote)
            db.session.commit()
            return redirect(redirect_url)
        else:
            annotation.rollback(vote)

    annotation.downvote(current_user)
    db.session.commit()

    return redirect(redirect_url)

@app.route("/annotation/<annotation_id>/flag/<flag_id>/")
@login_required
def flag_annotation(flag_id, annotation_id):
    annotation = Annotation.query.get_or_404(annotation_id)
    if not annotation.active:
        current_user.authorize("view_deactivated_annotations")
    flag = AnnotationFlagEnum.query.get_or_404(flag_id)

    redirect_url = generate_next(url_for("annotation",
        annotation_id=annotation.id))

    annotation.flag(flag, current_user)
    db.session.commit()
    flash(f"Annotation {annotation.id} flagged \"{flag.flag}\"")
    return redirect(redirect_url)
