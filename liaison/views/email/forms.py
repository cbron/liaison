from flask.ext.wtf import Form
from wtforms import (ValidationError, HiddenField, TextField,
        SubmitField, TextAreaField, SelectMultipleField)
from wtforms.validators import Required


class NewEmailForm(Form):
    name = TextField(u'Name', [Required()])
    subject = TextField('Subject')
    preheader = TextField('Pre-Header')
    template = HiddenField()
    selector_col_val = SelectMultipleField('Selector Value', choices=[('', "Please select a value")])
    submit = SubmitField('Save')


class EditEmailForm(Form):
    name = TextField(u'Name', [Required()])
    subject = TextField('Subject')
    preheader = TextField('Pre-Header')
    selector_col_val = SelectMultipleField('Selector Value', choices=[('', "Please select a value")])
    html = TextAreaField('Body')
    text = TextAreaField('Text')
    submit = SubmitField('Save')
