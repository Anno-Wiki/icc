from flask import render_template, url_for, request, abort, current_app
from flask_login import current_user
from sqlalchemy import and_

from icc import db
from icc.main import main

from icc.models.annotation import Annotation,  Edit, AnnotationFlagEnum
from icc.models.content import Text, Edition, Writer, Line
from icc.models.tables import authors as authors_table


@main.route('/text/list')
def text_index():
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'title', type=str)

    if sort == 'title':
        texts = Text.query\
            .order_by(Text.sort_title.asc())\
            .paginate(page, current_app.config['CARDS_PER_PAGE'], False)
    elif sort == 'author':
        texts = Text.query\
            .join(authors_table)\
            .join(Writer)\
            .order_by(Writer.last_name.asc())\
            .paginate(page, current_app.config['CARDS_PER_PAGE'], False)
    elif sort == 'oldest':
        texts = Text.query\
            .order_by(Text.published.asc())\
            .paginate(page, current_app.config['CARDS_PER_PAGE'], False)
    elif sort == 'newest':
        texts = Text.query\
            .order_by(Text.published.desc())\
            .paginate(page, current_app.config['CARDS_PER_PAGE'], False)
    elif sort == 'length':
        texts = Text.query\
            .join(Edition, and_(Edition.text_id == Text.id,
                                Edition.primary == True))\
            .outerjoin(Line).group_by(Text.id)\
            .order_by(db.func.count(Line.id).desc())\
            .paginate(page, current_app.config['CARDS_PER_PAGE'], False)
    elif sort == 'annotations':
        texts = Text.query\
            .outerjoin(Edition, and_(Edition.text_id == Text.id,
                                     Edition.primary == True))\
            .outerjoin(Annotation).group_by(Text.id)\
            .order_by(db.func.count(Annotation.id).desc())\
            .paginate(page, current_app.config['CARDS_PER_PAGE'], False)
    else:
        texts = Text.query\
            .order_by(Text.sort_title.asc())\
            .paginate(page, current_app.config['CARDS_PER_PAGE'], False)

    if not texts.items and page > 1:
        abort(404)

    sorts = {
        'title': url_for('main.text_index', sort='title', page=page),
        'author': url_for('main.text_index', sort='author', page=page),
        'oldest': url_for('main.text_index', sort='oldest', page=page),
        'newest': url_for('main.text_index', sort='newest', page=page),
        'length': url_for('main.text_index', sort='length', page=page),
        'annotations': url_for('main.text_index', sort='annotations',
                               page=page),
    }

    next_page = url_for('main.text_index', page=texts.next_num, sort=sort) \
        if texts.has_next else None
    prev_page = url_for('main.text_index', page=texts.prev_num, sort=sort) \
        if texts.has_prev else None

    return render_template('indexes/texts.html', title="Texts",
                           prev_page=prev_page, next_page=next_page,
                           sorts=sorts, sort=sort, texts=texts.items)


@main.route('/text/<text_url>')
def text(text_url):
    text = Text.query.filter_by(title=text_url.replace('_', ' ')).first_or_404()
    return render_template('view/text.html', title=text.title, text=text)


@main.route('/text/<text_url>/annotations')
def text_annotations(text_url):
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'weight', type=str)

    text = Text.query.filter_by(title=text_url.replace('_', ' ')).first_or_404()

    if sort == 'newest':
        annotations = text.annotations\
            .order_by(Annotation.timestamp.desc())\
            .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    elif sort == 'oldest':
        annotations = text.annotations\
            .order_by(Annotation.timestamp.asc())\
            .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    elif sort == 'weight':
        annotations = text.annotations\
            .order_by(Annotation.weight.desc())\
            .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    elif sort == 'line':
        annotations = text.annotations\
            .join(Edit, Annotation.id == Edit.entity_id)\
            .filter(Edit.current == True)\
            .order_by(Edit.last_line_num.asc())\
            .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    else:
        annotations = text.annotations\
            .order_by(Annotation.timestamp.desc())\
            .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
        sort = 'newest'

    if not annotations.items and page > 1:
        abort(404)

    annotationflags = AnnotationFlagEnum.query.all()
    sorts = {
        'newest': url_for('main.text_annotations', text_url=text.url,
                          sort='newest', page=page),
        'oldest': url_for('main.text_annotations', text_url=text.url,
                          sort='oldest', page=page),
        'weight': url_for('main.text_annotations', text_url=text.url,
                          sort='weight', page=page),
        'line': url_for('main.text_annotations', text_url=text.url, sort='line',
                        page=page),
    }
    next_page = url_for(
        'main.text_annotations', text_url=text.url, sort=sort,
        page=annotations.next_num) if annotations.has_next else None
    prev_page = url_for(
        'main.text_annotations', text_url=text_url, sort=sort,
        page=annotations.prev_num) if annotations.has_prev else None
    return render_template(
        'indexes/annotation_list.html', title=f"{text.title} - Annotations",
        next_page=next_page, prev_page=prev_page, sorts=sorts, sort=sort,
        annotations=annotations.items, annotationflags=annotationflags)
