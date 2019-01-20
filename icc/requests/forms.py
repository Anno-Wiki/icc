from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import ValidationError, InputRequired, URL

class TextRequestForm(FlaskForm):
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

    def validate_wikipedia(self, wikipedia):
        if "wikipedia" not in wikipedia.data:
            raise ValidationError(f"{wikipedia.data} is not a link to a Wikipedia page.")

    def validate_gutenberg(self, gutenberg):
        if gutenberg.data != "" and "gutenberg" not in gutenberg.data:
            raise ValidationError(f"{gutenberg.data} is not a link to a Project Gutenberg page.")

class TagRequestForm(FlaskForm):
    tag = StringField("tag", validators=[InputRequired()],
            render_kw={"placeholder":"tag-name"})
    description = TextAreaField("Notes",
            render_kw={"placeholder":"Enter a description of the tag, it’s"
                " significance, and why it belongs on Annopedia."})
    notes = TextAreaField("Notes", 
            render_kw={"placeholder":"Enter notes for special consideration here."})
    wikipedia = StringField("Wikipedia", 
            validators=[URL(require_tld=True), InputRequired()],
            render_kw={"placeholder":"URL to a relevant Wikipedia page."})

    submit = SubmitField("Submit")

    def validate_wikipedia(self, wikipedia):
        if "wikipedia" not in wikipedia.data:
            raise ValidationError(f"{wikipedia.data} is not a link to a Wikipedia page.")
