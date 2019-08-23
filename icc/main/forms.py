"""Forms for the main system."""
from flask_wtf import FlaskForm

from wtforms import (StringField, SubmitField, PasswordField, BooleanField,
                     IntegerField, TextAreaField)
from wtforms.validators import (ValidationError, InputRequired, Email, EqualTo,
                                Optional, Length)
from icc.models.user import User


class LineNumberForm(FlaskForm):
    """A line number form for use in the read view. To be hidden and quietly
    manipulated when javascript is enabled.
    """
    first_line = IntegerField("First Line", render_kw={'placeholder': "From"},
                              validators=[Optional()])
    last_line = IntegerField("Last Line", render_kw={'placeholder': "To"},
                             validators=[Optional()])
    first_char = IntegerField("First Character",
                              render_kw={'placeholder': "From"},
                             validators=[Optional()])
    last_char = IntegerField("Last Character", render_kw={'placeholder': "To"},
                             validators=[Optional()])
    submit = SubmitField("annotate")


class CommentForm(FlaskForm):
    """A simple comment form."""
    comment = TextAreaField("Comment", validators=[InputRequired(),
                                                   Length(min=1, max=60000)])
    submit = SubmitField("Post")


class AnnotationForm(FlaskForm):
    """A form to write and edit annotations."""
    first_line = IntegerField("First Line", validators=[InputRequired()])
    last_line = IntegerField("Last Line", validators=[InputRequired()])
    first_char_idx = IntegerField("First Char", validators=[InputRequired()])
    last_char_idx = IntegerField("Last Char", validators=[InputRequired()])

    annotation = TextAreaField(
        "Annotation", render_kw={'placeholder': "Type your annotation here.",
                                 'maxlength': 60000},
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
            'maxlength': 191},
        validators=[Optional(), Length(min=0, max=191)])
    submit = SubmitField("Annotate")


class WikiForm(FlaskForm):
    """A form for editing wikis."""
    wiki = TextAreaField("Text", render_kw={'placeholder': "Edit wiki here."})
    reason = StringField(
        "Reason",
        render_kw={
            'placeholder': "e.g. \"Edited grammar\", \"Expanded tags\", etc.",
            'style': 'width: 100%;', 'maxlength': 191},
        validators=[Optional(), Length(min=0, max=191)])
    submit = SubmitField("Submit")


class LoginForm(FlaskForm):
    """A login form."""
    email = StringField("Email", validators=[InputRequired()])
    password = PasswordField("Password", validators=[InputRequired()])
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Sign In")


class RegistrationForm(FlaskForm):
    """A registration form."""
    displayname = StringField("Display Name", validators=[InputRequired()])
    email = StringField("Email", validators=[InputRequired(), Email()])
    password = PasswordField("Password", validators=[InputRequired()])
    password2 = PasswordField("Repeat Password",
                              validators=[InputRequired(), EqualTo("password")])
    honeypot = StringField("Website", render_kw={'style': 'display: none;'})
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
