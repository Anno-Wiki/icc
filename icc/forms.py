"""Forms common to the entire icc web app."""
from flask import request
from flask_wtf import FlaskForm

from wtforms import StringField, SubmitField
from wtforms.validators import InputRequired


class SearchForm(FlaskForm):
    """The search form. This is really only used in one place, but I'm keeping
    it in the common forms for future possible reasons.
    """
    q = StringField('Search', validators=[InputRequired()])

    def __init__(self, *args, **kwargs):
        if 'formdata' not in kwargs:
            kwargs['formdata'] = request.args
        super(SearchForm, self).__init__(*args, **kwargs)


class AreYouSureForm(FlaskForm):
    """A submit button for checking if you're sure."""
    submit = SubmitField("Yes, I am sure.")
