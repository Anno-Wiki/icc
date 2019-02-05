from flask import render_template, url_for, request, abort, current_app
from flask_login import current_user

from icc.main import main

from icc.models.annotation import (Annotation, Edit, AnnotationFlagEnum)
from icc.models.content import (Text, Edition, Line, LineEnum)


@main.route('/text/<text_url>/edition/<edition_num>')
def edition(text_url, edition_num):
    text = Text.query.filter_by(title=text_url.replace('_', ' ')).first_or_404()
    edition = Edition.query\
        .filter(Edition.text_id == text.id,
                Edition.num == edition_num).first_or_404()

    # get the labels for each heierarchical chapter level
    enums = LineEnum.query.filter(LineEnum.enum.startswith('lvl')).all()
    enum_ids = [e.id for e in enums]

    # get all the heierarchical chapter lines
    hierarchy = edition.toc()

    return render_template('view/edition.html', title=f"{text.title} "
                           f"#{edition.num}", hierarchy=hierarchy,
                           edition=edition)


@main.route('/text/<text_url>/edition/<edition_num>/annotations')
def edition_annotations(text_url, edition_num):
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'weight', type=str)

    text = Text.query.filter_by(title=text_url.replace('_', ' ')).first_or_404()
    edition = text.editions.filter_by(num=edition_num).first()

    if sort == 'newest':
        annotations = edition.annotations\
            .order_by(Annotation.timestamp.desc())\
            .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    elif sort == 'oldest':
        annotations = edition.annotations\
            .order_by(Annotation.timestamp.asc())\
            .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    elif sort == 'weight':
        annotations = edition.annotations\
            .order_by(Annotation.weight.desc())\
            .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    elif sort == 'line':
        annotations = edition.annotations\
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

    sorts = {
        'newest': url_for('main.edition_annotations', text_url=text.url,
                          edition_num=edition.num, sort='newest', page=page),
        'oldest': url_for('main.edition_annotations', text_url=text.url,
                          edition_num=edition.num, sort='oldest', page=page),
        'weight': url_for('main.edition_annotations', text_url=text.url,
                          edition_num=edition.num, sort='weight', page=page),
        'line': url_for('main.edition_annotations', text_url=text.url,
                        edition_num=edition.num, sort='line', page=page),
    }

    next_page = url_for(
        'main.edition_annotations', text_url=text.url, edition_num=edition.num,
        sort=sort, page=annotations.next_num) if annotations.has_next else None
    prev_page = url_for(
        'main.edition_annotations', text_url=text_url, edition_num=edition.num,
        sort=sort, page=annotations.prev_num) if annotations.has_prev else None

    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
        else None
    annotationflags = AnnotationFlagEnum.query.all()

    return render_template(
        'indexes/annotation_list.html', title=f"{text.title} - Annotations",
        next_page=next_page, prev_page=prev_page, sorts=sorts, sort=sort,
        annotations=annotations.items, annotationflags=annotationflags,
        uservotes=uservotes)
