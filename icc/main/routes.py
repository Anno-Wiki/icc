from collections import defaultdict

from flask import (render_template, redirect, url_for, request, abort, g,
                   current_app)
from flask_login import current_user, logout_user
from sqlalchemy import and_

from icc.main import main

from icc.models.annotation import Annotation, Edit, Tag, AnnotationFlagEnum
from icc.models.content import Text, Edition, Line
from icc.models.tables import tags as tags_table

from icc.forms import LineNumberForm, SearchForm


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
    lines, line_total = Line.search(g.search_form.q.data, page,
                                    current_app.config['LINES_PER_SEARCH_PAGE'])
    next_page = (url_for('main.search', q=g.search_form.q.data, page=page + 1)
                 if line_total > page *
                 current_app.config['LINES_PER_SEARCH_PAGE'] else None)
    prev_page = url_for('main.search', q=g.search_form.q.data, page=page - 1)\
        if page > 1 else None
    return render_template('indexes/search.html', title="Search",
                           next_page=next_page, prev_page=prev_page,
                           lines=lines, line_total=line_total)


@main.route('/')
@main.route('/index')
def index():
    """The main index page for the web site. It defaults to displaying the
    newest annotations because I want the newest ones reviewed.
    """
    default = 'newest'
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', default, type=str)

    # one letter representations of the classes to reduce code length.
    a = Annotation
    e = Edit
    sorts = {
        'newest': a.query.filter_by(active=True).order_by(a.timestamp.desc()),
        'oldest': a.query.filter_by(active=True).order_by(a.timestamp.asc()),
        'modified': (a.query.join(e).order_by(e.timestamp.desc())
                     .filter(a.active==True, e.current==True)),
        'weight': a.query.filter_by(active=True).order_by(a.weight.desc()),
    }

    # default to newest in case there's some funky sort that ends up in this
    # variable.
    sort = sort if sort in sorts else default

    annotations = sorts[sort]\
        .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)

    if not annotations.items and page > 1:
        abort(404)

    sorturls = {key: url_for('main.index', page=page, sort=key) for key in
                sorts.keys()}

    next_page = (url_for('main.index', page=annotations.next_num, sort=sort) if
                 annotations.has_next else None)
    prev_page = (url_for('main.index', page=annotations.prev_num, sort=sort) if
                 annotations.has_prev else None)

    return render_template('indexes/annotation_list.html', title="Home",
                           active_page='index',
                           sort=sort, sorts=sorturls,
                           next_page=next_page, prev_page=prev_page,
                           annotations=annotations.items)


@main.route('/text/<text_url>/edition/<edition_num>/'
            'line/<line_num>/annotations')
@main.route('/text/<text_url>/line/<line_num>/annotations',
            methods=['GET', 'POST'], defaults={'edition_num': None})
def line_annotations(text_url, edition_num, line_num):
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'weight', type=str)

    text = Text.query.filter_by(title=text_url.replace('_', ' ')).first_or_404()
    edition = (text.primary if not edition_num else
               Edition.query.filter(Edition.text==text,
                                    Edition.num==edition_num).first_or_404())
    line = Line.query.filter(Line.edition==edition,
                             Line.num==line_num).first_or_404()

    a = Annotation
    e = Edit
    sorts = {
        'newest': line.annotations.order_by(a.timestamp.desc()),
        'oldest': line.annotations.order_by(a.timestamp.asc()),
        'weight': line.annotations.order_by(a.weight.desc()),
        'modified': (line.annotations.join(e).order_by(e.timestamp.desc())
                     .filter(a.active==True, e.current==True))
    }

    sort = sort if sort in sorts else 'newest'

    sorturls = {key: url_for('main.index', text_url=text_url,
                             edition_num=edition_num, line_num=line_num,
                             sort=key) for key in sorts.keys()}

    annotations = sorts[sort]\
        .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)

    if not annotations and page > 1:
        abort(404)

    next_page = (
        url_for('main.edition_annotations', text_url=text.url,
                edition_num=edition.num, line_num=line.num, sort=sort,
                page=annotations.next_num) if annotations.has_next else None)
    prev_page = (
        url_for('main.edition_annotations', text_url=text_url,
                edition_num=edition.num, line_num=line.num, sort=sort,
                page=annotations.prev_num) if annotations.has_prev else None)

    return render_template('indexes/annotation_list.html',
                           title=f"{text.title} - Annotations",
                           next_page=next_page, prev_page=prev_page,
                           sorts=sorturls, sort=sort,
                           annotations=annotations.items)


@main.route('/read/<text_url>/edition/<edition_num>', methods=['GET', 'POST'])
@main.route('/read/<text_url>', methods=['GET', 'POST'],
            defaults={'edition_num': None})
def read(text_url, edition_num):
    """The main read route for viewing the text of any edition."""
    def underscores_to_ems(lines):
        """Convert all of the underscores to em tags and prepend and
        append em tags based on line.emphasis values.
        """
        us = False
        for i, line in enumerate(lines):
            if '_' in lines[i].line:
                newline = []
                for c in lines[i].line:
                    if c == '_':
                        if us:
                            newline.append('</em>')
                            us = False
                        else:
                            newline.append('<em>')
                            us = True
                    else:
                        newline.append(c)
                lines[i].line = ''.join(newline)

            if line.emphasis == 'oem':
                lines[i].line = lines[i].line + '</em>'
            elif line.emphasis == 'cem':
                lines[i].line = '<em>' + lines[i].line
            elif line.emphasis == 'em':
                lines[i].line = '<em>' + lines[i].line + '</em>'

    text = Text.get_by_url(text_url).first_or_404()
    edition = text.primary if not edition_num else \
        text.editions.filter_by(num=edition_num).first_or_404()
    form = LineNumberForm()

    if form.validate_on_submit():
        first_line, last_line = line_number_boiler_plate(form.first_line.data,
                                                         form.last_line.data)
        return redirect(url_for('main.annotate', text_url=text_url,
                                edition_num=edition.num, first_line=first_line,
                                last_line=last_line, next=request.full_path))

    section_strings = tuple(request.args.getlist('section'))
    # Get the section tuple or else all 1's for the deepest possible precedence.
    section = tuple(int(i) for i in section_strings) if section_strings\
        else tuple(1 for i in range(edition.deepest_precedence()))

    lines = edition.section(section).all()
    if not lines:
        abort(404)

    next_section = edition.next_section(section)
    next_page = url_for(
        'main.read', text_url=text_url, edition_num=edition.num,
        section=next_section.section()) if next_section else None

    prev_section = edition.prev_section(section)
    prev_page = url_for(
        'main.read', text_url=text_url, edition_num=edition.num,
        section=prev_section.section()) if prev_section else None

    tag = request.args.get('tag', None, type=str)
    if tag:
        tag = Tag.query.filter_by(tag=tag).first_or_404()
        annotations = tag.annotations.filter(
            Annotation.edition_id==text.id,
            Edit.first_line_num>=lines[0].num,
            Edit.last_line_num<=lines[-1].num).all()
        tags = None
    else:
        annotations = edition.annotations\
            .join(Edit, and_(Edit.entity_id==Annotation.id,
                             Edit.current==True))\
            .filter(Edit.last_line_num<=lines[-1].num,
                    Edit.first_line_num>=lines[0].num).all()
        # this query is like 5 times faster than the old double-for loop. I am,
        # however, wondering if some of the join conditions should be offloaded
        # into a filter
        tags = Tag.query\
            .outerjoin(tags_table)\
            .join(Edit, and_(Edit.id==tags_table.c.edit_id, Edit.current==True,
                             Edit.first_line_num>=lines[0].num,
                             Edit.last_line_num<=lines[-1].num))\
            .join(Annotation)\
            .filter(Annotation.edition_id==edition.id).all()

    # index the annotations in a dictionary
    annotations_idx = defaultdict(list)
    if annotations:
        for a in annotations:
            annotations_idx[a.HEAD.last_line_num].append(a)

    # I have to query this so I only make a db call once instead of each time
    # for every line to find out if the user has edit_rights
    can_edit_lines = current_user.is_authorized('edit_lines')\
        if current_user.is_authenticated else False

    # This is faster than the markdown plugin
    underscores_to_ems(lines)

    return render_template('read.html', title=text.title, form=form,
                           next_page=next_page, prev_page=prev_page,
                           text=text, edition=edition,
                           section='.'.join(map(str, section)), lines=lines,
                           annotations_idx=annotations_idx,
                           tags=tags, tag=tag,
                           can_edit_lines=can_edit_lines)
