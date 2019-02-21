"""The main routes for writers."""

from flask import render_template, url_for, request, abort, current_app

from icc import db
from icc.main import main

from icc.models.annotation import Annotation, Edit
from icc.models.content import Text, Edition, Writer, WriterConnection, WRITERS


@main.route('/writer/list')
def writer_index():
    """The writer index.
    """
    default = 'last name'
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', default, type=str)

    sorts = {
        'last name': Writer.query.order_by(Writer.last_name.asc()),
        'age': Writer.query.order_by(Writer.birth_date.asc()),
        'youth': Writer.query.order_by(Writer.birth_date.desc()),
        'annotations': Writer.query\
            .join(WriterConnection)\
            .join(Edition)\
            .join(Annotation)\
            .group_by(Writer.id)\
            .order_by(db.func.count(Annotation.id).desc())
    }
    for i, conn in enumerate(WRITERS):
        # this will create sorts for the different writer connection roles
        sorts[conn] = Writer.query\
            .join(WriterConnection)\
            .filter_by(enum_id=i)\
            .group_by(Writer.id)\
            .order_by(db.func.count(WriterConnection.id).desc())

    sort = sort if sort in sorts else default
    writers = sorts[sort]\
        .paginate(page, current_app.config['CARDS_PER_PAGE'], False)
    if not writers.items and page > 1:
        abort(404)

    sorturls = {key: url_for('main.writer_index', sort=key, page=page) for key
                in sorts.keys()}
    next_page = (url_for('main.writer_index', page=writers.next_num, sort=sort)
                 if writers.has_next else None)
    prev_page = (url_for('main.writer_index', page=writers.prev_num, sort=sort)
                 if writers.has_prev else None)
    return render_template('indexes/writers.html', title="Authors",
                           next_page=next_page, prev_page=prev_page,
                           sorts=sorturls, sort=sort,
                           writers=writers.items)


@main.route('/writer/<writer_url>')
def writer(writer_url):
    """The writer view."""
    writer = Writer.query\
        .filter_by(name=writer_url.replace('_', ' ')).first_or_404()
    return render_template('view/writer.html', title=writer.name, writer=writer)


@main.route('/writer/<writer_url>/annotations')
def writer_annotations(writer_url):
    """See all annotations by writer.

    Notes
    -----
    Instead, I will associate it with the Edition, and make authors on text a
    special case, like an association_proxy.

    One good idea to simplify a lot will be to make a dictionary on edition for
    every type of writer connection.
    """
    default = 'newest'
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', default, type=str)
    writer = Writer.query\
        .filter_by(name=writer_url.replace('_', ' ')).first_or_404()

    sorts = {
        'newest': writer.annotations.order_by(Annotation.timestamp.desc()),
        'oldest': writer.annotations.order_by(Annotation.timestamp.asc()),
        'weight': writer.annotations.order_by(Annotation.weight.desc()),
        'modified': (writer.annotations.join(Edit)
                     .order_by(Edit.timestamp.desc())),
    }

    sort = sort if sort in sorts else default
    annotations = sorts[sort] \
        .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    if not annotations.items and page > 1:
        abort(404)

    sorturls = {key: url_for('main.writer_annotations', writer_url=writer_url,
                             sort=key, page=page) for key in sorts.keys()}
    next_page = (url_for('main.writer_annotations', writer_url=writer_url,
                         sort=sort, page=annotations.next_num) if
                 annotations.has_next else None)
    prev_page = (url_for('main.writer_annotations', writer_url=writer_url,
                         sort=sort, page=annotations.prev_num) if
                 annotations.has_prev else None)
    return render_template('indexes/annotation_list.html',
                           title=f"{writer.name} - Annotations",
                           next_page=next_page, prev_page=prev_page,
                           sorts=sorturls, sort=sort,
                           annotations=annotations.items)
