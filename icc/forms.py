from flask import request
from flask_wtf import FlaskForm

from wtforms import (StringField, SubmitField, IntegerField, TextAreaField,
                     PasswordField, BooleanField)
from wtforms.validators import (ValidationError, InputRequired, Optional,
                                Length, Email, EqualTo)

from icc.models.user import User


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[InputRequired()])
    password = PasswordField("Password", validators=[InputRequired()])
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Sign In")


class RegistrationForm(FlaskForm):
    displayname = StringField("Display Name", validators=[InputRequired()])
    email = StringField("Email", validators=[InputRequired(), Email()])
    password = PasswordField("Password", validators=[InputRequired()])
    password2 = PasswordField("Repeat Password",
                              validators=[InputRequired(), EqualTo("password")])
    submit = SubmitField("Register")

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError("Please use a different email address.")

    # I need to add a log for this sort of event, because it's actually pretty
    # obvious someone is trying to be devious. Also see in EditProfileForm
    def validate_displayname(self, displayname):
        if displayname == "Community":
            raise ValidationError("Community is the only forbidden "
                                  "displayname.")


class LineNumberForm(FlaskForm):
    first_line = IntegerField("First Line", render_kw={'placeholder': "From"},
                              validators=[Optional()])
    last_line = IntegerField("Last Line", render_kw={'placeholder': "To"},
                             validators=[Optional()])
    submit = SubmitField("Annotate")


class CommentForm(FlaskForm):
    comment = TextAreaField("Comment", validators=[InputRequired(),
                                                   Length(min=1, max=60000)])
    submit = SubmitField("Add Comment")


class AnnotationForm(FlaskForm):
    first_line = IntegerField("First Line", validators=[InputRequired()])
    last_line = IntegerField("Last Line", validators=[InputRequired()])
    first_char_idx = IntegerField("First Char", validators=[InputRequired()])
    last_char_idx = IntegerField("Last Char", validators=[InputRequired()])

    annotation = TextAreaField(
        "Annotation", render_kw={'placeholder': "Type your annotation here.",
                                 'style': 'width: 700px;', 'maxlength': 60000},
        validators=[InputRequired(), Length(min=0, max=60000)])

    tags = StringField(
        "Tags",
        render_kw={'placeholder': "e.g. (explanation freudian reference)",
                   'autocomplete': 'off'},
        validators=[Optional()])

    reason = StringField(
        "Reason",
        render_kw={
            'placeholder': "e.g. \"Edited grammar\", \"Expanded tags\", etc.",
            'style': 'width: 100%;', 'maxlength': 191},
        validators=[Optional(), Length(min=0, max=191)])
    submit = SubmitField("Annotate")


class SearchForm(FlaskForm):
    q = StringField('Search', validators=[InputRequired()])

    def __init__(self, *args, **kwargs):
        if 'formdata' not in kwargs:
            kwargs['formdata'] = request.args
        super(SearchForm, self).__init__(*args, **kwargs)


class AreYouSureForm(FlaskForm):
    submit = SubmitField("Yes, I am sure.")


class WikiForm(FlaskForm):
    wiki = TextAreaField("Text", render_kw={'placeholder': "Edit wiki here."})
    reason = StringField(
        "Reason",
        render_kw={
            'placeholder': "e.g. \"Edited grammar\", \"Expanded tags\", etc.",
            'style': 'width: 100%;', 'maxlength': 191},
        validators=[Optional(), Length(min=0, max=191)])
    submit = SubmitField("Submit")
