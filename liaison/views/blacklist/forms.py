from flask.ext.wtf import Form
from wtforms import TextField, SubmitField
from wtforms.validators import Required

class BlacklistForm(Form):
    name = TextField(u'Name', [Required()])
    submit = SubmitField('Upload list')
