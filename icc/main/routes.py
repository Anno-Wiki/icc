"""This file is the absolute primary collection of routes. That is to say, it
consists of the sine qua non routes for the icc. They include:

- The search route
- The primary index
- The list of annotations by line route
- The read route.

Of course, one could argue that he annotation routes are the sine qua non of the
icc. I would argue that you are an idiot.

"""
from collections import defaultdict

from flask import (render_template, redirect, url_for, request, abort, g,
                   current_app)
from flask_login import current_user, logout_user

from icc.funky import line_check
from icc.main import main

from icc.models.annotation import Annotation, Edit, AnnotationFlagEnum
from icc.models.content import Text, Edition, Line

from icc.forms import LineNumberForm, SearchForm


@main.before_app_request
def before_request():
    """The before request route makes sure that the user's account is not
    locked. If it is, then it logs them out. It then adds the search form and
    the list of annotation flagas to the global variable.
    """
    if current_user.is_authenticated and current_user.locked:
        logout_user()
    g.search_form = SearchForm()
    g.aflags = AnnotationFlagEnum.query.all()


@main.route('/search')
def search():
    """The search method is for lines. It uses elasticsearch to search for a
    given line, which can then be reviewed, and checked for annotations in
    another view.

    A separate search function will be created for the omni-search. Lines are
    the primary way of interacting with the application. Eventually my
    omni-search will be parsed to handle searching annotations, wikis, and tags.
    """
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
    sorts = {
        'newest': (Annotation.query.filter_by(active=True)
                   .order_by(Annotation.timestamp.desc())),
        'oldest': (Annotation.query.filter_by(active=True)
                   .order_by(Annotation.timestamp.asc())),
        'modified': (Annotation.query.join(Edit).order_by(Edit.timestamp.desc())
                     .filter(Annotation.active==True, Edit.current==True)),
        'weight': (Annotation.query.filter_by(active=True)
                   .order_by(Annotation.weight.desc())),
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
    """See all annotations for a given line. That is to say, all the annotations
    which have this particular line within their target body.
    """
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'weight', type=str)

    text = Text.query.filter_by(title=text_url.replace('_', ' ')).first_or_404()
    edition = (text.primary if not edition_num else
               Edition.query.filter(Edition.text==text,
                                    Edition.num==edition_num).first_or_404())
    line = Line.query.filter(Line.edition==edition,
                             Line.num==line_num).first_or_404()

    sorts = {
        'newest': line.annotations.order_by(Annotation.timestamp.desc()),
        'oldest': line.annotations.order_by(Annotation.timestamp.asc()),
        'weight': line.annotations.order_by(Annotation.weight.desc()),
        'modified': (line.annotations.join(Edit).order_by(Edit.timestamp.desc())
                     .filter(Annotation.active==True, Edit.current==True))
    }

    sort = sort if sort in sorts else 'newest'

    sorturls = {key: url_for('main.index', text_url=text_url,
                             edition_num=edition_num, line_num=line_num,
                             sort=key) for key in sorts.keys()}

    annotations = sorts[sort]\
        .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)

    if not annotations.items and page > 1:
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
        append em tags based on line.emphasis values. This is to open and close
        any emphasis tags that correspond to underscores that span multiple
        lines. If we *don't* do this, we get all kinds of broken html. And
        that's never fun.

        This method is ten thousand times faster than an actual markdown
        pre-processor. The only thing that would be faster is if I put the
        actual emphasis tags into the database. I may still eventually do that.
        The issue will be when I begin to use char-by-char annotation. That will
        be a headache. I still don't know what the char-by-char highlighting
        will return in javascript. Will it ignore emphasis tags, or include
        them? This will have to be tested.
        """
        us = False
        underscoredict = {True: '</em>', False: '<em>'}
        emdict = {'oem': lambda line: f'{line}</em>',
                  'cem': lambda line: f'<em>{line}',
                  'em': lambda line: f'<em>{line}</em>',
                  'nem': lambda line: line}
        for i, line in enumerate(lines):
            linetext = line.line
            if '_' in linetext:
                newline = []
                for c in linetext:
                    if c == '_':
                        newline.append(underscoredict[us])
                        us = not us
                    else:
                        newline.append(c)
                linetext = ''.join(newline)
                lines[i].line = emdict[line.emphasis](linetext)

    text = Text.get_by_url(text_url).first_or_404()
    edition = text.primary if not edition_num else \
        text.editions.filter_by(num=edition_num).first_or_404()
    form = LineNumberForm()

    if form.validate_on_submit():
        first_line, last_line = line_check(form.first_line.data,
                                           form.last_line.data)
        return redirect(url_for('main.annotate', text_url=text_url,
                                edition_num=edition.num, first_line=first_line,
                                last_line=last_line, next=request.full_path))

    section_strings = tuple(request.args.getlist('section'))
    # Get the section tuple or else all 1's for the deepest possible precedence.
    section = (tuple(int(i) for i in section_strings) if section_strings else
               tuple(1 for i in range(edition.deepest_precedence())))

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

    annotations = edition.annotations\
        .join(Edit)\
        .filter(Edit.last_line_num<=lines[-1].num,
                Edit.first_line_num>=lines[0].num, Edit.current==True,
                Annotation.active==True).all()

    # index the annotations in a dictionary by the line number.
    annotations_idx = defaultdict(list)
    if annotations:
        for a in annotations:
            annotations_idx[a.HEAD.last_line_num].append(a)

    # This is faster than the markdown plugin
    underscores_to_ems(lines)

    return render_template('read.html', title=text.title, form=form,
                           next_page=next_page, prev_page=prev_page,
                           text=text, edition=edition, lines=lines,
                           section='.'.join(map(str, section)),
                           annotations_idx=annotations_idx)
