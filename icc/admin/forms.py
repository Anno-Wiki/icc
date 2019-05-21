"""Forms specific to the admin module."""
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import ValidationError, InputRequired, Length, Email

from icc.models.annotation import Tag


class TagForm(FlaskForm):
    """A form to create a tag."""
    tag = StringField('Tag', render_kw={'placeholder': 'Tag'},
                      validators=[InputRequired()])
    description = TextAreaField('Description',
                                render_kw={'placeholder': 'Description'},
                                validators=[InputRequired()])
    submit = SubmitField('Submit')

    def validate_tag(self, tag):
        tag = Tag.query.filter_by(tag=tag.data).first()
        if tag is not None and self.description == tag.description:
            raise ValidationError("This tag already exists!")


class LineForm(FlaskForm):
    """A form to edit a line."""
    line = StringField('Line',
                       validators=[InputRequired(), Length(min=0, max=140)],
                       render_kw={'maxlength': 200})
    submit = SubmitField('Submit')


class InviteForm(FlaskForm):
    """A form for an admin to beta invite a user."""
    email = StringField('Email', validators=[InputRequired(), Email()])
    submit = SubmitField('Submit')
