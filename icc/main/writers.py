from flask import render_template, url_for, request, abort, current_app
from flask_login import current_user
from sqlalchemy import and_

from icc import db
from icc.main import main

from icc.models.annotation import Annotation, AnnotationFlagEnum
from icc.models.content import (Text, Writer, WriterEditionConnection,
                                ConnectionEnum)
from icc.models.tables import authors as authors_table


@main.route('/writer/list')
def writer_index():
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'last name', type=str)

    if sort == 'last name':
        writers = Writer.query\
            .order_by(Writer.last_name.asc())\
            .paginate(page, current_app.config['CARDS_PER_PAGE'], False)
    elif sort == 'oldest':
        writers = Writer.query\
            .order_by(Writer.birth_date.asc())\
            .paginate(page, current_app.config['CARDS_PER_PAGE'], False)
    elif sort == 'youngest':
        writers = Writer.query\
            .order_by(Writer.birth_date.desc())\
            .paginate(page, current_app.config['CARDS_PER_PAGE'], False)
    elif sort == 'authored':
        writers = Writer.query\
            .outerjoin(authors_table)\
            .outerjoin(Text, Text.id == authors_table.c.text_id)\
            .group_by(Writer.id)\
            .order_by(db.func.count(Text.id).desc())\
            .paginate(page, current_app.config['CARDS_PER_PAGE'], False)
    elif sort == 'edited':
        writers = Writer.query\
            .outerjoin(WriterEditionConnection)\
            .outerjoin(
                ConnectionEnum, and_(ConnectionEnum.id ==
                                     WriterEditionConnection.enum_id,
                                     ConnectionEnum.enum == 'Editor'))\
            .group_by(Writer.id)\
            .order_by(db.func.count(ConnectionEnum.id).desc())\
            .paginate(page, current_app.config['CARDS_PER_PAGE'], False)
    elif sort == 'translated':
        writers = Writer.query\
            .outerjoin(WriterEditionConnection)\
            .outerjoin(
                ConnectionEnum, and_(ConnectionEnum.id ==
                                     WriterEditionConnection.enum_id,
                                     ConnectionEnum.enum == 'Translator'))\
            .group_by(Writer.id)\
            .order_by(db.func.count(ConnectionEnum.id).desc())\
            .paginate(page, current_app.config['CARDS_PER_PAGE'], False)
    else:
        writers = Writer.query\
            .order_by(Writer.last_name.asc())\
            .paginate(page, current_app.config['CARDS_PER_PAGE'], False)

    if not writers.items and page > 1:
        abort(404)

    sorts = {
        'last name': url_for('main.writer_index', sort='last name', page=page),
        'oldest': url_for('main.writer_index', sort='oldest', page=page),
        'youngest': url_for('main.writer_index', sort='youngest', page=page),
        'authored': url_for('main.writer_index', sort='authored', page=page),
        'edited': url_for('main.writer_index', sort='edited', page=page),
        'translated': url_for('main.writer_index', sort='translated',
                              page=page),
    }

    next_page = url_for('main.writer_index', page=writers.next_num, sort=sort) \
        if writers.has_next else None
    prev_page = url_for('main.writer_index', page=writers.prev_num, sort=sort) \
        if writers.has_prev else None

    return render_template('indexes/writers.html', title="Authors",
                           writers=writers.items, next_page=next_page,
                           prev_page=prev_page, sorts=sorts, sort=sort)


@main.route('/writer/<writer_url>')
def writer(writer_url):
    writer = Writer.query\
        .filter_by(name=writer_url.replace('_', ' ')).first_or_404()
    return render_template('view/writer.html', title=writer.name, writer=writer)


@main.route('/writer/<writer_url>/annotations')
def writer_annotations(writer_url):
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'weight', type=str)

    writer = Writer.query\
        .filter_by(name=writer_url.replace('_', ' ')).first_or_404()

    if sort == 'newest':
        annotations = writer.annotations\
            .order_by(Annotation.timestamp.desc())\
            .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    elif sort == 'oldest':
        annotations = writer.annotations\
            .order_by(Annotation.timestamp.asc())\
            .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    elif sort == 'weight':
        annotations = writer.annotations\
            .order_by(Annotation.weight.desc())\
            .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    # tried to do sort==modified except it's totally buggy and I gotta sort
    # through the problems.
    else:
        annotations = writer.annotations\
            .order_by(Annotation.timestamp.desc())\
            .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
        sort == 'newest'

    if not annotations.items and page > 1:
        abort(404)

    sorts = {
        'newest': url_for('main.writer_annotations', writer_url=writer.url,
                          sort='newest', page=page),
        'oldest': url_for('main.writer_annotations', writer_url=writer.url,
                          sort='oldest', page=page),
        'weight': url_for('main.writer_annotations', writer_url=writer.url,
                          sort='weight', page=page),
    }

    annotationflags = AnnotationFlagEnum.query.all()

    next_page = url_for(
        'main.writer_annotations', writer_url=writer.url, sort=sort,
        page=annotations.next_num) if annotations.has_next else None
    prev_page = url_for(
        'main.writer_annotations', writer_url=writer.url, sort=sort,
        page=annotations.prev_num) if annotations.has_prev else None

    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
        else None

    return render_template(
        'indexes/annotation_list.html', title=f"{writer.name} - Annotations",
        next_page=next_page, prev_page=prev_page, sorts=sorts, sort=sort,
        annotations=annotations.items, annotationflags=annotationflags,
        uservotes=uservotes)
