"""The routes governing editions."""
from flask import render_template, url_for, request, abort, current_app
from icc.main import main

from icc.models.annotation import Annotation, Edit
from icc.models.content import Text, Edition


@main.route('/text/<text_url>/edition/<edition_num>')
def edition(text_url, edition_num):
    """The main edition view."""
    text = Text.query.filter_by(title=text_url.replace('_', ' ')).first_or_404()
    edition = Edition.query.filter(Edition.text_id==text.id,
                                   Edition.num==edition_num).first_or_404()
    hierarchy = edition.toc()
    return render_template('view/edition.html',
                           title=f"{text.title} #{edition.num}",
                           hierarchy=hierarchy, edition=edition)


@main.route('/text/<text_url>/edition/<edition_num>/annotations')
def edition_annotations(text_url, edition_num):
    """The annotations for the edition."""
    default = 'newest'
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'weight', type=str)
    text = Text.query.filter_by(title=text_url.replace('_', ' ')).first_or_404()
    edition = text.editions.filter_by(num=edition_num).first_or_404()

    sorts = {
        'newest': (edition.annotations.filter_by(active=True)
                   .order_by(Annotation.timestamp.desc())),
        'oldest': (edition.annotations.filter_by(active=True)
                   .order_by(Annotation.timestamp.asc())),
        'modified': (edition.annotations.join(Edit)
                     .filter(Annotation.active==True, Edit.current==True)
                     .order_by(Edit.timestamp.desc())),
        'weight': (edition.annotations.filter_by(active=True)
                   .order_by(Annotation.weight.desc())),
        'line': (edition.annotations.join(Edit)
                 .filter(Annotation.active==True, Edit.current==True)
                 .order_by(Edit.last_line_num.asc()))
    }

    sort = sort if sort in sorts else default
    annotations = sorts[sort]\
        .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    if not annotations.items and page > 1:
        abort(404)

    sorturls = {key: url_for('main.edition_annotations', text_url=text_url,
                             edition_num=edition_num, page=page, sort=key) for
                key in sorts.keys()}
    next_page = url_for(
        'main.edition_annotations', text_url=text.url, edition_num=edition.num,
        sort=sort, page=annotations.next_num) if annotations.has_next else None
    prev_page = url_for(
        'main.edition_annotations', text_url=text_url, edition_num=edition.num,
        sort=sort, page=annotations.prev_num) if annotations.has_prev else None
    return render_template('indexes/annotation_list.html',
                           title=f"{text.title} - Annotations",
                           next_page=next_page, prev_page=prev_page,
                           sorts=sorturls, sort=sort,
                           annotations=annotations.items)
