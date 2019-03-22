"""Grab bag of uncategorizable routes."""
from flask import render_template, flash, redirect
from flask_login import login_required

from icc import db
from icc.funky import generate_next, authorize
from icc.admin import admin
from icc.admin.forms import LineForm

from icc.models.content import Line


@admin.route('/edit/line/<line_id>/', methods=['GET', 'POST'])
@login_required
@authorize('edit_lines')
def edit_line(line_id):
    """Edit a line. Purely for administrators. Perhaps to be made more robust.
    """
    line = Line.query.get_or_404(line_id)
    form = LineForm()
    redirect_url = generate_next(line.url)
    if form.validate_on_submit() and form.line.data is not None:
        line.line = form.line.data
        db.session.commit()
        flash("Line updated.")
        return redirect(redirect_url)
    form.line.data = line.line
    return render_template('forms/line.html', title="Edit Line", form=form)
