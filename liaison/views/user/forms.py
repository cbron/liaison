from flask.ext.wtf import Form
from flask.ext.wtf.html5 import EmailField, TelField
from wtforms import ValidationError, TextField, SubmitField
from wtforms.validators import Required, Length, Email


class ProfileForm(Form):
    email = EmailField(u'Email', [Required(), Email()])
    first_name = TextField(u'First Name', [Required()])
    last_name = TextField(u'Last Name', [Required()])
    phone = TelField(u'Phone', [Length(max=64)])
    submit = SubmitField(u'Save')

class SubscribeForm(Form):
    email = EmailField(u'Email', [Required(), Email()])
    submit = SubmitField(u'Submit')

class EulaForm(Form):
    submit = SubmitField(u'I Accept')
