"""The main routes for writers."""

from flask import render_template, url_for, request, abort, current_app

from icc import db
from icc.forms import SearchForm
from icc.main import main

from icc.models.annotation import Annotation, Edit, Comment
from icc.models.content import Edition, Writer, WriterConnection, WRITERS


@main.route('/writer/list')
def writer_index():
    """The writer index.
    """
    default = 'last name'
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', default, type=str)

    sorts = {
        'last name': Writer.query.order_by(Writer.family_name.asc()),
        'age': Writer.query.order_by(Writer.birth_date.asc()),
        'youth': Writer.query.order_by(Writer.birth_date.desc()),
        'annotations': (Writer.query
                        .join(WriterConnection).join(Edition).join(Annotation)
                        .group_by(Writer.id)
                        .order_by(db.func.count(Annotation.id).desc()))
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

    sorturls = {key: url_for('main.writer_index', sort=key) for key in
                sorts.keys()}
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
    form = SearchForm()
    writer = Writer.query\
        .filter_by(name=writer_url.replace('_', ' ')).first_or_404()
    return render_template('view/writer.html', title=writer.name, writer=writer,
                           form=form)


@main.route('/writer/<writer_url>/annotations')
def writer_annotations(writer_url):
    """See all annotations by writer."""
    default = 'newest'
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', default, type=str)
    writer = Writer.query\
        .filter_by(name=writer_url.replace('_', ' ')).first_or_404()

    sorts = {
        'newest': writer.annotations.order_by(Annotation.id.desc()),
        'oldest': writer.annotations.order_by(Annotation.id.asc()),
        'weight': writer.annotations.order_by(Annotation.weight.desc()),
        'modified': (writer.annotations
                     .join(Edit, Edit.entity_id==Annotation.id)
                     .order_by(Edit.timestamp.desc())),
        'active': (writer.annotations.join(Comment).group_by(Annotation.id)
                   .order_by(Comment.timestamp.desc()))
    }

    sort = sort if sort in sorts else default
    annotations = sorts[sort].filter(Annotation.active==True)\
        .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    if not annotations.items and page > 1:
        abort(404)

    sorturls = {key: url_for('main.writer_annotations', writer_url=writer_url,
                             sort=key) for key in sorts.keys()}
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
