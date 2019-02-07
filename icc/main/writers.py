"""The main routes for writers."""

from flask import render_template, url_for, request, abort, current_app

from icc import db
from icc.main import main

from icc.models.annotation import Annotation, Edit
from icc.models.content import (Text, Writer, WriterEditionConnection,
                                ConnectionEnum)
from icc.models.tables import authors as authors_table


@main.route('/writer/list')
def writer_index():
    """The writer index."""
    default = 'last name'
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', default, type=str)

    sorts = {
        'last name': Writer.query.order_by(Writer.last_name.asc()),
        'age': Writer.query.order_by(Writer.birth_date.asc()),
        'youth': Writer.query.order_by(Writer.birth_date.desc()),
        'authored': (Writer.query.join(authors_table).join(Text)
                     .order_by(db.func.count(Text.id).desc())
                     .group_by(Writer.id)),
        'edited': (Writer.query.join(WriterEditionConnection)
                   .join(ConnectionEnum).filter(ConnectionEnum.enum=='Editor')
                   .order_by(db.func.count(ConnectionEnum.id).desc())
                   .group_by(Writer.id)),
        'translated': (Writer.query.join(WriterEditionConnection)
                       .join(ConnectionEnum)
                       .filter(ConnectionEnum.enum=='Translator')
                       .order_by(db.func.count(ConnectionEnum.id).desc())
                       .group_by(Writer.id)),
    }

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
    Currently the way we calculate the annotations is not ideal. I cannot get
    annotations for editors or translators. I could do it, but not in the same
    attribute.

    I will, in the near future, need to reformulate the way authors are defined.
    Now they will need to be added via WriterEditionConnections, which I will
    rename WriterConnections for obvious simplicity reasons, and will make
    author a subset of those connections. It will simplify a lot.

    But in the process, I will have to modify `insertlines.py`, and modify the
    way the config yaml file is read in.

    It won't be trivial is my point. It is stupid that I didn't do it in the
    first place. The reason I didn't is obvious, because the naive way to do
    this is to associate authorship with the text, because that's what it
    technically is.

    Instead, I will associate it with the Edition, and make authors on text a
    special case, like an association_proxy.

    One good idea to simplify a lot will be to make a dictionary on edition for
    every type of writer connection.

    I'm also curious if I wouldn't be better off making the enum a static list
    instead of a database table, like with everything else I've been moving
    toward.

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
        .paginate(page, current_app.config['CARDS_PER_PAGE'], False)
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
