from flask.ext.wtf import Form
from wtforms import TextField, SubmitField
from wtforms.validators import Required


class ListForm(Form):
    name = TextField(u'Name', [Required()])
    submit = SubmitField('Create List')
