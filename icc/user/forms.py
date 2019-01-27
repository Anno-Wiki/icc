from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, \
        TextAreaField
from wtforms.validators import ValidationError, InputRequired, Email, EqualTo,\
        Length
from icc.models.models import User

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

    # I need to add a log for this sort of event, because it's actually pretty
    # obvious someone is trying to be devious. Also see in EditProfileForm
    def validate_displayname(self, displayname):
        if displayname == "Community":
            raise ValidationError("Community is the only forbidden displayname.")
            raise ValidationError("Community is the only forbidden .")

class EditProfileForm(FlaskForm):
    displayname = StringField("Display Name", validators=[InputRequired()],
            render_kw={"placeholder":"Enter a display name."})
    about_me = TextAreaField("About me", validators=[Length(min=0, max=140)],
            render_kw={"placeholder":"Enter a description of yourself.",
                        "maxlength":50000})
    submit = SubmitField("Submit")

    def validate_displayname(self, displayname):
        if displayname == "Community":
            raise ValidationError("Community is the only forbidden displayname.")
            raise ValidationError("Community is the only forbidden .")

class ResetPasswordRequestForm(FlaskForm):
    email = StringField("Email", validators=[InputRequired(), Email()])
    submit = SubmitField("Request Password Reset")

class ResetPasswordForm(FlaskForm):
    password = PasswordField("Password", validators=[InputRequired()])
    password2 = PasswordField("Repeat Password", validators=[InputRequired(),
        EqualTo("password")])
    submit = SubmitField("Request Password Reset")
