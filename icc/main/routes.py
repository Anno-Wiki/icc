"""This file is the absolute primary collection of routes. That is to say, it
consists of the sine qua non routes for the icc. They include:

- login, logout, and register
- The search route
- The primary index
- The list of annotations by line route
- The read route.

Of course, one could argue that the annotation routes are the sine qua non of
the icc. I would argue that you are an idiot.
"""

import jwt
from string import ascii_lowercase as lowercase
from collections import defaultdict

from flask import (render_template, redirect, url_for, request, abort, g, flash,
                   current_app)
from flask_login import current_user, logout_user, login_user, login_required

from icc import db, classes
from icc.funky import line_check, generate_next
from icc.main import main

from icc.models.annotation import Annotation, Edit, AnnotationFlag, Comment
from icc.models.content import Text, Edition, Line
from icc.models.user import User

from icc.forms import SearchForm
from icc.main.forms import RegistrationForm, LoginForm, LineNumberForm


@main.before_app_request
def before_request():
    """The before request route makes sure that the user's account is not
    locked. If it is, then it logs them out. It then adds the search form and
    the list of annotation flagas to the global variable.
    """
    if current_user.is_authenticated and current_user.locked:
        logout_user()
    g.search_form = SearchForm()
    g.aflags = AnnotationFlag.enum_cls.query.all()


@main.route('/register', methods=['GET', 'POST'])
def register():
    redirect_url = generate_next(url_for('main.index'))
    if current_user.is_authenticated:
        return redirect(redirect_url)
    form = RegistrationForm()
    if form.validate_on_submit():
        token = request.args.get('token')
        email = jwt.decode(token, current_app.config['SECRET_KEY'],
                        algorithms=['HS256'])['email'] if token else None
        if current_app.config['HASH_REGISTRATION'] and email != form.email.data:
            flash("Registration is currently invite only. Either you have "
                  "submitted an invalid invite token, or no invite token at "
                  "all. Public registration will begin soon. Please have "
                  "patience. Alternatively, if you recieved an email token, "
                  "please contact your administrator for a fresh one.")
            return redirect(redirect_url)
        user = User(displayname=form.displayname.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Congratulations, you are now a registered user!")
        login_user(user)
        return redirect(redirect_url)
    return render_template('forms/register.html', title="Register", form=form)


@main.route('/login', methods=['GET', 'POST'])
def login():
    redirect_url = generate_next(url_for('main.index'))
    if current_user.is_authenticated:
        return redirect(redirect_url)
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.locked:
            flash("That account is locked.")
            return redirect(url_for('main.login', next=redirect_url))
        elif user is None or not user.check_password(form.password.data):
            flash("Invalid email or password")
            return redirect(url_for('main.login', next=redirect_url))
        login_user(user, remember=form.remember_me.data)

        return redirect(redirect_url)

    return render_template('forms/login.html', title="Sign In", form=form)


@main.route('/logout')
def logout():
    redirect_url = generate_next(url_for('main.index'))
    logout_user()
    return redirect(redirect_url)


@main.route('/search')
def search():
    """The search method is for lines. It uses elasticsearch to search for a
    given line, which can then be reviewed, and checked for annotations in
    another view.

    A separate search function will be created for the omni-search. Lines are
    the primary way of interacting with the application. Eventually my
    omni-search will be parsed to handle searching annotations, wikis, and tags.
    """
    page = request.args.get('page', 1, type=int)
    lines, line_total = Line.search(g.search_form.q.data, page,
                                    current_app.config['LINES_PER_SEARCH_PAGE'])
    val = line_total.get('value', 1)
    next_page = (url_for('main.search', q=g.search_form.q.data, page=page + 1)
                 if val > page *
                 current_app.config['LINES_PER_SEARCH_PAGE'] else None)
    prev_page = url_for('main.search', q=g.search_form.q.data, page=page - 1)\
        if page > 1 else None
    return render_template('indexes/search.html', title="Search",
                           next_page=next_page, prev_page=prev_page,
                           lines=lines, line_total=line_total)


@main.route('/')
@main.route('/index')
def index():
    """The main index page for the web site. It defaults to displaying the
    newest annotations because I want the newest ones reviewed.
    """
    default = 'newest'
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', default, type=str)

    sorts = {
        'newest': Annotation.query.order_by(Annotation.id.desc()),
        'oldest': Annotation.query.order_by(Annotation.id.asc()),
        'modified': (Annotation.query.join(Edit).order_by(Edit.timestamp.desc())
                     .filter(Edit.current==True)),
        'weight': Annotation.query.order_by(Annotation.weight.desc()),
        'active': (Annotation.query.join(Comment).group_by(Annotation.id)
                   .order_by(Comment.timestamp.desc()))
    }

    sort = sort if sort in sorts else default
    annotations = sorts[sort].filter(Annotation.active==True)\
        .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    if not annotations.items and page > 1:
        abort(404)

    sorturls = {key: url_for('main.index', sort=key) for key in
                sorts.keys()}
    next_page = (url_for('main.index', page=annotations.next_num, sort=sort) if
                 annotations.has_next else None)
    prev_page = (url_for('main.index', page=annotations.prev_num, sort=sort) if
                 annotations.has_prev else None)
    return render_template('indexes/annotation_list.html', title="Home",
                           active_page='index',
                           sort=sort, sorts=sorturls,
                           next_page=next_page, prev_page=prev_page,
                           annotations=annotations.items)


def string_to_tuple(string):
    string = string.strip('l')
    if '-' in string:
        ls = string.split('-')
        ints = tuple(map(int, ls))
    else:
        ints = int(string),
    return ints


@main.route('/text/<text_url>/edition/<edition_num>/<nums>')
@main.route('/text/<text_url>/<nums>', defaults={'edition_num': None})
def lines(text_url, edition_num, nums):
    """See the particular lines from a particular text/edition."""
    text = Text.get_by_url(text_url).first_or_404()
    edition = (text.primary if not edition_num else
               Edition.query.filter(Edition.text==text,
                                    Edition.num==edition_num).first_or_404())
    intnums = string_to_tuple(nums)
    lines = edition.get_lines(intnums).all()
    return render_template('view/lines.html', title=f'{text.title} {nums}',
                           text=text, edition=edition, nums=nums, lines=lines)


@main.route('/text/<text_url>/edition/<edition_num>/<nums>/annotations')
@main.route('/text/<text_url>/<nums>/annotations', defaults={'edition_num': None})
def line_annotations(text_url, edition_num, nums):
    """See all annotations for given set of lines. That is to say, all the
    annotations which have this particular line within their target body.
    """
    default = 'newest'
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', default, type=str)
    text = Text.get_by_url(text_url).first_or_404()
    edition = (text.primary if not edition_num else
               Edition.query.filter(Edition.text==text,
                                    Edition.num==edition_num).first_or_404())

    intnums = string_to_tuple(nums)

    sorts = {
        'newest': edition.annotations.order_by(Annotation.timestamp.desc()),
        'oldest': edition.annotations.order_by(Annotation.timestamp.asc()),
        'weight': edition.annotations.order_by(Annotation.weight.desc()),
        'line': edition.annotations.order_by(Edit.last_line_num.asc()),
        'modified': (edition.annotations.order_by(Edit.timestamp.desc())
                     .filter(Edit.current==True))
    }

    # if there is a single num, then we're going to duplicate it
    intnums = intnums*2 if len(intnums) == 1 else intnums

    sort = sort if sort in sorts else default
    annotations = sorts[sort]\
        .join(Edit).filter(Edit.current==True).group_by(Annotation.id)\
        .filter(Annotation.active==True, Edit.first_line_num>=intnums[0],
                Edit.last_line_num<=intnums[-1])\
        .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)

    if not annotations.items and page > 1:
        abort(404)

    sorturls = {key: url_for('main.line_annotations', text_url=text_url,
                             edition_num=edition_num, nums=nums, sort=key) for
                key in sorts.keys()}
    next_page = (url_for('main.edition_annotations', text_url=text.url,
                         edition_num=edition.num, nums=nums, sort=sort,
                         page=annotations.next_num) if annotations.has_next else
                 None)
    prev_page = (url_for('main.line_annotations', text_url=text_url,
                         edition_num=edition.num, nums=nums, sort=sort,
                         page=annotations.prev_num) if annotations.has_prev else
                 None)
    return render_template('indexes/annotation_list.html',
                           title=f"{text.title} {nums} - Annotations",
                           next_page=next_page, prev_page=prev_page,
                           sorts=sorturls, sort=sort,
                           annotations=annotations.items)


@main.route('/read/<text_url>/edition/<edition_num>', methods=['GET', 'POST'])
@main.route('/read/<text_url>', methods=['GET', 'POST'],
            defaults={'edition_num': None})
def read(text_url, edition_num):
    """The main read route for viewing the text of any edition."""
    def underscores_to_ems(lines):
        """Convert all of the underscores to em tags and prepend and
        append em tags based on line.emphasis values. This is to open and close
        any emphasis tags that correspond to underscores that span multiple
        lines. If we *don't* do this, we get all kinds of broken html. And
        that's never fun.

        This method is ten thousand times faster than an actual markdown
        pre-processor. The only thing that would be faster is if I put the
        actual emphasis tags into the database. I may still eventually do that.
        The issue will be when I begin to use char-by-char annotation. That will
        be a headache. I still don't know what the char-by-char highlighting
        will return in javascript. Will it ignore emphasis tags, or include
        them? This will have to be tested.
        """
        us = False
        underscoredict = {True: '</em>', False: '<em>'}
        emdict = {'oem': lambda line: f'{line}</em>',
                  'cem': lambda line: f'<em>{line}',
                  'em': lambda line: f'<em>{line}</em>',
                  'nem': lambda line: line}
        for i, line in enumerate(lines):
            linetext = line.line
            if '_' in linetext:
                newline = []
                for c in linetext:
                    if c == '_':
                        newline.append(underscoredict[us])
                        us = not us
                    else:
                        newline.append(c)
                linetext = ''.join(newline)
                lines[i].line = emdict[line.emphasis](linetext)

    text = Text.get_by_url(text_url).first_or_404()
    edition = text.primary if not edition_num else \
        text.editions.filter_by(num=edition_num).first_or_404()
    form = LineNumberForm()

    if form.validate_on_submit():
        first_line, last_line = line_check(form.first_line.data,
                                           form.last_line.data)
        return redirect(url_for('main.annotate', text_url=text_url,
                                edition_num=edition.num, first_line=first_line,
                                last_line=last_line, next=request.full_path))

    section_strings = tuple(request.args.getlist('section'))
    # Get the section tuple or else all 1's for the deepest possible precedence.
    section = (tuple(int(i) for i in section_strings) if section_strings
               else tuple(1 for i in range(edition.deepest_precedence)))

    lines = edition.section(section).all()
    if not lines:
        abort(404)

    next_section = edition.next_section(section)
    next_page = url_for(
        'main.read', text_url=text_url, edition_num=edition.num,
        section=next_section.section) if next_section else None

    prev_section = edition.prev_section(section)
    prev_page = url_for(
        'main.read', text_url=text_url, edition_num=edition.num,
        section=prev_section.section) if prev_section else None

    annotations = edition.annotations\
        .join(Edit)\
        .filter(Edit.last_line_num<=lines[-1].num,
                Edit.first_line_num>=lines[0].num, Edit.current==True,
                Annotation.active==True).all()

    # index the annotations in a dictionary by the line number.
    annotations_idx = defaultdict(list)
    if annotations:
        for a in annotations:
            annotations_idx[a.HEAD.last_line_num].append(a)

    # This is faster than the markdown plugin
    underscores_to_ems(lines)

    return render_template('read.html', title=text.title, form=form,
                           next_page=next_page, prev_page=prev_page,
                           text=text, edition=edition, lines=lines,
                           section='.'.join(map(str, section)),
                           annotations_idx=annotations_idx)


@main.route('/vote')
@login_required
def vote():
    """This pretty much covers voting! Love it."""
    entity_cls = classes.get(request.args.get('entity'), None)
    entity_id = request.args.get('id').strip(lowercase)
    if not entity_cls:
        abort(404)
    if not issubclass(entity_cls, classes['VotableMixin']):
        abort(501)
    entity = entity_cls.query.get_or_404(entity_id)
    redirect_url = generate_next(entity.url)
    if isinstance(entity, classes['Annotation']) and not entity.active:
        flash("You cannot vote on deactivated annotations.")
        return redirect(redirect_url)
    if isinstance(entity, classes['Edit'])\
            and not entity.annotation.active\
            and not current_user.is_authorized(
                'review_deactivated_annotation_edits'):
            flash("You cannot vote on deactivated annotations edits.")
            return redirect(redirect_url)
    up = True if request.args.get('up').lower() == 'true' else False
    if up:
        entity.upvote(current_user)
    else:
        entity.downvote(current_user)
    db.session.commit()
    return redirect(redirect_url)
