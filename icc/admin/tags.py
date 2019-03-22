"""Administrative routes for tags."""

from flask import render_template, flash, redirect, url_for
from flask_login import login_required

from icc import db
from icc.funky import generate_next, authorize
from icc.admin import admin
from icc.admin.forms import TagForm

from icc.models.request import TagRequest
from icc.models.annotation import Tag


@admin.route('/tags/create/', methods=['GET', 'POST'])
@login_required
@authorize('create_tags')
def create_tag():
    """Create a new tag."""
    tag_request = None
    redirect_url = generate_next(url_for('requests.tag_request_index'))
    form = TagForm()
    if form.validate_on_submit():
        if form.tag.data is not None and form.description.data is not None:
            tag = Tag(tag=form.tag.data, description=form.description.data)
            db.session.add(tag)
            db.session.commit()
            flash("Tag created.")
            return redirect(redirect_url)
    return render_template('forms/tag.html', title="Create Tag", form=form)


@admin.route('/tags/reject/<tag_request_id>/')
@login_required
@authorize('create_tags')
def reject_tag(tag_request_id):
    """Reject a tag request."""
    tag_request = TagRequest.query.get_or_404(tag_request_id)
    redirect_url = generate_next(url_for('requests.tag_request_index'))
    tag_request.rejected = True
    db.session.commit()
    return redirect(redirect_url)
