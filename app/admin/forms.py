from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import ValidationError, InputRequired, Length
from app.models import Tag

class TagForm(FlaskForm):
    tag = StringField("Tag", render_kw={"placeholder":"Tag"},
            validators=[InputRequired()])
    description = TextAreaField("Description",
            render_kw={"placeholder":"Description"},
            validators=[InputRequired()])
    submit = SubmitField("Submit")

    def validate_tag(self, tag):
        tag = Tag.query.filter_by(tag=tag.data).first()
        if tag is not None and self.description == tag.description:
            raise ValidationError("This tag already exists!")

class LineForm(FlaskForm):
    line = StringField("Line", validators=[InputRequired(), 
            Length(min=0, max=140)], render_kw={"maxlength":200})
    submit = SubmitField("Submit")

class TextForm(FlaskForm):
    text = TextAreaField("Text",
            render_kw={"placeholder":"Edit text here."})
    submit = SubmitField("Submit")
