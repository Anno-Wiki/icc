from flask_wtf import FlaskForm
from flask_login import current_user
from wtforms import StringField, PasswordField, BooleanField, SubmitField, \
        IntegerField, TextAreaField
from wtforms.validators import ValidationError, InputRequired, Email, EqualTo, \
    Optional, URL, Length
from app.models import User, Tag
from flask import request

class LineNumberForm(FlaskForm):
    first_line = IntegerField("First Line", render_kw={"placeholder":"From"},
            validators=[Optional()])
    last_line = IntegerField("Last Line", render_kw={"placeholder":"To"},
            validators=[Optional()])
    submit = SubmitField("Annotate")

class CommentForm(FlaskForm):
    comment = TextAreaField("Comment",
            validators=[InputRequired(), Length(min=10, max=60000)])
    submit = SubmitField("Add Comment")

class AnnotationForm(FlaskForm):
    first_line = IntegerField("First Line", validators=[InputRequired()])
    last_line = IntegerField("Last Line", validators=[InputRequired()])
    first_char_idx = IntegerField("First Char", validators=[InputRequired()])
    last_char_idx = IntegerField("Last Char", validators=[InputRequired()])

    annotation = TextAreaField("Annotation", 
            render_kw={"placeholder":"Type your annotation here.",
                "style":"width: 700px;",
                "maxlength": 60000},
            validators=[InputRequired(), Length(min=0,max=60000)])

    tags = StringField("Tags", 
            render_kw={"placeholder":"e.g. (explanation freudian reference)",
                "autocomplete":"off"}, 
            validators=[Optional()])

    reason = StringField("Reason",
            render_kw={
                "placeholder": 'e.g. "Edited grammar", "Expanded tags", etc.',
                "style": "width: 100%;",
                "maxlength":255
                },
            validators=[Optional(), Length(min=0,max=255)])

    locked = BooleanField("Locked")

    submit = SubmitField("Annotate")

class SearchForm(FlaskForm):
    q = StringField('Search', validators=[InputRequired()])

    def __init__(self, *args, **kwargs):
        if 'formdata' not in kwargs:
            kwargs['formdata'] = request.args
        if 'csrf_enabled' not in kwargs:
            kwargs['csrf_enabled'] = False
        super(SearchForm, self).__init__(*args, **kwargs)

class AreYouSureForm(FlaskForm):
    submit = SubmitField("Yes, I am sure.")
