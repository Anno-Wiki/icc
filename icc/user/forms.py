"""Forms specific to the user system."""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField
from wtforms.validators import (ValidationError, InputRequired, Email, EqualTo,
                                Length)


class EditProfileForm(FlaskForm):
    displayname = StringField("Display Name", validators=[InputRequired()],
                              render_kw={
                                  "placeholder": "Enter a display name."})
    about_me = TextAreaField("About me", validators=[Length(min=0, max=140)],
                             render_kw={
                                 "placeholder": "Enter a description of "
                                 "yourself.", "maxlength": 50000})
    submit = SubmitField("Submit")

    def validate_displayname(self, displayname):
        if displayname == "Community":
            raise ValidationError("Community is the only forbidden "
                                  "displayname.")


class ResetPasswordRequestForm(FlaskForm):
    email = StringField("Email", validators=[InputRequired(), Email()])
    submit = SubmitField("Request Password Reset")


class ResetPasswordForm(FlaskForm):
    password = PasswordField("Password", validators=[InputRequired()])
    password2 = PasswordField("Repeat Password",
                              validators=[InputRequired(), EqualTo("password")])
    submit = SubmitField("Request Password Reset")
