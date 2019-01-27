import re
import difflib

from flask import (render_template, flash, redirect, url_for, request,
                   current_app)
from flask_login import current_user, login_required

from sqlalchemy import and_

from icc import db
from icc.funky import authorize
from icc.admin import admin

from icc.models.annotation import Edit, EditVote, Annotation
from icc.models.user import User


@admin.route('/annotation/edits/review')
@login_required
@authorize('review_edits')
def edit_review_queue():
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'voted', type=str)

    if sort == 'voted':
        edits = Edit.query\
            .outerjoin(EditVote, and_(EditVote.voter_id == current_user.id,
                                      EditVote.edit_id == Edit.id))\
            .filter(Edit.approved == False, Edit.rejected == False)\
            .order_by(EditVote.delta.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'voted_invert':
        edits = Edit.query\
            .outerjoin(EditVote, and_(EditVote.voter_id == current_user.id,
                                      EditVote.edit_id == Edit.id))\
            .filter(Edit.approved == False, Edit.rejected == False)\
            .order_by(EditVote.delta.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'id':
        edits = Edit.query.outerjoin(Annotation)\
            .filter(Edit.approved == False, Edit.rejected == False)\
            .order_by(Annotation.id.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'id_invert':
        edits = Edit.query.outerjoin(Annotation)\
            .filter(Edit.approved == False, Edit.rejected == False)\
            .order_by(Annotation.id.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'edit_num':
        edits = Edit.query\
            .filter(Edit.approved == False, Edit.rejected == False)\
            .order_by(Edit.num.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'edit_num_invert':
        edits = Edit.query\
            .filter(Edit.approved == False, Edit.rejected == False)\
            .order_by(Edit.num.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'editor':
        edits = Edit.query.outerjoin(User)\
            .filter(Edit.approved == False, Edit.rejected == False)\
            .order_by(User.displayname.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'editor_invert':
        edits = Edit.query.outerjoin(User)\
            .filter(Edit.approved == False, Edit.rejected == False)\
            .order_by(User.displayname.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'time':
        edits = Edit.query\
            .filter(Edit.approved == False, Edit.rejected == False)\
            .order_by(Edit.timestamp.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'time_invert':
        edits = Edit.query\
            .filter(Edit.approved == False, Edit.rejected == False)\
            .order_by(Edit.timestamp.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'reason':
        edits = Edit.query\
            .filter(Edit.approved == False, Edit.rejected == False)\
            .order_by(Edit.reason.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'reason_invert':
        edits = Edit.query\
            .filter(Edit.approved == False, Edit.rejected == False)\
            .order_by(Edit.reason.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    else:
        edits = Edit.query\
            .outerjoin(EditVote, and_(EditVote.voter_id == current_user.id,
                                      EditVote.edit_id == Edit.id))\
            .filter(Edit.approved == False, Edit.rejected == False)\
            .order_by(EditVote.delta.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
        sort = 'voted'

    votes = current_user.edit_votes

    next_page = url_for('admin.edit_review_queue', page=edits.next_num,
                        sort=sort) if edits.has_next else None
    prev_page = url_for('admin.edit_review_queue', page=edits.prev_num,
                        sort=sort) if edits.has_prev else None

    return render_template(
        'indexes/edit_review_queue.html', title="Edit Review Queue",
        next_page=next_page, prev_page=prev_page, sort=sort, edits=edits.items,
        votes=votes)


@admin.route('/annotation/<annotation_id>/edit/<edit_id>/review')
@login_required
@authorize('review_edits')
def review_edit(annotation_id, edit_id):
    edit = Edit.query.get_or_404(edit_id)
    if edit.approved == True:
        return redirect(url_for('view_edit', annotation_id=edit.annotation_id,
                                num=edit.num))
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


@admin.route('/annotation/<annotation_id>/edit/<edit_id>/upvote')
@login_required
@authorize('review_edits')
def upvote_edit(annotation_id, edit_id):
    edit = Edit.query.get_or_404(edit_id)
    if not edit.annotation.active:
        current_user.authorize('review_deactivated_annotation_edits')
    elif edit.editor == current_user:
        flash("You cannot approve or reject your own edits")
        return redirect(url_for('admin.edit_review_queue'))
    edit.upvote(current_user)
    db.session.commit()
    return redirect(url_for('admin.edit_review_queue'))


@admin.route('/annotation/<annotation_id>/edit/<edit_id>/downvote')
@login_required
@authorize('review_edits')
def downvote_edit(annotation_id, edit_id):
    edit = Edit.query.get_or_404(edit_id)
    if not edit.annotation.active:
        current_user.authorize('review_deactivated_annotation_edits')
    elif edit.editor == current_user:
        flash("You cannot approve or reject your own edits")
        return redirect(url_for('admin.edit_review_queue'))
    edit.downvote(current_user)
    db.session.commit()
    return redirect(url_for('admin.edit_review_queue'))
