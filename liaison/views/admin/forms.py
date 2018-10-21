from flask.ext.wtf import Form
from wtforms import SubmitField

class EndToEndForm(Form):
    submit = SubmitField('Run Test')
