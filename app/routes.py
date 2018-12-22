import re, difflib

from collections import defaultdict
from datetime import datetime

from flask import render_template, flash, redirect, url_for, request, abort, g
from flask_login import current_user, login_required, login_manager, logout_user
from sqlalchemy import and_

from app import app, db
from app.models import User, Text, Edition, Writer, WriterEditionConnection, \
        ConnectionEnum, Line, LineEnum, Annotation, Comment, AnnotationFlag, \
        AnnotationFlagEnum, Vote, Edit, EditVote, Tag, tags as tags_table, \
        authors as authors_table, Wiki, WikiEdit, WikiEditVote
from app.forms import AnnotationForm, LineNumberForm, SearchForm, CommentForm, \
        WikiForm
from app.funky import preplines, generate_next, line_check


@app.before_request
def before_request():
    if current_user.is_authenticated and current_user.locked:
        logout_user()
    g.search_form = SearchForm()


@app.route('/search')
def search():
    if not g.search_form.validate():
        return redirect(url_for('index'))
    page = request.args.get('page', 1, type=int)
    lines, line_total = Line.search(g.search_form.q.data, page,
            app.config['LINES_PER_SEARCH_PAGE'])
    next_page = url_for('search', q=g.search_form.q.data, page=page + 1)\
        if line_total > page * app.config['LINES_PER_SEARCH_PAGE']\
        else None
    prev_page = url_for('search', q=g.search_form.q.data, page=page - 1) \
        if page > 1 else None
    return render_template('indexes/search.html',
            title="Search", next_page=next_page, prev_page=prev_page,
            lines=lines, line_total=line_total)


@app.route('/')
@app.route('/index')
def index():
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'newest', type=str)

    if sort == 'newest':
        annotations = Annotation.query.filter_by(active=True)\
                .order_by(Annotation.timestamp.desc())\
                .paginate(page, app.config['ANNOTATIONS_PER_PAGE'], False)
    elif sort == 'oldest':
        annotations = Annotation.query.filter_by(active=True)\
                .order_by(Annotation.timestamp.asc())\
                .paginate(page, app.config['ANNOTATIONS_PER_PAGE'], False)
    elif sort == 'modified':
        annotations = Annotation.query.outerjoin(Edit,
                and_(Annotation.id==Edit.annotation_id, Edit.current==True))\
                .group_by(Annotation.id).order_by(Edit.timestamp.desc())\
                .paginate(page, app.config['ANNOTATIONS_PER_PAGE'], False)
    elif sort == 'weight':
        annotations = Annotation.query.filter_by(active=True)\
                .order_by(Annotation.weight.desc())\
                .paginate(page, app.config['ANNOTATIONS_PER_PAGE'], False)
    else:
        annotations = Annotation.query.filter_by(active=True)\
                .order_by(Annotation.timestamp.desc())\
                .paginate(page, app.config['ANNOTATIONS_PER_PAGE'], False)

    if not annotations.items:
        abort(404)

    sorts = {
            'newest': url_for('index', page=page, sort='newest'),
            'oldest': url_for('index', page=page, sort='oldest'),
            'modified': url_for('index', page=page, sort='modified'),
            'weight': url_for('index', page=page, sort='weight'),
            }

    annotationflags = AnnotationFlagEnum.query.all()

    next_page = url_for('index', page=annotations.next_num, sort=sort) \
            if annotations.has_next else None
    prev_page = url_for('index', page=annotations.prev_num, sort=sort) \
            if annotations.has_prev else None

    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None

    return render_template('indexes/annotation_list.html',
            title="Home",
            sort=sort, sorts=sorts, uservotes=uservotes,
            next_page=next_page, prev_page=prev_page,
            annotations=annotations.items, annotationflags=annotationflags, 
            active_page='index')


@app.route('/read/<text_url>/edition/<edition_num>', methods=['GET', 'POST'])
@app.route('/read/<text_url>', methods=['GET', 'POST'],
        defaults={'edition_num':None})
def read(text_url, edition_num):
    if edition_num:
        text = Text.query.filter_by(title=text_url.replace('_', ' '))\
                .first_or_404()
        edition = Edition.query.filter(Edition.text_id==text.id,
                Edition.num==edition_num).first_or_404()
    else:
        text = Text.query.filter_by(title=text_url.replace('_', ' '))\
                .first_or_404()
        edition = text.primary
    tag = request.args.get('tag', None, type=str)
    lvl = [request.args.get('l1', 0, type=int)]
    lvl.append(request.args.get('l2', 0, type=int))
    lvl.append(request.args.get('l3', 0, type=int))
    lvl.append(request.args.get('l4', 0, type=int))

    annotationflags = AnnotationFlagEnum.query.all()

    if lvl[3]:
        lines = edition.lines.filter(Line.lvl4==lvl[3], Line.lvl3==lvl[2],
                Line.lvl2==lvl[1], Line.lvl1==lvl[0])\
                        .order_by(Line.num.asc()).all()
    elif lvl[2]:
        lines = edition.lines.filter(Line.lvl3==lvl[2], Line.lvl2==lvl[1],
                Line.lvl1==lvl[0]).order_by(Line.num.asc()).all()
    elif lvl[1]:
        lines = edition.lines.filter(Line.lvl2==lvl[1], Line.lvl1==lvl[0])\
                .order_by(Line.num.asc()).all()
    elif lvl[0]:
        lines = edition.lines.filter(Line.lvl1==lvl[0])\
                .order_by(Line.num.asc()).all()
    else:
        lines = edition.lines.order_by(Line.num.asc()).all()

    if len(lines) <= 0:
        abort(404)

    form = LineNumberForm()

    next_page = lines[0].get_next_page()
    prev_page = lines[0].get_prev_page()

    if form.validate_on_submit():
        # line number boiler plate
        if not form.first_line.data and not form.last_line.data:
            flash("Please enter a first and last line number to annotate a"
                    " selection.")
            return redirect(request.full_path)
        elif not form.first_line.data:
            ll = int(form.last_line.data)
            fl = ll
        elif not form.last_line.data:
            fl = int(form.first_line.data)
            ll = fl
        else:
            fl = int(form.first_line.data)
            ll = int(form.last_line.data)

        if fl < 1:
            fl = 1
        if ll < 1:
            fl = 1
            ll = 1

        # redirect to annotate page, with next query param being the current
        # page. Multi-layered nested return statement. Read carefully.
        return redirect(url_for('annotate', text_url=text_url,
            edition_num=edition.num, first_line=fl, last_line=ll,
            next=request.full_path))

    # get all the annotations
    if tag:
        tag = Tag.query.filter_by(tag=tag).first_or_404()
        annotations = tag.annotations.filter(Annotation.edition_id==text.id,
                        Edit.first_line_num>=lines[0].num,
                        Edit.last_line_num<=lines[-1].num).all()
        tags = None
    else:
        annotations = edition.annotations.join(Edit,
                and_(Edit.annotation_id==Annotation.id, Edit.current==True))\
                .filter(Edit.last_line_num<=lines[-1].num,
                        Edit.first_line_num>=lines[0].num).all()
        # this query is like 5 times faster than the old double-for loop. I am,
        # however, wondering if some of the join conditions should be offloaded
        # into a filter
        tags = Tag.query.outerjoin(tags_table)\
                .join(Edit, and_(Edit.id==tags_table.c.edit_id,
                    Edit.current==True,
                    Edit.first_line_num>=lines[0].num,
                    Edit.last_line_num<=lines[-1].num))\
                .join(Annotation).filter(Annotation.edition_id==edition.id)\
                .all()

    # index the annotations in a dictionary
    annotations_idx = defaultdict(list)
    for a in annotations:
        annotations_idx[a.HEAD.last_line_num].append(a)

    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None

    # I have to query this so I only make a db call once instead of each time
    # for every line to find out if the user has edit_rights
    if current_user.is_authenticated:
        can_edit_lines = current_user.is_authorized('edit_lines')
    else:
        can_edit_lines = False

    # This custom method for replacing underscores with <em> tags is still way
    # faster than the markdown converter. Since I'm not using anything other
    # than underscores for italics in the body of the actual text (e.g., I'm
    # using other methods to indicate blockquotes), I'll just keep using this.
    preplines(lines)

    return render_template('read.html', title=text.title, form=form, text=text,
            edition=edition, lines=lines, annotations_idx=annotations_idx,
            uservotes=uservotes, tags=tags, tag=tag, next_page=next_page,
            prev_page=prev_page, can_edit_lines=can_edit_lines,
            annotationflags=annotationflags)



#####################
## Content Systems ##
#####################

# Writer routes
@app.route('/writer/list')
def writer_index():
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'last name', type=str)

    if sort == 'last name':
        writers = Writer.query.order_by(Writer.last_name.asc())\
                .paginate(page, app.config['CARDS_PER_PAGE'], False)
    elif sort == 'oldest':
        writers = Writer.query.order_by(Writer.birth_date.asc())\
                .paginate(page, app.config['CARDS_PER_PAGE'], False)
    elif sort == 'youngest':
        writers = Writer.query.order_by(Writer.birth_date.desc())\
                .paginate(page, app.config['CARDS_PER_PAGE'], False)
    elif sort == 'authored':
        writers = Writer.query.outerjoin(authors_table).outerjoin(Text,
                Text.id==authors_table.c.text_id).group_by(Writer.id)\
                .order_by(db.func.count(Text.id).desc())\
                .paginate(page, app.config['CARDS_PER_PAGE'], False)
    elif sort == 'edited':
        writers = Writer.query.outerjoin(WriterEditionConnection)\
                .outerjoin(ConnectionEnum,
                        and_(ConnectionEnum.id==WriterEditionConnection.enum_id,
                            ConnectionEnum.type=='Editor')).group_by(Writer.id)\
                .order_by(db.func.count(ConnectionEnum.id).desc())\
                .paginate(page, app.config['CARDS_PER_PAGE'], False)
    elif sort == 'translated':
        writers = Writer.query\
                .outerjoin(WriterEditionConnection).outerjoin(ConnectionEnum,
                        and_(ConnectionEnum.id==WriterEditionConnection.enum_id,
                            ConnectionEnum.type=='Translator'))\
                .group_by(Writer.id)\
                .order_by(db.func.count(ConnectionEnum.id).desc())\
                .paginate(page, app.config['CARDS_PER_PAGE'], False)
    else:
        writers = Writer.query.order_by(Writer.last_name.asc())\
                .paginate(page, app.config['CARDS_PER_PAGE'], False)

    if not writers.items:
        abort(404)

    sorts = {
            'last name': url_for('writer_index', sort='last name', page=page),
            'oldest': url_for('writer_index', sort='oldest', page=page),
            'youngest': url_for('writer_index', sort='youngest', page=page),
            'authored': url_for('writer_index', sort='authored', page=page),
            'edited': url_for('writer_index', sort='edited', page=page),
            'translated': url_for('writer_index', sort='translated', page=page),
            }

    next_page = url_for('writer_index', page=writers.next_num, sort=sort) \
            if writers.has_next else None
    prev_page = url_for('writer_index', page=writers.prev_num, sort=sort) \
            if writers.has_prev else None

    return render_template('indexes/writers.html', title="Authors",
            writers=writers.items, next_page=next_page, prev_page=prev_page,
            sorts=sorts, sort=sort)


@app.route('/writer/<writer_url>')
def writer(writer_url):
    writer = Writer.query.filter_by(name=writer_url.replace('_',' '))\
            .first_or_404()
    return render_template('view/writer.html', title=writer.name, writer=writer)


@app.route('/writer/<writer_url>/annotations')
def writer_annotations(writer_url):
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'weight', type=str)

    writer = Writer.query.filter_by(name=writer_url.replace('_',' '))\
            .first_or_404()

    if sort == 'newest':
        annotations = writer.annotations.order_by(Annotation.timestamp.desc())\
                .paginate(page, app.config['ANNOTATIONS_PER_PAGE'], False)
    elif sort == 'oldest':
        annotations = writer.annotations.order_by(Annotation.timestamp.asc())\
                .paginate(page, app.config['ANNOTATIONS_PER_PAGE'], False)
    elif sort == 'weight':
        annotations = writer.annotations.order_by(Annotation.weight.desc())\
                .paginate(page, app.config['ANNOTATIONS_PER_PAGE'], False)
    # tried to do sort==modified except it's totally buggy and I gotta sort
    # through the problems.
    else:
        annotations = writer.annotations.order_by(Annotation.timestamp.desc())\
                .paginate(page, app.config['ANNOTATIONS_PER_PAGE'], False)
        sort == 'newest'

    sorts = {
            'newest': url_for('writer_annotations', writer_url=writer.url,
                sort='newest', page=page),
            'oldest': url_for('writer_annotations', writer_url=writer.url,
                sort='oldest', page=page),
            'weight': url_for('writer_annotations', writer_url=writer.url,
                sort='weight', page=page),
            }

    annotationflags = AnnotationFlagEnum.query.all()

    next_page = url_for('writer_annotations', writer_url=writer.url, sort=sort,
            page=annotations.next_num) if annotations.has_next else None
    prev_page = url_for('writer_annotations', writer_url=writer.url, sort=sort,
            page=annotations.prev_num) if annotations.has_prev else None

    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None

    return render_template('indexes/annotation_list.html',
            title=f"{writer.name} - Annotations",
            next_page=next_page, prev_page=prev_page, sorts=sorts, sort=sort,
            annotations=annotations.items, annotationflags=annotationflags,
            uservotes=uservotes)


# Text routes
@app.route('/text/list')
def text_index():
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'title', type=str)

    if sort == 'title':
        texts = Text.query.order_by(Text.sort_title.asc())\
                .paginate(page, app.config['CARDS_PER_PAGE'], False)
    elif sort == 'author':
        texts = Text.query.join(authors_table).join(Writer)\
                .order_by(Writer.last_name.asc())\
                .paginate(page, app.config['CARDS_PER_PAGE'], False)
    elif sort == 'oldest':
        texts = Text.query.order_by(Text.published.asc())\
                .paginate(page, app.config['CARDS_PER_PAGE'], False)
    elif sort == 'newest':
        texts = Text.query.order_by(Text.published.desc())\
                .paginate(page, app.config['CARDS_PER_PAGE'], False)
    elif sort == 'length':
        texts = Text.query.join(Edition, and_(Edition.text_id==Text.id,
            Edition.primary==True)).outerjoin(Line).group_by(Text.id)\
                .order_by(db.func.count(Line.id).desc())\
                .paginate(page, app.config['CARDS_PER_PAGE'], False)
    elif sort == 'annotations':
        texts = Text.query.outerjoin(Edition, and_(Edition.text_id==Text.id,
            Edition.primary==True)).outerjoin(Annotation).group_by(Text.id)\
                .order_by(db.func.count(Annotation.id).desc())\
                .paginate(page, app.config['CARDS_PER_PAGE'], False)
    else:
        texts = Text.query.order_by(Text.sort_title.asc())\
                .paginate(page, app.config['CARDS_PER_PAGE'], False)

    if not texts.items:
        abort(404)

    sorts = {
            'title': url_for('text_index', sort='title', page=page),
            'author': url_for('text_index', sort='author', page=page),
            'oldest': url_for('text_index', sort='oldest', page=page),
            'newest': url_for('text_index', sort='newest', page=page),
            'length': url_for('text_index', sort='length', page=page),
            'annotations': url_for('text_index', sort='annotations', page=page),
    }

    next_page = url_for('text_index', page=texts.next_num, sort=sort) \
            if texts.has_next else None
    prev_page = url_for('text_index', page=texts.prev_num, sort=sort) \
            if texts.has_prev else None

    return render_template('indexes/texts.html', title="Texts",
            prev_page=prev_page, next_page=next_page,
            sorts=sorts, sort=sort,
            texts=texts.items)


@app.route('/text/<text_url>')
def text(text_url):
    text = Text.query.filter_by(title=text_url.replace('_',' ')).first_or_404()
    return render_template('view/text.html', title=text.title, text=text)


@app.route('/text/<text_url>/annotations')
def text_annotations(text_url):
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'weight', type=str)

    text = Text.query.filter_by(title=text_url.replace('_', ' ')).first_or_404()

    if sort == 'newest':
        annotations = text.annotations\
                .order_by(Annotation.timestamp.desc())\
                .paginate(page, app.config['ANNOTATIONS_PER_PAGE'], False)
    elif sort == 'oldest':
        annotations = text.annotations\
                .order_by(Annotation.timestamp.asc())\
                .paginate(page, app.config['ANNOTATIONS_PER_PAGE'], False)
    elif sort == 'weight':
        annotations = text.annotations\
                .order_by(Annotation.weight.desc())\
                .paginate(page, app.config['ANNOTATIONS_PER_PAGE'], False)
    elif sort == 'line':
        annotations = text.annotations\
                .join(Edit, Annotation.id==Edit.annotation_id)\
                .filter(Edit.current==True)\
                .order_by(Edit.last_line_num.asc())\
                .paginate(page, app.config['ANNOTATIONS_PER_PAGE'], False)
    else:
        annotations = text.annotations\
                .order_by(Annotation.timestamp.desc())\
                .paginate(page, app.config['ANNOTATIONS_PER_PAGE'], False)
        sort = 'newest'

    annotationflags = AnnotationFlagEnum.query.all()
    sorts = {
            'newest': url_for('text_annotations', text_url=text.url,
                sort='newest', page=page),
            'oldest': url_for('text_annotations', text_url=text.url,
                sort='oldest', page=page),
            'weight': url_for('text_annotations', text_url=text.url,
                sort='weight', page=page),
            'line': url_for('text_annotations', text_url=text.url, sort='line',
                page=page),
            }
    next_page = url_for('text_annotations', text_url=text.url, sort=sort,
            page=annotations.next_num) if annotations.has_next else None
    prev_page = url_for('text_annotations', text_url=text_url, sort=sort,
            page=annotations.prev_num) if annotations.has_prev else None
    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None
    return render_template('indexes/annotation_list.html',
            title=f"{text.title} - Annotations",
            next_page=next_page, prev_page=prev_page, sorts=sorts, sort=sort,
            annotations=annotations.items, annotationflags=annotationflags,
            uservotes=uservotes)


# Edition routes
@app.route('/text/<text_url>/edition/<edition_num>')
def edition(text_url, edition_num):
    text = Text.query.filter_by(title=text_url.replace('_',' ')).first_or_404()
    edition = Edition.query.filter(Edition.text_id==text.id,
        Edition.num==edition_num).first_or_404()

    # get the labels for each heierarchical chapter level
    labels = LineEnum.query.filter(LineEnum.label.startswith('lvl')).all()
    label_ids = [l.id for l in labels]

    # get all the heierarchical chapter lines
    hierarchy = edition.lines.filter(Line.label_id.in_(label_ids))\
            .order_by(Line.num.asc()).all()

    return render_template('view/edition.html', 
            title=f"{text.title} #{edition.num}",
            hierarchy=hierarchy, edition=edition)


@app.route('/text/<text_url>/edition/<edition_num>/annotations')
def edition_annotations(text_url, edition_num):
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'weight', type=str)

    text = Text.query.filter_by(title=text_url.replace('_', ' ')).first_or_404()
    edition = text.editions.filter_by(num=edition_num).first()

    if sort == 'newest':
        annotations = edition.annotations.order_by(Annotation.timestamp.desc())\
                .paginate(page, app.config['ANNOTATIONS_PER_PAGE'], False)
    elif sort == 'oldest':
        annotations = text.annotations.order_by(Annotation.timestamp.asc())\
                .paginate(page, app.config['ANNOTATIONS_PER_PAGE'], False)
    elif sort == 'weight':
        annotations = text.annotations.order_by(Annotation.weight.desc())\
                .paginate(page, app.config['ANNOTATIONS_PER_PAGE'], False)
    elif sort == 'line':
        annotations = text.annotations.join(Edit,
                Annotation.id==Edit.annotation_id).filter(Edit.current==True)\
                .order_by(Edit.last_line_num.asc()).paginate(page,
                        app.config['ANNOTATIONS_PER_PAGE'], False)
    else:
        annotations = text.annotations.order_by(Annotation.timestamp.desc())\
                .paginate(page, app.config['ANNOTATIONS_PER_PAGE'], False)
        sort = 'newest'

    sorts = {
            'newest': url_for('edition_annotations', text_url=text.url,
                edition_num=edition.num, sort='newest', page=page),
            'oldest': url_for('edition_annotations', text_url=text.url,
                edition_num=edition.num, sort='oldest', page=page),
            'weight': url_for('edition_annotations', text_url=text.url,
                edition_num=edition.num, sort='weight', page=page),
            'line': url_for('edition_annotations', text_url=text.url,
                edition_num=edition.num, sort='line', page=page),
            }

    next_page = url_for('edition_annotations', text_url=text.url,
            edition_num=edition.num, sort=sort, page=annotations.next_num)\
                    if annotations.has_next else None
    prev_page = url_for('edition_annotations', text_url=text_url,
            edition_num=edition.num, sort=sort, page=annotations.prev_num)\
                    if annotations.has_prev else None

    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None
    annotationflags = AnnotationFlagEnum.query.all()

    return render_template('indexes/annotation_list.html',
            title=f"{text.title} - Annotations",
            next_page=next_page, prev_page=prev_page, sorts=sorts, sort=sort,
            annotations=annotations.items, annotationflags=annotationflags,
            uservotes=uservotes)


# Tag routes
@app.route('/tag/list')
def tag_index():
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'tag', type=str)

    if sort == 'tag':
        tags = Tag.query.order_by(Tag.tag)\
                .paginate(page, app.config['CARDS_PER_PAGE'], False)
    elif sort == 'annotations':
        # This doesn't do anything but the same sort yet
        tags = Tag.query.outerjoin(tags_table).outerjoin(Edit,
                and_(Edit.id==tags_table.c.edit_id, Edit.current==True))\
                .group_by(Tag.id).order_by(db.func.count(Edit.id).desc())\
                .paginate(page, app.config['CARDS_PER_PAGE'], False)
    else:
        tags = Tag.query.order_by(Tag.tag)\
                .paginate(page, app.config['CARDS_PER_PAGE'], False)

    if not tags.items:
        abort(404)

    sorts = {
            'tag': url_for('tag_index', sort='tag', page=page),
            'annotations': url_for('tag_index', sort='annotations', page=page)
            }

    next_page = url_for('tag_index', page=tags.next_num, sort=sort) \
            if tags.has_next else None
    prev_page = url_for('tag_index', page=tags.prev_num, sort=sort) \
            if tags.has_prev else None

    return render_template('indexes/tags.html', title="Tags",
            next_page=next_page, prev_page=prev_page, sorts=sorts, sort=sort,
            tags=tags.items)


@app.route('/tag/<tag>')
def tag(tag):
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'modified', type=str)

    tag = Tag.query.filter_by(tag=tag).first_or_404()

    if sort == 'newest':
        annotations = tag.annotations.order_by(Annotation.timestamp.desc())\
                .paginate(page, app.config['ANNOTATIONS_PER_PAGE'], False)
    elif sort == 'weight':
        annotations = tag.annotations.order_by(Annotation.weight.desc())\
                .paginate(page, app.config['ANNOTATIONS_PER_PAGE'], False)
    elif sort == 'oldest':
        annotations = tag.annotations.order_by(Annotation.timestamp.asc())\
                .paginate(page, app.config['ANNOTATIONS_PER_PAGE'], False)
    elif sort == 'modified':
        annotations = tag.annotations.order_by(Edit.timestamp.desc())\
                .paginate(page, app.config['ANNOTATIONS_PER_PAGE'], False)
    else:
        annotations = tag.annotations.order_by(Annotation.timestamp.desc())\
                .paginate(page, app.config['ANNOTATIONS_PER_PAGE'], False)

    sorts = {
            'newest': url_for('tag', tag=tag.tag, page=page, sort='newest'),
            'oldest': url_for('tag', tag=tag.tag, page=page, sort='oldest'),
            'weight': url_for('tag', tag=tag.tag, page=page, sort='weight'),
            'modified': url_for('tag', tag=tag.tag, page=page, sort='modified'),
            }

    next_page = url_for('tag', tag=tag.tag, page=annotations.next_num,
            sort=sort) if annotations.has_next else None
    prev_page = url_for('tag', tag=tag.tag, page=annotations.prev_num,
            sort=sort) if annotations.has_prev else None

    annotationflags = AnnotationFlagEnum.query.all()
    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None

    return render_template('view/tag.html', title=tag.tag,
            next_page=next_page, prev_page=prev_page, sorts=sorts, sort=sort,
            tag=tag, annotations=annotations.items,
            annotationflags=annotationflags, uservotes=uservotes)



#################
## Wiki System ##
#################

@app.route('/wiki/<wiki_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_wiki(wiki_id):
    form = WikiForm()
    wiki = Wiki.query.get_or_404(wiki_id)
    redirect_url = generate_next(wiki.entity.get_url())

    if wiki.edit_pending:
        flash("That wiki is locked from a pending edit.")
        return redirect(redirect_url)

    if form.validate_on_submit():
        wiki.edit(current_user, body=form.wiki.data, reason=form.reason.data)
        db.session.commit()
        return redirect(redirect_url)

    form.wiki.data = wiki.current.body

    return render_template('forms/wiki.html', title="Edit wiki", form=form)


@app.route('/wiki/<wiki_id>/history')
def wiki_edit_history(wiki_id):
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'num', type=str)

    wiki = Wiki.query.get_or_404(wiki_id)

    if sort == 'num':
        edits = wiki.edits.filter(WikiEdit.approved==True)\
                .order_by(WikiEdit.num.desc())\
                .paginate(page, app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'num_invert':
        edits = wiki.edits.filter(WikiEdit.approved==True)\
                .order_by(WikiEdit.num.asc())\
                .paginate(page, app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'editor':
        edits = wiki.edits.outerjoin(User).filter(WikiEdit.approved==True)\
                .order_by(User.displayname.asc())\
                .paginate(page, app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'editor_invert':
        edits = wiki.edits.outerjoin(User).filter(WikiEdit.approved==True)\
                .order_by(User.displayname.desc())\
                .paginate(page, app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'time':
        edits = wiki.edits.filter(WikiEdit.approved==True)\
                .order_by(WikiEdit.timestamp.asc())\
                .paginate(page, app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'time_invert':
        edits = wiki.edits.filter(WikiEdit.approved==True)\
                .order_by(WikiEdit.timestamp.desc())\
                .paginate(page, app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'reason':
        edits = wiki.edits.filter(WikiEdit.approved==True)\
                .order_by(WikiEdit.reason.asc())\
                .paginate(page, app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'reason_invert':
        edits = wiki.edits.filter(WikiEdit.approved==True)\
                .order_by(WikiEdit.reason.desc())\
                .paginate(page, app.config['NOTIFICATIONS_PER_PAGE'], False)
    else:
        edits = wiki.edits.filter(WikiEdit.approved==True)\
                .order_by(WikiEdit.num.desc())\
                .paginate(page, app.config['NOTIFICATIONS_PER_PAGE'], False)
        sort = 'num'

    next_page = url_for('admin.wiki_edit_review_queue', page=edits.next_num,
            sort=sort) if edits.has_next else None
    prev_page = url_for('admin.wiki_edit_review_queue', page=edits.prev_num,
            sort=sort) if edits.has_prev else None

    return render_template('indexes/wiki_edits.html',
            title=f"{str(wiki.entity)} Edit History",
            next_page=next_page, prev_page=prev_page, page=page, sort=sort,
            edits=edits.items, wiki=wiki)


@app.route('/wiki/<wiki_id>/edit/<edit_num>')
def view_wiki_edit(wiki_id, edit_num):
    wiki = Wiki.query.get_or_404(wiki_id)
    edit = wiki.edits.filter(WikiEdit.approved==True,
            WikiEdit.num==edit_num).first_or_404()

    if not edit.previous:
        return render_template('view/wiki_first_version.html',
                title=f'First Version of {str(edit.wiki.entity)} wiki',
                edit=edit)

    # we have to replace single returns with spaces because markdown only
    # recognizes paragraph separation based on two returns. We also have to be
    # careful to do this for both unix and windows return variants (i.e. be
    # careful of \r's).
    diff1 = re.sub(r'(?<!\n)\r?\n(?![\r\n])', ' ', edit.previous.body)
    diff2 = re.sub(r'(?<!\n)\r?\n(?![\r\n])', ' ', edit.body)

    diff = list(difflib.Differ().compare(diff1.splitlines(),
        diff2.splitlines()))

    return render_template('view/wiki_edit.html',
            title=f"{str(edit.wiki.entity)} edit #{edit.num}",
            diff=diff, edit=edit)



#######################
## Annotation System ##
#######################

# Annotation routes
### THIS IS BROKEN RIGHT NOW
@app.route('/annotate/<text_url>/<first_line>/<last_line>',
        methods=['GET', 'POST'], defaults={'edition_num':None})
@app.route('/annotate/<text_url>/edition/<edition_num>/<first_line>/<last_line>',
        methods=['GET', 'POST'])
@login_required
def annotate(text_url, edition_num, first_line, last_line):
    if int(first_line) > int(last_line):
        tmp = first_line
        first_line = last_line
        last_line = tmp
    if int(first_line) < 1:
        first_line = 1
    if int(last_line) < 1:
        first_line = 1
        last_line = 1

    text = Text.query.filter_by(title=text_url.replace('_',' ')).first_or_404()
    if edition_num:
        edition = Edition.query.filter(Edition.text_id==text.id,
                Edition.num==edition_num).first_or_404()
    else:
        edition = text.primary
    lines = edition.lines.filter(Line.num>=first_line,
            Line.num<=last_line).all()
    context = edition.lines.filter(Line.num>=int(first_line)-5,
            Line.num<=int(last_line)+5).all()
    form = AnnotationForm()

    if lines == None:
        abort(404)

    redirect_url = generate_next(lines[0].get_url())

    if form.validate_on_submit():
        # line number boiler plate
        fl, ll = line_check(int(form.first_line.data), int(form.last_line.data))

        # Process all the tags
        raw_tags = form.tags.data.split()
        tags = []
        for tag in raw_tags:
            t = Tag.query.filter_by(tag=tag).first()
            if t:
                tags.append(t)
            else:
                flash(f"tag {tag} does not exist.")
                return render_template('forms/annotation.html',
                        title=book.title, form=form, text=text, edition=edition,
                        lines=lines, context=context)

        if len(tags) > 5:
            flash("There is a five tag limit.")
            return render_template('forms/annotation.html', title=book.title,
                    form=form, text=text, edition=edition, lines=lines,
                    context=context)

        annotation = Annotation(edition=edition, annotator=current_user, fl=fl,
                ll=ll, fc=form.first_char_idx.data, lc=form.last_char_idx.data,
                body=form.annotation.data, tags=tags)

        db.session.add(annotation)
        db.session.commit()

        flash("Annotation Submitted")

        return redirect(redirect_url)
    else:
        form.first_line.data = first_line
        form.last_line.data = last_line
        form.first_char_idx.data = 0
        form.last_char_idx.data = -1

    return render_template('forms/annotation.html',
            title=f"Annotating {text.title}", form=form, text=text,
            edition=edition, lines=lines, context=context)


@app.route('/annotation/<annotation_id>')
def annotation(annotation_id):
    annotation = Annotation.query.get_or_404(annotation_id)
    if not annotation.active:
        current_user.authorize('view_deactivated_annotations')

    annotationflags = AnnotationFlagEnum.query.all()
    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None

    return render_template('view/annotation.html',
            title=f"Annotation [{annotation.id}]",
            annotation=annotation, uservotes=uservotes,
            annotationflags=annotationflags)


@app.route('/annotation/<annotation_id>/flag/<flag_id>')
@login_required
def flag_annotation(flag_id, annotation_id):
    redirect_url = generate_next(url_for('annotation',
        annotation_id=annotation.id))

    annotation = Annotation.query.get_or_404(annotation_id)
    if not annotation.active:
        current_user.authorize('view_deactivated_annotations')
    flag = AnnotationFlagEnum.query.get_or_404(flag_id)

    annotation.flag(flag, current_user)
    db.session.commit()
    flash(f"Annotation {annotation.id} flagged \"{flag.flag}\"")
    return redirect(redirect_url)


# Voting routes
@app.route('/upvote/<annotation_id>')
@login_required
def upvote(annotation_id):
    redirect_url = generate_next(url_for('annotation',
        annotation_id=annotation_id))

    annotation = Annotation.query.get_or_404(annotation_id)
    if not annotation.active:
        flash("You cannot vote on deactivated annotations.")
        return redirect(redirect_url)

    if current_user == annotation.annotator:
        flash("You cannot vote on your own annotations.")
        return redirect(redirect_url)
    elif current_user.already_voted(annotation):
        vote = current_user.ballots.filter(Vote.annotation==annotation).first()
        diff = datetime.utcnow() - vote.timestamp

        if diff.days > 0 and annotation.HEAD.modified < vote.timestamp:
            flash("Your vote is locked until the annotation is modified.")
            return redirect(redirect_url)
        elif vote.is_up():
            annotation.rollback(vote)
            db.session.commit()
            return redirect(redirect_url)
        else:
            annotation.rollback(vote)

    annotation.upvote(current_user)
    db.session.commit()

    return redirect(redirect_url)


@app.route('/downvote/<annotation_id>')
@login_required
def downvote(annotation_id):
    redirect_url = generate_next(url_for('annotation',
        annotation_id=annotation_id))

    annotation = Annotation.query.get_or_404(annotation_id)
    if not annotation.active:
        flash("You cannot vote on deactivated annotations.")

    if current_user == annotation.annotator:
        flash("You cannot vote on your own annotation.")
        return redirect(redirect_url)
    elif current_user.already_voted(annotation):
        vote = current_user.ballots.filter(Vote.annotation==annotation).first()
        diff = datetime.utcnow() - vote.timestamp

        if diff.days > 0 and annotation.HEAD.modified < vote.timestamp:
            flash("Your vote is locked until the annotation is modified.")
            return redirect(redirect_url)
        elif not vote.is_up():
            annotation.rollback(vote)
            db.session.commit()
            return redirect(redirect_url)
        else:
            annotation.rollback(vote)

    annotation.downvote(current_user)
    db.session.commit()

    return redirect(redirect_url)


# Edit routes
@app.route('/edit/<annotation_id>', methods=['GET', 'POST'])
@login_required
def edit(annotation_id):
    form = AnnotationForm()
    redirect_url = generate_next(url_for('annotation',
        annotation_id=annotation_id))

    annotation = Annotation.query.get_or_404(annotation_id)
    if annotation.locked == True\
            and not current_user.is_authorized('edit_locked_annotations'):
        flash("That annotation is locked from editing.")
        return redirect(redirect_url)
    elif annotation.edit_pending:
        flash("There is an edit still pending peer review.")
        return redirect(redirect_url)
    elif not annotation.active:
        current_user.authorize('edit_deactivated_annotations')

    lines = annotation.HEAD.lines
    context = annotation.HEAD.context

    if form.validate_on_submit():
        # line number boilerplate
        fl, ll = line_check(int(form.first_line.data), int(form.last_line.data))
        fail = False # if at any point we run into problems, flip this var

        raw_tags = form.tags.data.split()
        tags = []
        for tag in raw_tags:
            t = Tag.query.filter_by(tag=tag).first()
            if t:
                tags.append(t)
            else:
                fail = True
                flash(f"tag {tag} does not exist.")
        if len(tags) > 5:
            fail = True
            flash("There is a five tag limit.")

        success = annotation.edit(editor=current_user,
                reason=form.reason.data, fl=fl, ll=ll,
                fc=form.first_char_idx.data, lc=form.last_char_idx.data,
                body=form.annotation.data, tags=tags)

        # rerender the template with the work already filled
        if not success or not fail:
            db.session.rollback()
            return render_template('forms/annotation.html', form=form,
                    title=annotation.text.title, lines=lines,
                    text=annotation.text, annotation=annotation)
        db.session.commit()
        return redirect(redirect_url)

    elif not annotation.edit_pending:
        tag_strings = []
        for t in annotation.HEAD.tags: tag_strings.append(t.tag)
        form.first_line.data = annotation.HEAD.first_line_num
        form.last_line.data = annotation.HEAD.last_line_num
        form.first_char_idx.data = annotation.HEAD.first_char_idx
        form.last_char_idx.data = annotation.HEAD.last_char_idx
        form.annotation.data = annotation.HEAD.body
        form.tags.data = ' '.join(tag_strings)
    return render_template('forms/annotation.html', form=form,
            title=f"Edit Annotation {annotation.id}",
            text=annotation.text, lines=lines, annotation=annotation,
            context=context)


@app.route('/annotation/<annotation_id>/edit/history')
def edit_history(annotation_id):
    annotation = Annotation.query.get_or_404(annotation_id)
    if not annotation.active:
        current_user.authorize('view_deactivated_annotations')

    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'num_invert', type=str)

    if sort == 'num':
        edits = annotation.history.filter(Edit.approved==True)\
                .order_by(Edit.num.asc())\
                .paginate(page, app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'num_invert':
        edits = annotation.history.filter(Edit.approved==True)\
                .order_by(Edit.num.desc())\
                .paginate(page, app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'editor':
        edits = annotation.history.outerjoin(User).filter(Edit.approved==True)\
                .order_by(User.displayname.asc())\
                .paginate(page, app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'editor_invert':
        edits = annotation.history.outerjoin(User).filter(Edit.approved==True)\
                .order_by(User.displayname.desc())\
                .paginate(page, app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'time':
        edits = annotation.history.filter(Edit.approved==True)\
                .order_by(Edit.timestamp.asc())\
                .paginate(page, app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'time_invert':
        edits = annotation.history.filter(Edit.approved==True)\
                .order_by(Edit.timestamp.desc())\
                .paginate(page, app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'reason':
        edits = annotation.history.filter(Edit.approved==True)\
                .order_by(Edit.reason.asc())\
                .paginate(page, app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'reason_invert':
        edits = annotation.history.filter(Edit.approved==True)\
                .order_by(Edit.reason.desc())\
                .paginate(page, app.config['NOTIFICATIONS_PER_PAGE'], False)
    else:
        edits = annotation.history.outerjoin(EditVote,
                and_(EditVote.user_id==current_user.id,
                    EditVote.edit_id==Edit.id)).filter(Edit.approved==True)\
                .order_by(EditVote.delta.desc())\
                .paginate(page, app.config['NOTIFICATIONS_PER_PAGE'], False)
        sort = 'voted'


    next_page = url_for('edit_review_queue', page=edits.next_num, sort=sort)\
            if edits.has_next else None
    prev_page = url_for('edit_review_queue', page=edits.prev_num, sort=sort)\
            if edits.has_prev else None

    return render_template('indexes/edit_history.html', title="Edit History",
            next_page=next_page, prev_page=prev_page, page=page, sort=sort,
            edits=edits.items, annotation=annotation)


@app.route('/annotation/<annotation_id>/edit/<num>')
def view_edit(annotation_id, num):
    edit = Edit.query.filter( Edit.annotation_id==annotation_id, Edit.num==num,
            Edit.approved==True).first_or_404()
    if not edit.previous:
        return render_template('view/first_version.html',
                title=f'First Version of [{edit.annotation.id}]', edit=edit)

    # we have to replace single returns with spaces because markdown only
    # recognizes paragraph separation based on two returns. We also have to be
    # careful to do this for both unix and windows return variants (i.e. be
    # careful of \r's).
    diff1 = re.sub(r'(?<!\n)\r?\n(?![\r\n])', ' ', edit.previous.body)
    diff2 = re.sub(r'(?<!\n)\r?\n(?![\r\n])', ' ', edit.body)
    diff = list(difflib.Differ().compare(diff1.splitlines(),
        diff2.splitlines()))

    tags = [tag for tag in edit.tags]
    for tag in edit.previous.tags:
        if tag not in tags:
            tags.append(tag)

    if edit.first_line_num > edit.previous.first_line_num:
        context = [line for line in edit.previous.context]
        for line in edit.context:
            if line not in context:
                context.append(line)
    else:
        context = [line for line in edit.context]
        for line in edit.previous.context:
            if line not in context:
                context.append(line)

    return render_template('view/edit.html',
            title=f"Edit number {edit.num}",
            diff=diff, edit=edit, tags=tags, context=context)


# Comment routes
@app.route('/annotation/<annotation_id>/comments', methods=['GET', 'POST'])
@login_required
def comments(annotation_id):
    page = request.args.get('page', 1, type=int)
    form = CommentForm()

    annotation = Annotation.query.get_or_404(annotation_id)
    comments = annotation.comments.filter(Comment.depth==0).paginate(page,
            app.config['COMMENTS_PER_PAGE'], False)

    if form.validate_on_submit():
        comment = Comment(annotation=annotation, body=form.comment.data,
                poster=current_user)
        db.session.add(comment)
        db.session.commit()
        flash("Comment posted")
        return redirect(url_for('comments', annotation_id=annotation.id))

    return render_template('indexes/comments.html',
            title=f"[{annotation.id}] comments",
            form=form, annotation=annotation, comments=comments.items)


@app.route('/annotation/<annotation_id>/comment/<comment_id>/reply',
        methods=['GET', 'POST'])
@login_required
def reply(annotation_id, comment_id):
    form = CommentForm()

    annotation = Annotation.query.get_or_404(annotation_id)
    comment = Comment.query.get_or_404(comment_id)

    if form.validate_on_submit():
        reply = Comment(annotation=annotation, body=form.comment.data,
                poster=current_user, parent=comment, depth=comment.depth+1)
        db.session.add(reply)
        db.session.commit()
        flash("Reply posted")
        return redirect(url_for('comments', annotation_id=annotation.id))
    return render_template('forms/reply.html', title="Reply",
            form=form, comment=comment)
