"""Administrative routes for edits."""

import re
import difflib

from flask import (render_template, flash, redirect, url_for, request,
                   current_app, abort)
from flask_login import current_user, login_required

from icc import db
from icc.funky import authorize, generate_next
from icc.admin import admin
from icc.forms import AreYouSureForm

from icc.models.annotation import Edit, EditVote, Annotation
from icc.models.user import User


@admin.route('/annotation/edits/review')
@login_required
@authorize('review_edits')
def edit_review_queue():
    """The edit review queue. This is one of the chief moderation routes."""
    default = 'voted'
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', default, type=str)

    sorts = {
        'voted': Edit.query.outerjoin(EditVote).order_by(EditVote.delta.desc()),
        'annotation': Edit.query.join(Annotation).order_by(Annotation.id.asc()),
        'number': Edit.query.order_by(Edit.num.asc()),
        'editor': Edit.query.join(User).order_by(User.displayname.asc()),
        'time': Edit.query.order_by(Edit.timestamp.asc()),
    }

    sort = sort if sort in sorts else default
    edits = (sorts[sort].filter(Edit.approved==False, Edit.rejected==False)
             .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'],
                       False))

    if not edits.items and page > 1:
        abort(404)

    sorturls = {key: url_for('admin.edit_review_queue', sort=key) for key in
                sorts.keys()}
    next_page = url_for('admin.edit_review_queue', page=edits.next_num,
                        sort=sort) if edits.has_next else None
    prev_page = url_for('admin.edit_review_queue', page=edits.prev_num,
                        sort=sort) if edits.has_prev else None
    return render_template('indexes/edit_review_queue.html',
                           title="Edit Review Queue",
                           next_page=next_page, prev_page=prev_page,
                           sort=sort, sorts=sorturls,
                           edits=edits.items)


@admin.route('/annotation/<annotation_id>/edit/<edit_id>/review')
@login_required
@authorize('review_edits')
def review_edit(annotation_id, edit_id):
    """Review an edit. This, with the queue, are the chief moderation routes."""
    edit = Edit.query.get_or_404(edit_id)
    if edit.approved == True:
        return redirect(edit.url)
    if not edit.annotation.active:
        current_user.authorize('review_deactivated_annotation_edits')

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

    return render_template('view/edit_review.html',
                           title=f"[{edit.annotation.id}] Edit #{edit.num}",
                           diff=diff, edit=edit, tags=tags, context=context)


@admin.route('/edit/<edit_id>/delete/', methods=['GET', 'POST'])
@login_required
@authorize('delete_annotations')
def delete_edit(edit_id):
    """This annotation is to delete an *edit* to an annotation because it
    contains illegal content.
    """
    form = AreYouSureForm()
    edit = Edit.query.get_or_404(edit_id)
    redirect_url = generate_next(url_for('main.edit_history',
                                         annotation_id=edit.annotation_id))
    if form.validate_on_submit():
        if edit.current:
            edit.previous.current = True
        else:
            for e in edit.annotation.all_edits.order_by(Edit.num.desc()).all():
                if e.num > edit.num:
                    e.num -= 1
        flash(f"Edit #{edit.num} of [{edit.annotation_id}] deleted.")
        db.session.delete(edit)
        db.session.commit()
        return redirect(redirect_url)
    text = """If you click submit the edit, all of the votes for the edit, and
    all of the reputation changes based on the edit being approved will be
    deleted. The edit numbers of all the subsequent edits will be decremented by
    one. It will therefore be as though the edit never even existed.

    The only reason for this is if there is illegal content in the edit.
    """
    return render_template('forms/delete_check.html',
                           title=f"Delete edit #{edit.num} of "
                           f"[{edit.annotation_id}]",
                           form=form,
                           text=text)
