import re
import difflib

from collections import defaultdict
from datetime import datetime

from flask import render_template, flash, redirect, url_for, request, abort,\
    g, current_app
from flask_login import current_user, login_required, logout_user
from sqlalchemy import and_

from icc import db
from icc.main import main

from icc.models.annotation import (Annotation, Comment, Vote, Edit, EditVote,
                                   Tag, AnnotationFlagEnum)
from icc.models.content import (Text, Edition, Writer, WriterEditionConnection,
                               ConnectionEnum, Line, LineEnum)
from icc.models.tables import tags as tags_table, authors as authors_table
from icc.models.wiki import Wiki, WikiEdit
from icc.models.user import User

from icc.forms import (AnnotationForm, LineNumberForm, SearchForm, CommentForm,
                       WikiForm)
from icc.funky import preplines, generate_next, line_check


@main.before_request
def before_request():
    if current_user.is_authenticated and current_user.locked:
        logout_user()
    g.search_form = SearchForm()


@main.route('/search')
def search():
    if not g.search_form.validate():
        return redirect(url_for('main.index'))
    page = request.args.get('page', 1, type=int)
    lines, line_total = Line.search(
        g.search_form.q.data, page,
        current_app.config['LINES_PER_SEARCH_PAGE'])
    next_page = (
        url_for('main.search', q=g.search_form.q.data, page=page + 1) if
        line_total > page * current_app.config['LINES_PER_SEARCH_PAGE'] else
        None
    )
    prev_page = url_for('main.search', q=g.search_form.q.data, page=page - 1)\
        if page > 1 else None
    return render_template('indexes/search.html', title="Search",
                           next_page=next_page, prev_page=prev_page,
                           lines=lines, line_total=line_total)


@main.route('/')
@main.route('/index')
def index():
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'newest', type=str)

    if sort == 'newest':
        annotations = Annotation.query.filter_by(active=True)\
            .order_by(Annotation.timestamp.desc())\
            .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    elif sort == 'oldest':
        annotations = Annotation.query.filter_by(active=True)\
            .order_by(Annotation.timestamp.asc())\
            .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    elif sort == 'modified':
        annotations = Annotation.query.outerjoin(
            Edit, and_(Annotation.id==Edit.entity_id, Edit.current==True)
        ).group_by(
            Annotation.id
        ).order_by(
            Edit.timestamp.desc()
        ).paginate(
            page, current_app.config['ANNOTATIONS_PER_PAGE'], False
        )
    elif sort == 'weight':
        annotations = Annotation.query.filter_by(active=True)\
            .order_by(Annotation.weight.desc())\
            .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    else:
        annotations = Annotation.query.filter_by(active=True)\
            .order_by(Annotation.timestamp.desc())\
            .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)

    if not annotations.items and page > 1:
        abort(404)

    sorts = {
        'newest': url_for('main.index', page=page, sort='newest'),
        'oldest': url_for('main.index', page=page, sort='oldest'),
        'modified': url_for('main.index', page=page, sort='modified'),
        'weight': url_for('main.index', page=page, sort='weight'),
    }

    annotationflags = AnnotationFlagEnum.query.all()

    next_page = url_for('main.index', page=annotations.next_num, sort=sort) \
        if annotations.has_next else None
    prev_page = url_for('main.index', page=annotations.prev_num, sort=sort) \
        if annotations.has_prev else None

    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
        else None

    return render_template(
        'indexes/annotation_list.html', title="Home", sort=sort, sorts=sorts,
        uservotes=uservotes, next_page=next_page, prev_page=prev_page,
        annotations=annotations.items, annotationflags=annotationflags,
        active_page='index')


@main.route(
    '/text/<text_url>/edition/<edition_num>/line/<line_num>/annotations')
@main.route('/text/<text_url>/line/<line_num>/annotations',
            methods=['GET', 'POST'], defaults={'edition_num': None})
def line_annotations(text_url, edition_num, line_num):
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'weight', type=str)

    text = Text.query.filter_by(title=text_url.replace('_', ' ')).first_or_404()
    edition = text.primary if not edition_num\
            else Edition.query.filter(Edition.text==text,
                    Edition.num==edition_num).first_or_404()
    line = Line.query.filter(Line.edition==edition,
            Line.num==line_num).first_or_404()

    if sort == 'newest':
        annotations = line.annotations.order_by(Annotation.timestamp.desc())\
                .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    elif sort == 'oldest':
        annotations = line.annotations.order_by(Annotation.timestamp.asc())\
                .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    elif sort == 'weight':
        annotations = line.annotations.order_by(Annotation.weight.desc())\
                .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    else:
        annotations = line.annotations.order_by(Annotation.timestamp.desc())\
                .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
        sort = 'newest'

    if not annotations and page > 1:
        abort(404)

    sorts = {
            'newest': url_for('main.line_annotations', text_url=text.url,
                edition_num=edition.num, line_num=line.num, sort='newest',
                page=page),
            'oldest': url_for('main.line_annotations', text_url=text.url,
                edition_num=edition.num, line_num=line.num, sort='oldest',
                page=page),
            'weight': url_for('main.line_annotations', text_url=text.url,
                edition_num=edition.num, line_num=line.num, sort='weight',
                page=page),
            }

    next_page = url_for('main.edition_annotations', text_url=text.url,
            edition_num=edition.num, line_num=line.num, sort=sort,
            page=annotations.next_num) if annotations.has_next else None
    prev_page = url_for('main.edition_annotations', text_url=text_url,
            edition_num=edition.num, line_num=line.num, sort=sort,
            page=annotations.prev_num) if annotations.has_prev else None

    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None
    annotationflags = AnnotationFlagEnum.query.all()

    return render_template('indexes/annotation_list.html',
            title=f"{text.title} - Annotations",
            next_page=next_page, prev_page=prev_page, sorts=sorts, sort=sort,
            annotations=annotations.items, annotationflags=annotationflags,
            uservotes=uservotes)


@main.route('/read/<text_url>/edition/<edition_num>', methods=['GET', 'POST'])
@main.route('/read/<text_url>', methods=['GET', 'POST'],
            defaults={'edition_num': None})
def read(text_url, edition_num):
    if edition_num:
        text = Text.query.filter_by(title=text_url.replace('_', ' '))\
            .first_or_404()
        edition = Edition.query.filter(Edition.text_id==text.id,
                                       Edition.num==edition_num).first_or_404()
    else:
        text = Text.query.filter_by(title=text_url.replace('_', ' '))\
            .first_or_404()
        edition = text.primary
    tag = request.args.get('tag', None, type=str)
    lvl = [request.args.get('l1', 0, type=int)]
    lvl.append(request.args.get('l2', 0, type=int))
    lvl.append(request.args.get('l3', 0, type=int))
    lvl.append(request.args.get('l4', 0, type=int))

    annotationflags = AnnotationFlagEnum.query.all()

    if lvl[3]:
        lines = edition.lines.filter(
            Line.lvl4==lvl[3], Line.lvl3==lvl[2], Line.lvl2==lvl[1],
            Line.lvl1==lvl[0]).order_by(Line.num.asc()).all()
    elif lvl[2]:
        lines = edition.lines.filter(
            Line.lvl3==lvl[2], Line.lvl2==lvl[1],
            Line.lvl1==lvl[0]).order_by(Line.num.asc()).all()
    elif lvl[1]:
        lines = edition.lines.filter(
            Line.lvl2==lvl[1], Line.lvl1==lvl[0]).order_by(Line.num.asc()).all()
    elif lvl[0]:
        lines = edition.lines.filter(
            Line.lvl1==lvl[0]).order_by(Line.num.asc()).all()
    else:
        lines = edition.lines.order_by(Line.num.asc()).all()

    if len(lines) <= 0:
        abort(404)

    form = LineNumberForm()

    next_page = lines[0].get_next_page()
    prev_page = lines[0].get_prev_page()

    if form.validate_on_submit():
        # line number boiler plate
        if not form.first_line.data and not form.last_line.data:
            flash("Please enter a first and last line number to annotate a"
                  " selection.")
            return redirect(request.full_path)
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
        return redirect(url_for('main.annotate', text_url=text_url,
                                edition_num=edition.num, first_line=fl,
                                last_line=ll, next=request.full_path)
                        )

    # get all the annotations
    if tag:
        tag = Tag.query.filter_by(tag=tag).first_or_404()
        annotations = tag.annotations.filter(
            Annotation.edition_id==text.id, Edit.first_line_num>=lines[0].num,
            Edit.last_line_num<=lines[-1].num).all()
        tags = None
    else:
        annotations = edition.annotations.join(
            Edit, and_(
                Edit.entity_id==Annotation.id, Edit.current==True)
        ).filter(
            Edit.last_line_num<=lines[-1].num,
            Edit.first_line_num>=lines[0].num
        ).all()
        # this query is like 5 times faster than the old double-for loop. I am,
        # however, wondering if some of the join conditions should be offloaded
        # into a filter
        tags = Tag.query.outerjoin(tags_table).join(
            Edit, and_(Edit.id==tags_table.c.edit_id, Edit.current==True,
                       Edit.first_line_num>=lines[0].num,
                       Edit.last_line_num<=lines[-1].num)
        ).join(Annotation).filter(Annotation.edition_id==edition.id).all()

    # index the annotations in a dictionary
    annotations_idx = defaultdict(list)
    for a in annotations:
        annotations_idx[a.HEAD.last_line_num].append(a)

    uservotes = current_user.get_vote_dict() if current_user.is_authenticated\
        else None

    # I have to query this so I only make a db call once instead of each time
    # for every line to find out if the user has edit_rights
    if current_user.is_authenticated:
        can_edit_lines = current_user.is_authorized('edit_lines')
    else:
        can_edit_lines = False

    # This custom method for replacing underscores with <em> tags is still way
    # faster than the markdown converter. Since I'm not using anything other
    # than underscores for italics in the body of the actual text (e.g., I'm
    # using other methods to indicate blockquotes), I'll just keep using this.
    preplines(lines)

    return render_template(
        'read.html', title=text.title, form=form, text=text, edition=edition,
        lines=lines, annotations_idx=annotations_idx, uservotes=uservotes,
        tags=tags, tag=tag, next_page=next_page, prev_page=prev_page,
        can_edit_lines=can_edit_lines, annotationflags=annotationflags
    )
