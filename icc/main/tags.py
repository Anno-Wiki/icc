"""The main routes for examining tags."""
from flask import render_template, url_for, request, abort, current_app

from icc import db
from icc.main import main

from icc.models.annotation import Annotation,  Edit, Tag, Comment
from icc.models.tables import tags as tags_table


@main.route('/tag/list')
def tag_index():
    """The main index for all tags."""
    # The annotations and activity sorts only display tags with at least one
    # annotation. This doesn't seem like a serious problem to me.
    default = 'tag'
    sort = request.args.get('sort', default, type=str)
    page = request.args.get('page', 1, type=int)

    sorts = {
        'tag': Tag.query.order_by(Tag.tag),
        'annotations': (Tag.query.join(tags_table).join(Edit)
                        .filter(Edit.current==True).group_by(Tag.id)
                        .order_by(db.func.count(Edit.id).desc())),
        'activity': (Tag.query.join(tags_table).join(Edit)
                     .filter(Edit.current==True).group_by(Tag.id)
                     .order_by(Edit.timestamp)),
    }

    sort = sort if sort in sorts else default
    tags = sorts[sort]\
        .paginate(page, current_app.config['CARDS_PER_PAGE'], False)
    if not tags.items and page > 1:
        abort(404)

    sorturls = {key: url_for('main.tag_index', sort=key) for key in
                sorts.keys()}
    next_page = (url_for('main.tag_index', page=tags.next_num, sort=sort) if
                 tags.has_next else None)
    prev_page = (url_for('main.tag_index', page=tags.prev_num, sort=sort) if
                 tags.has_prev else None)
    return render_template('indexes/tags.html', title="Tags",
                           next_page=next_page, prev_page=prev_page,
                           sorts=sorturls, sort=sort,
                           tags=tags.items)


@main.route('/tag/<tag>')
def tag(tag):
    """The main view page for tags."""
    tag = Tag.query.filter_by(tag=tag).first_or_404()
    return render_template('view/tag.html', title=tag.tag, tag=tag)


@main.route('/tag/<tag>/annotations')
def tag_annotations(tag):
    """See all annotations for a given tag."""
    default = 'newest'
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', default, type=str)
    tag = Tag.query.filter_by(tag=tag).first_or_404()

    sorts = {
        'newest': tag.annotations.order_by(Annotation.id.desc()),
        'oldest': tag.annotations.order_by(Annotation.id.asc()),
        'weight': tag.annotations.order_by(Annotation.weight.desc()),
        'modified': (tag.annotations.order_by(Edit.timestamp.desc())
                     .filter(Edit.current==True)),
        'active': (tag.annotations.join(Comment).group_by(Annotation.id)
                   .order_by(Comment.timestamp.desc()))
    }

    sort = sort if sort in sorts else default
    annotations = sorts[sort].filter(Annotation.active==True)\
        .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    if not annotations.items and page > 1:
        abort(404)

    sorturls = {key: url_for('main.tag_annotations', tag=tag.tag, sort=key) for
                key in sorts.keys()}
    next_page = (url_for('main.tag_annotations', tag=tag.tag, sort=sort,
                         page=annotations.next_num) if annotations.has_next else
                 None)
    prev_page = (url_for('main.tag_annotations', tag=tag.tag, sort=sort,
                         page=annotations.prev_num) if annotations.has_prev else
                 None)
    return render_template('indexes/annotation_list.html',
                           title=f"{tag.tag} - Annotations",
                           next_page=next_page, prev_page=prev_page,
                           sorts=sorturls, sort=sort,
                           annotations=annotations.items)
