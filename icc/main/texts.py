"""The main routes for texts."""

from flask import render_template, url_for, request, abort, current_app

from icc import db
from icc.main import main

from icc.models.annotation import Annotation,  Edit
from icc.models.content import Text, Edition, WriterConnection, Line, WRITERS


@main.route('/text/list')
def text_index():
    """The index of texts."""
    default = 'title'
    sort = request.args.get('sort', default, type=str)
    page = request.args.get('page', 1, type=int)

    sorts = {
        'title': Text.query.order_by(Text.sort_title.asc()),
        'age': Text.query.order_by(Text.published.asc()),
        'youth': Text.query.order_by(Text.published.desc()),
        'length': (Text.query.join(Edition)
                   .filter(Edition.primary==True).join(Line)
                   .order_by(db.func.count(Line.id).desc()).group_by(Text.id)),
        'annotations': (Text.query.join(Edition)
                        .filter(Edition.primary==True).join(Annotation)
                        .order_by(db.func.count(Annotation.id).desc())
                        .group_by(Text.id)),
    }

    for i, conn in enumerate(WRITERS):
        # This creates a new sort for each possible writer connection.
        # It does it dynamically so I never have to worry about it again.
        # Which I likely wouldn't anyway because how many ways are there to
        # connect a writer to a text?
        sorts[conn] = Text.query.join(Edition).join(WriterConnection)\
            .group_by(Text.id).filter(WriterConnection.enum_id==i)\
            .order_by(db.func.count(WriterConnection.id).desc())

    sort = sort if sort in sorts else default
    texts = sorts[sort]\
        .paginate(page, current_app.config['CARDS_PER_PAGE'], False)
    if not texts.items and page > 1:
        abort(404)

    sorturls = {key: url_for('main.text_index', sort=key) for key in
                sorts.keys()}
    next_page = (url_for('main.text_index', page=texts.next_num, sort=sort) if
                 texts.has_next else None)
    prev_page = (url_for('main.text_index', page=texts.prev_num, sort=sort) if
                 texts.has_prev else None)
    return render_template('indexes/texts.html', title="Texts",
                           prev_page=prev_page, next_page=next_page,
                           sorts=sorturls, sort=sort,
                           texts=texts.items)


@main.route('/text/<text_url>')
def text(text_url):
    """The main view page for a text."""
    text = Text.query.filter_by(title=text_url.replace('_', ' ')).first_or_404()
    return render_template('view/text.html', title=text.title, text=text)


@main.route('/text/<text_url>/annotations')
def text_annotations(text_url):
    """The annotations for a given text."""
    default = 'newest'
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', default, type=str)
    text = Text.query.filter_by(title=text_url.replace('_', ' ')).first_or_404()

    sorts = {
        'newest': text.annotations.order_by(Annotation.timestamp.desc()),
        'oldest': text.annotations.order_by(Annotation.timestamp.asc()),
        'weight': text.annotations.order_by(Annotation.weight.desc()),
        'line': (text.annotations.join(Edit).filter(Edit.current==True)
                 .order_by(Edit.last_line_num.asc())),
        'modified': (text.annotations.join(Edit).filter(Edit.current==True)
                     .order_by(Edit.timestamp.desc())),
    }

    sort = sort if sort in sorts else default
    annotations = sorts[sort].filter(Annotation.active==True)\
        .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    if not annotations.items and page > 1:
        abort(404)

    sorturls = {key: url_for('main.text_annotations', text_url=text_url,
                             sort=key) for key in sorts.keys()}
    next_page = (url_for('main.text_annotations', text_url=text_url, sort=sort,
                         page=annotations.next_num) if annotations.has_next else
                 None)
    prev_page = (url_for('main.text_annotations', text_url=text_url, sort=sort,
                         page=annotations.prev_num) if annotations.has_prev else
                 None)
    return render_template('indexes/annotation_list.html',
                           title=f"{text.title} - Annotations",
                           next_page=next_page, prev_page=prev_page,
                           sorts=sorturls, sort=sort,
                           annotations=annotations.items)
