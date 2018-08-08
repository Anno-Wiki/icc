from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, \
        IntegerField, TextAreaField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo
from app.models import User

class PageNumberForm(FlaskForm):
    page_num = IntegerField('Page Number', validators=[DataRequired()])

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class AnnotationForm(FlaskForm):
    book_id = StringField('Book url', validators=[DataRequired()])
    first_line = IntegerField('First Line', validators=[DataRequired()])
    last_line = IntegerField('Last Line', validators=[DataRequired()])
    first_char_idx = IntegerField('First Char', validators=[DataRequired()])
    last_char_idx = IntegerField('Last Char', validators=[DataRequired()])
    annotation = TextAreaField('Annotation')
    tag_1 = StringField('Tag 1')
    tag_2 = StringField('Tag 2')
    tag_3 = StringField('Tag 3')
    tag_4 = StringField('Tag 4')
    tag_5 = StringField('Tag 5')
    submit = SubmitField('Annotate')
