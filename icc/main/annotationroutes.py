
@main.route('/text/<text_url>/edition/<edition_num>/annotations')
def edition_annotations(text_url, edition_num):
    """The annotations for the edition."""
    default = 'newest'
    sort = request.args.get('sort', default, type=str)
    page = request.args.get('page', 1, type=int)
    text = Text.query.filter_by(title=text_url.replace('_', ' ')).first_or_404()
    edition = text.editions.filter_by(num=edition_num).first_or_404()

    sorts = {
        'newest': edition.annotations.order_by(Annotation.timestamp.desc()),
        'oldest': edition.annotations.order_by(Annotation.timestamp.asc()),
        'modified': (edition.annotations.join(Edit)
                     .filter(Edit.current==True)
                     .order_by(Edit.timestamp.desc())),
        'weight': edition.annotations.order_by(Annotation.weight.desc()),
        'line': (edition.annotations.join(Edit)
                 .filter(Edit.current==True)
                 .order_by(Edit.last_line_num.asc()))
    }

    sort = sort if sort in sorts else default
    annotations = sorts[sort].filter(Annotation.active==True)\
        .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    if not annotations.items and page > 1:
        abort(404)

    sorturls = {key: url_for('main.edition_annotations', text_url=text_url,
                             edition_num=edition_num, sort=key) for key in
                sorts.keys()}
    next_page = (url_for('main.edition_annotations', text_url=text.url,
                         edition_num=edition.num, sort=sort,
                         page=annotations.next_num) if annotations.has_next else
                 None)
    prev_page = (url_for('main.edition_annotations', text_url=text_url,
                         edition_num=edition.num, sort=sort,
                         page=annotations.prev_num) if annotations.has_prev else
                 None)
    return render_template('indexes/annotation_list.html',
                           title=f"{str(edition)} - Annotations",
                           next_page=next_page, prev_page=prev_page,
                           sorts=sorturls, sort=sort,
                           annotations=annotations.items)