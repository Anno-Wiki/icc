from flask import url_for, flash, redirect, render_template
from flask_login import login_required, current_user

from icc import db
from icc.forms import AreYouSureForm
from icc.admin import admin

from icc.models.request import TextRequest, TagRequest


@admin.route('/request/text/<text_request_id>/delete/', methods=['GET', 'POST'])
@login_required
def delete_text_request(text_request_id):
    form = AreYouSureForm()
    text_request = TextRequest.query.get_or_404(text_request_id)
    if not current_user == text_request.requester:
        current_user.authorize('delete_text_requests')
    redirect_url = url_for('text_request_index')
    if form.validate_on_submit():
        flash(f"Book Request for {text_request.title} deleted.")
        db.session.delete(text_request)
        db.session.commit()
        return redirect(redirect_url)
    text = """If you click submit the text request and all of it's votes will be deleted
permanently."""
    return render_template(
        'forms/delete_check.html', title=f"Delete Book Request", form=form,
        text=text)


@admin.route('/request/tag/<tag_request_id>/delete/', methods=['GET', 'POST'])
@login_required
def delete_tag_request(tag_request_id):
    form = AreYouSureForm()
    tag_request = TagRequest.query.get_or_404(tag_request_id)
    if not current_user == tag_request.requester:
        current_user.authorize('delete_tag_requests')
    redirect_url = url_for('tag_request_index')
    if form.validate_on_submit():
        flash(f"Tag Request for {tag_request.tag} deleted.")
        db.session.delete(tag_request)
        db.session.commit()
        return redirect(redirect_url)
    text = """If you click submit the text request and all of it's votes will be deleted
permanently."""
    return render_template(
        'forms/delete_check.html', title=f"Delete Tag Request", form=form,
        text=text)
