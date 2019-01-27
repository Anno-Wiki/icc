import re
import difflib

from flask import render_template, flash, redirect, url_for, request,\
    current_app
from flask_login import current_user, login_required

from sqlalchemy import and_

from icc import db
from icc.forms import AreYouSureForm
from icc.funky import generate_next, authorize
from icc.admin import admin

from icc.models.wiki import Wiki, WikiEdit, WikiEditVote
from icc.models.user import User



@admin.route('/wiki/edits/review')
@login_required
@authorize('review_wiki_edits')
def wiki_edit_review_queue():
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'voted', type=str)

    if sort == 'voted':
        edits = WikiEdit.query\
            .outerjoin(WikiEditVote,
                       and_(WikiEditVote.voter_id == current_user.id,
                            WikiEditVote.edit_id == WikiEdit.id))\
            .filter(WikiEdit.approved == False, WikiEdit.rejected == False)\
            .order_by(WikiEditVote.delta.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'voted_invert':
        edits = WikiEdit.query\
            .outerjoin(WikiEditVote,
                       and_(WikiEditVote.voter_id == current_user.id,
                            WikiEditVote.edit_id == WikiEdit.id))\
            .filter(WikiEdit.approved == False, WikiEdit.rejected == False)\
            .order_by(WikiEditVote.delta.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'entity':
        edits = WikiEdit.query\
            .outerjoin(Wiki)\
            .filter(WikiEdit.approved == False, WikiEdit.rejected == False)\
            .order_by(Wiki.entity_string.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'entity_invert':
        edits = WikiEdit.query\
            .outerjoin(Wiki)\
            .filter(WikiEdit.approved == False, WikiEdit.rejected == False)\
            .order_by(Wiki.entity_string.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'num':
        edits = WikiEdit.query\
            .filter(WikiEdit.approved == False, WikiEdit.rejected == False)\
            .order_by(WikiEdit.num.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'num_invert':
        edits = WikiEdit.query\
            .filter(WikiEdit.approved == False, WikiEdit.rejected == False)\
            .order_by(WikiEdit.num.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'editor':
        edits = WikiEdit.query\
            .outerjoin(User)\
            .filter(WikiEdit.approved == False, WikiEdit.rejected == False)\
            .order_by(User.displayname.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'editor_invert':
        edits = WikiEdit.query\
            .outerjoin(User)\
            .filter(WikiEdit.approved == False, WikiEdit.rejected == False)\
            .order_by(User.displayname.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'time':
        edits = WikiEdit.query\
            .filter(WikiEdit.approved == False, WikiEdit.rejected == False)\
            .order_by(WikiEdit.timestamp.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'time_invert':
        edits = WikiEdit.query\
            .filter(WikiEdit.approved == False, WikiEdit.rejected == False)\
            .order_by(WikiEdit.timestamp.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'reason':
        edits = WikiEdit.query\
            .filter(WikiEdit.approved == False, WikiEdit.rejected == False)\
            .order_by(WikiEdit.reason.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'reason_invert':
        edits = WikiEdit.query\
            .filter(WikiEdit.approved == False, WikiEdit.rejected == False)\
            .order_by(WikiEdit.reason.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    else:
        edits = WikiEdit.query\
            .outerjoin(WikiEditVote,
                       and_(WikiEditVote.voter_id == current_user.id,
                            WikiEditVote.edit_id == WikiEdit.id))\
            .filter(WikiEdit.approved == False, WikiEdit.rejected == False)\
            .order_by(WikiEditVote.delta.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
        sort = 'voted'

    ids = [edit.id for edit in edits.items]

    votes = current_user.wiki_edit_votes.filter(WikiEdit.id.in_(ids)).all()

    next_page = url_for('admin.wiki_edit_review_queue', page=edits.next_num,
                        sort=sort) if edits.has_next else None
    prev_page = url_for('admin.wiki_edit_review_queue', page=edits.prev_num,
                        sort=sort) if edits.has_prev else None

    return render_template(
        'indexes/wiki_edit_review_queue.html', title="Wiki Edit Review Queue",
        next_page=next_page, prev_page=prev_page, sort=sort, page=page,
        edits=edits.items, votes=votes)


@admin.route('/wiki/<wiki_id>/edit/<edit_id>/review')
@login_required
@authorize('review_wiki_edits')
def review_wiki_edit(wiki_id, edit_id):
    edit = WikiEdit.query.get_or_404(edit_id)
    if edit.approved == True:
        return redirect(url_for('view_wiki_edit', wiki_id=edit.wiki.id,
                                edit_num=edit.num))

    # we have to replace single returns with spaces because markdown only
    # recognizes paragraph separation based on two returns. We also have to be
    # careful to do this for both unix and windows return variants (i.e. be
    # careful of \r's).
    diff1 = re.sub(r'(?<!\n)\r?\n(?![\r\n])', ' ', edit.previous.body)
    diff2 = re.sub(r'(?<!\n)\r?\n(?![\r\n])', ' ', edit.body)

    diff = list(difflib.Differ().compare(diff1.splitlines(),
                                         diff2.splitlines()))

    return render_template(
        'view/wiki_edit_review.html', title=f"Edit number {edit.num}",
        diff=diff, edit=edit)


@admin.route('/wiki/<wiki_id>/edit/<edit_id>/upvote')
@login_required
@authorize('review_wiki_edits')
def upvote_wiki_edit(wiki_id, edit_id):
    redirect_url = generate_next(url_for('index'))
    edit = WikiEdit.query.get(edit_id)
    if edit.approved:
        flash("That wiki edit has already been approved.")
    elif edit.rejected:
        flash("That wiki edit has already been rejected.")
    edit.upvote(current_user)
    db.session.commit()
    return redirect(redirect_url)


@admin.route('/wiki/<wiki_id>/edit/<edit_id>/downvote')
@login_required
@authorize('review_wiki_edits')
def downvote_wiki_edit(wiki_id, edit_id):
    redirect_url = generate_next(url_for('index'))
    edit = WikiEdit.query.get(edit_id)
    if edit.approved:
        flash("That wiki edit has already been approved.")
    elif edit.rejected:
        flash("That wiki edit has already been rejected.")
    edit.downvote(current_user)
    db.session.commit()
    return redirect(redirect_url)


@admin.route('/wiki/edit/<edit_id>/delete', methods=['GET', 'POST'])
@login_required
@authorize('delete_wiki_edits')
def delete_wiki_edit(edit_id):
    form = AreYouSureForm()
    edit = WikiEdit.query.get_or_404(edit_id)
    redirect_url = url_for('wiki_edit_history', wiki_id=edit.wiki.id)
    if form.validate_on_submit():
        if edit.current:
            edit.previous.current = True
        else:
            for e in edit.wiki.edits.order_by(WikiEdit.num.desc()).all():
                if e.num > edit.num:
                    e.num -= 1
        flash(f"Edit #{edit.num} of {str(edit.wiki.entity)} deleted.")
        db.session.delete(edit)
        db.session.commit()
        return redirect(redirect_url)
    text = """If you click submit the edit, all of the votes for the edit, and all of the
reputation changes based on the edit being approved will be deleted. The edit
numbers of all the subsequent edits will be decremented by one. It will
therefore be as though the edit never even existed.

The only reason for this is if there is illegal content in the edit."""
    return render_template(
        'forms/delete_check.html', title=f"Delete wiki edit #{edit.num}",
        form=form, text=text)
