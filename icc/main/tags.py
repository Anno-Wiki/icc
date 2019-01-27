from flask import render_template, url_for, request, abort, current_app
from flask_login import current_user
from sqlalchemy import and_

from icc import db
from icc.main import main

from icc.models.annotation import (Annotation,  Edit, Tag, AnnotationFlagEnum)
from icc.models.tables import tags as tags_table


@main.route('/tag/list')
def tag_index():
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'tag', type=str)

    if sort == 'tag':
        tags = Tag.query.order_by(Tag.tag)\
                .paginate(page, current_app.config['CARDS_PER_PAGE'], False)
    elif sort == 'annotations':
        # This doesn't do anything but the same sort yet
        tags = Tag.query\
            .outerjoin(tags_table)\
            .outerjoin(Edit, and_(Edit.id == tags_table.c.edit_id,
                                  Edit.current == True))\
            .group_by(Tag.id)\
            .order_by(db.func.count(Edit.id).desc())\
            .paginate(page, current_app.config['CARDS_PER_PAGE'], False)
    else:
        tags = Tag.query.order_by(Tag.tag)\
                .paginate(page, current_app.config['CARDS_PER_PAGE'], False)

    if not tags.items and page > 1:
        abort(404)

    sorts = {
        'tag': url_for('main.tag_index', sort='tag', page=page),
        'annotations': url_for('main.tag_index', sort='annotations', page=page)
    }

    next_page = url_for('main.tag_index', page=tags.next_num, sort=sort)\
        if tags.has_next else None
    prev_page = url_for('main.tag_index', page=tags.prev_num, sort=sort)\
        if tags.has_prev else None

    return render_template('indexes/tags.html', title="Tags",
                           next_page=next_page, prev_page=prev_page,
                           sorts=sorts, sort=sort, tags=tags.items)


@main.route('/tag/<tag>')
def tag(tag):
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'modified', type=str)

    tag = Tag.query.filter_by(tag=tag).first_or_404()

    if sort == 'newest':
        annotations = tag.annotations\
            .order_by(Annotation.timestamp.desc())\
            .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    elif sort == 'weight':
        annotations = tag.annotations\
            .order_by(Annotation.weight.desc())\
            .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    elif sort == 'oldest':
        annotations = tag.annotations\
            .order_by(Annotation.timestamp.asc())\
            .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    elif sort == 'modified':
        annotations = tag.annotations\
            .order_by(Edit.timestamp.desc())\
            .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    else:
        annotations = tag.annotations\
            .order_by(Annotation.timestamp.desc())\
            .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)

    if not annotations.items and page > 1:
        abort(404)

    sorts = {
        'newest': url_for('main.tag', tag=tag.tag, page=page, sort='newest'),
        'oldest': url_for('main.tag', tag=tag.tag, page=page, sort='oldest'),
        'weight': url_for('main.tag', tag=tag.tag, page=page, sort='weight'),
        'modified': url_for('main.tag', tag=tag.tag, page=page,
                            sort='modified'),
    }

    next_page = url_for(
        'main.tag', tag=tag.tag, page=annotations.next_num, sort=sort)\
        if annotations.has_next else None
    prev_page = url_for(
        'main.tag', tag=tag.tag, page=annotations.prev_num, sort=sort)\
        if annotations.has_prev else None

    annotationflags = AnnotationFlagEnum.query.all()
    uservotes = current_user.get_vote_dict() if current_user.is_authenticated\
        else None

    return render_template(
        'view/tag.html', title=tag.tag, next_page=next_page,
        prev_page=prev_page, sorts=sorts, sort=sort, tag=tag,
        annotations=annotations.items, annotationflags=annotationflags,
        uservotes=uservotes)
