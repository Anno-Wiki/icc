from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, \
        IntegerField, TextAreaField
from wtforms.validators import ValidationError, InputRequired, Email, EqualTo, Optional
from app.models import User

################
## User Forms ##
################
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired()])
    password = PasswordField('Password', validators=[InputRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired()])
    email = StringField('Email', validators=[InputRequired(), Email()])
    password = PasswordField('Password', validators=[InputRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[InputRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

###################
## Content Forms ##
###################
class LineNumberForm(FlaskForm):
    first_line = IntegerField('First Line', validators=[InputRequired()])
    last_line = IntegerField('Last Line', validators=[InputRequired()])
    submit = SubmitField('Annotate')

class AnnotationForm(FlaskForm):
    first_line = IntegerField('First Line', validators=[InputRequired()])
    last_line = IntegerField('Last Line', validators=[InputRequired()])
    first_char_idx = IntegerField('First Char', validators=[InputRequired()])
    last_char_idx = IntegerField('Last Char', validators=[InputRequired()])
    annotation = TextAreaField('Annotation', 
            render_kw={"placeholder":"Type your annotation here."},
            validators=[InputRequired()])
    tag_1 = StringField('Tag 1', validators=[Optional()])
    tag_2 = StringField('Tag 2', validators=[Optional()])
    tag_3 = StringField('Tag 3', validators=[Optional()])
    tag_4 = StringField('Tag 4', validators=[Optional()])
    tag_5 = StringField('Tag 5', validators=[Optional()])
    submit = SubmitField('Annotate')
    cancel = SubmitField('Cancel')
