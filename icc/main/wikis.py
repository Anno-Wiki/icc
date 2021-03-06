"""The main routes for wikis."""
import re
import difflib

from flask import (render_template, flash, redirect, url_for, request,
                   current_app)
from flask_login import current_user, login_required

from icc import db
from icc.main import main

from icc.models.wiki import Wiki, WikiEdit
from icc.models.user import User

from icc.main.forms import WikiForm
from icc.funky import generate_next


@main.route('/wiki/<wiki_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_wiki(wiki_id):
    """Edit a wiki."""
    form = WikiForm()
    wiki = Wiki.query.get_or_404(wiki_id)
    redirect_url = generate_next(wiki.entity.url)

    if wiki.edit_pending:
        flash("That wiki is locked from a pending edit.")
        return redirect(redirect_url)
    if form.validate_on_submit():
        wiki.edit(current_user, body=form.wiki.data, reason=form.reason.data)
        db.session.commit()
        return redirect(redirect_url)

    form.wiki.data = wiki.current.body
    return render_template('forms/wiki.html', title="Edit wiki", form=form,
                           wiki=wiki)


@main.route('/wiki/<wiki_id>/history')
def wiki_edit_history(wiki_id):
    """The edit history for a given wiki."""
    default = 'number'
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', default, type=str)
    wiki = Wiki.query.get_or_404(wiki_id)

    sorts = {
        'number': wiki.edits.order_by(WikiEdit.num.desc()),
        'time': wiki.edits.order_by(WikiEdit.timestamp.desc()),
        'editor': wiki.edits.join(User).order_by(User.displayname.asc()),
        'reason': wiki.edits.order_by(WikiEdit.reason.asc()),
    }

    sort = sort if sort in sorts else default
    edits = sorts[sort].filter(WikiEdit.approved==True)\
        .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)

    sorturls = {key: url_for('main.wiki_edit_history', wiki_id=wiki_id,
                             sort=key) for key in sorts.keys()}
    next_page = (url_for('main.wiki_edit_history', page=edits.next_num,
                         sort=sort) if edits.has_next else None)
    prev_page = (url_for('main.wiki_edit_history', page=edits.prev_num,
                         sort=sort) if edits.has_prev else None)
    return render_template('indexes/wiki_edits.html',
                           title=f"{str(wiki.entity)} Edit History",
                           next_page=next_page, prev_page=prev_page,
                           sorts=sorturls, sort=sort,
                           wiki=wiki, edits=edits.items)


@main.route('/wiki/<wiki_id>/edit/<num>')
def view_wiki_edit(wiki_id, num):
    """The diff page for a wiki edit in comparison to it's previous version. For
    the first version we use a special template.
    """
    wiki = Wiki.query.get_or_404(wiki_id)
    edit = wiki.edits\
        .filter(WikiEdit.approved==True,
                WikiEdit.num==num).first_or_404()

    if not edit.previous:
        return render_template(
            'view/wiki_first_version.html',
            title=f"First Version of {str(edit.wiki.entity)} wiki", edit=edit)

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
