from flask_wtf import FlaskForm
from flask_login import current_user
from wtforms import StringField, PasswordField, BooleanField, SubmitField, \
        IntegerField, TextAreaField
from wtforms.validators import ValidationError, InputRequired, Email, EqualTo, Optional
from app.models import User, Tag

################
## User Forms ##
################
class LoginForm(FlaskForm):
    username = StringField("Username", validators=[InputRequired()])
    password = PasswordField("Password", validators=[InputRequired()])
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Sign In")

class RegistrationForm(FlaskForm):
    username = StringField("Username", validators=[InputRequired()])
    email = StringField("Email", validators=[InputRequired(), Email()])
    password = PasswordField("Password", validators=[InputRequired()])
    password2 = PasswordField( "Repeat Password", validators=[InputRequired(),
        EqualTo("password")])
    submit = SubmitField("Register")

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError("Please use a different username.")

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError("Please use a different email address.")

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
    line = StringField("Line", validators=[InputRequired()],
            render_kw={"maxlength":200})
    submit = SubmitField("Submit")
    cancel = SubmitField("Cancel")

    def validate_line(self, line):
        if len(line.data) > 200:
            raise ValidationError(f"The maximum length for a line is 200 characters")
