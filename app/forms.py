from flask_wtf import FlaskForm
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
    first_line = IntegerField("First Line", validators=[InputRequired()],
            render_kw={"placeholder":"From"})
    last_line = IntegerField("Last Line", validators=[InputRequired()],
            render_kw={"placeholder":"To"})
    submit = SubmitField("Annotate")

class AnnotationForm(FlaskForm):
    first_line = IntegerField("First Line", validators=[InputRequired()])
    last_line = IntegerField("Last Line", validators=[InputRequired()])
    first_char_idx = IntegerField("First Char", validators=[InputRequired()])
    last_char_idx = IntegerField("Last Char", validators=[InputRequired()])

    annotation = TextAreaField("Annotation", 
            render_kw={"placeholder":"Type your annotation here."},
            validators=[InputRequired()])

    tag_1 = StringField("Tag 1", render_kw={"placeholder":"Tag 1"},
            validators=[Optional()])
    tag_2 = StringField("Tag 2", render_kw={"placeholder":"Tag 2"},
            validators=[Optional()])
    tag_3 = StringField("Tag 3", render_kw={"placeholder":"Tag 3"},
            validators=[Optional()])
    tag_4 = StringField("Tag 4", render_kw={"placeholder":"Tag 4"},
            validators=[Optional()])
    tag_5 = StringField("Tag 5", render_kw={"placeholder":"Tag 5"},
            validators=[Optional()])

    submit = SubmitField("Annotate")
    cancel = SubmitField("Cancel")

    def validate_tag_1(self, tag_1):
        tag = Tag.query.filter_by(tag=tag_1.data).first()
        if tag is None:
            raise ValidationError(f"The tag '{tag_1.data}' does not exist.")

    def validate_tag_2(self, tag_2):
        tag = Tag.query.filter_by(tag=tag_2.data).first()
        if tag is None:
            raise ValidationError(f"The tag '{tag_2.data}' does not exist.")

        if tag_2.data == self.tag_1.data:
            raise ValidationError("You cannot use the same tag twice.")

    def validate_tag_3(self, tag_3):
        tag = Tag.query.filter_by(tag=tag_3.data).first()
        if tag is None:
            raise ValidationError(f"The tag '{tag_3.data}' does not exist.")

        if tag_3.data == self.tag_1.data or tag_3.data == self.tag_2.data:
            raise ValidationError("You cannot use the same tag twice.")

    def validate_tag_4(self, tag_4):
        tag = Tag.query.filter_by(tag=tag_4.data).first()
        if tag is None:
            raise ValidationError(f"The tag '{tag_4.data}' does not exist.")

        if tag_4.data == self.tag_1.data or tag_4.data == self.tag_2.data or \
                tag_4.data == self.tag_3.data:
            raise ValidationError("You cannot use the same tag twice.")

    def validate_tag_5(self, tag_5):
        tag = Tag.query.filter_by(tag=tag_5.data).first()
        if tag is None:
            raise ValidationError(f"The tag '{tag_5.data}' does not exist.")

        if tag_5.data == self.tag_1.data or tag_5.data == self.tag_2.data or \
                tag_5.data == self.tag_3.data or tag_5.data == self.tag_4.data:
            raise ValidationError("You cannot use the same tag twice.")

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
