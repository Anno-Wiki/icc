from flask_wtf import FlaskForm
from flask_login import current_user
from wtforms import StringField, PasswordField, BooleanField, SubmitField, \
        IntegerField, TextAreaField
from wtforms.validators import ValidationError, InputRequired, Email, EqualTo, \
    Optional, URL, Length
from app.models import User, Tag

################
## User Forms ##
################
class LoginForm(FlaskForm):
    email = StringField("Email", validators=[InputRequired()])
    password = PasswordField("Password", validators=[InputRequired()])
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Sign In")

class RegistrationForm(FlaskForm):
    displayname = StringField("Display Name", validators=[InputRequired()])
    email = StringField("Email", validators=[InputRequired(), Email()])
    password = PasswordField("Password", validators=[InputRequired()])
    password2 = PasswordField( "Repeat Password", validators=[InputRequired(),
        EqualTo("password")])
    submit = SubmitField("Register")

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError("Please use a different email address.")

class EditProfileForm(FlaskForm):
    displayname = StringField("Display Name", validators=[InputRequired()],
            render_kw={"placeholder":"Enter a display name."})
    about_me = TextAreaField("About me", validators=[Length(min=0, max=140)],
            render_kw={"placeholder":"Enter a description of yourself.",
                        "maxlength":140})
    submit = SubmitField("Submit")
    cancel = SubmitField("Cancel")

class ResetPasswordRequestForm(FlaskForm):
    email = StringField("Email", validators=[InputRequired(), Email()])
    submit = SubmitField("Request Password Reset")

class ResetPasswordForm(FlaskForm):
    password = PasswordField("Password", validators=[InputRequired()])
    password2 = PasswordField("Repeat Password", validators=[InputRequired(),
        EqualTo("password")])
    submit = SubmitField("Request Password Reset")

###################
## Content Forms ##
###################
class LineNumberForm(FlaskForm):
    first_line = IntegerField("First Line", render_kw={"placeholder":"From"},
            validators=[Optional()])
    last_line = IntegerField("Last Line", render_kw={"placeholder":"To"},
            validators=[Optional()])
    submit = SubmitField("Annotate")

class AnnotationForm(FlaskForm):
    first_line = IntegerField("First Line", validators=[InputRequired()])
    last_line = IntegerField("Last Line", validators=[InputRequired()])
    first_char_idx = IntegerField("First Char", validators=[InputRequired()])
    last_char_idx = IntegerField("Last Char", validators=[InputRequired()])

    annotation = TextAreaField("Annotation", 
            render_kw={"placeholder":"Type your annotation here."},
            validators=[InputRequired()])

    tags = StringField("Tags", render_kw={"placeholder":"e.g. "
        "(explanation freudian reference)"}, validators=[Optional()])

    locked = BooleanField("Locked")

    submit = SubmitField("Annotate")
    cancel = SubmitField("Cancel")


class TagForm(FlaskForm):
    tag = StringField("Tag", render_kw={"placeholder":"Tag"},
            validators=[InputRequired()])
    description = TextAreaField("Description",
            render_kw={"placeholder":"Description"},
            validators=[InputRequired()])
    submit = SubmitField("Submit")
    cancel = SubmitField("Cancel")

    def validate_tag(self, tag):
        tag = Tag.query.filter_by(tag=tag.data).first()
        if tag is not None:
            raise ValidationError("This tag already exists!")

class LineForm(FlaskForm):
    line = StringField("Line", validators=[InputRequired(), 
            Length(min=0, max=140)], render_kw={"maxlength":200})
    submit = SubmitField("Submit")
    cancel = SubmitField("Cancel")

class BookRequestForm(FlaskForm):
    title = StringField("Title", validators=[InputRequired()],
            render_kw={"placeholder":"Title"})
    author = StringField("Author", validators=[InputRequired()],
            render_kw={"placeholder":"Author"})
    notes = TextAreaField("Notes", render_kw={"placeholder":"Enter notes for"
            " special consideration here."})
    description = TextAreaField("Notes", 
            render_kw={"placeholder":"Enter a description of the book, it’s"
                " significance, and why it belongs on Annopedia."})
    wikipedia = StringField("Wikipedia",
            validators=[URL(require_tld=True), InputRequired()],
            render_kw={"placeholder":"URL to Wikipedia page for the book"})
    gutenberg = StringField("Gutenberg", validators=[URL(require_tld=True)],
            render_kw={"placeholder":"URL to Project Gutenberg copy of the book."})

    submit = SubmitField("Submit")
    cancel = SubmitField("Cancel")

    def validate_wikipedia(self, wikipedia):
        if "wikipedia" not in wikipedia.data:
            raise ValidationError(f"{wikipedia.data} is not a link to a Wikipedia page.")

    def validate_gutenberg(self, gutenberg):
        if "gutenberg" not in gutenberg.data:
            raise ValidationError(f"{gutenberg.data} is not a link to a Project Gutenberg page.")

class TagRequestForm(FlaskForm):
    tag = StringField("Title", validators=[InputRequired()],
            render_kw={"placeholder":"Tag Name"})
    notes = TextAreaField("Notes", 
            render_kw={"placeholder":"Enter notes for special consideration here."})
    description = TextAreaField("Notes",
            render_kw={"placeholder":"Enter a description of the book, it’s"
                " significance, and why it belongs on Annopedia."})
    wikipedia = StringField("Wikipedia", 
            validators=[URL(require_tld=True), InputRequired()],
            render_kw={"placeholder":"URL to a relevant Wikipedia page."})

    submit = SubmitField("Submit")
    cancel = SubmitField("Cancel")

    def validate_wikipedia(self, wikipedia):
        if "wikipedia" not in wikipedia.data:
            raise ValidationError(f"{wikipedia.data} is not a link to a Wikipedia page.")

class TextForm(FlaskForm):
    text = TextAreaField("Text",
            render_kw={"placeholder":"Edit text here."})
    submit = SubmitField("Submit")
    cancel = SubmitField("Cancel")
