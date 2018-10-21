from datetime import datetime, date, timedelta
from flask.ext.wtf import Form
from flask import flash
from flask.ext.wtf.html5 import URLField, EmailField, TelField, DateField, DateTimeField
from wtforms import (HiddenField, TextField, SubmitField, IntegerField, SelectField)
from wtforms.validators import (Required, Length, Email, URL, AnyOf, Optional)
from flask.ext.login import current_user
from liaison.models.campaign import Campaign

DT_FORMAT = '%Y-%m-%dT%H:%M'

class NewCampaignForm(Form):
    name = TextField(u'Name', [Required()])
    submit = SubmitField('Create New Campaign')


class CampaignForm(Form):
    name = TextField(u'Name', [Required()])
    list_id = HiddenField("List Id")
    selector_col_name = SelectField('Selector Value', choices=[('', "Please select a list")])
    from_email_dd = SelectField('From Email', choices=[('', "Please select a list")], default='')
    from_email_ov = TextField('From Email')
    from_name_dd = SelectField('From Name', choices=[('', "Please select a list")], default=1)
    from_name_ov = TextField('From Name')
    reply_to_dd = SelectField('Reply-to Email', choices=[('', "Please select a list")], default=1)
    reply_to_ov = TextField('Reply-to Email')
    to_email_dd = SelectField('To Email', choices=[('', "Please select a list")], default=1)
    to_email_ov = TextField('To Email')
    to_name_dd = SelectField('To Name', choices=[('', "Please select a list")], default=1)
    to_name_ov = TextField('To Name')
    submit = SubmitField('Save')


class CampaignListForm(Form):
    list_id = SelectField('List', [Required()])
    submit = SubmitField('Save')


class DispatcherForm(Form):
    send_at = DateTimeField('Date', format=DT_FORMAT)
    submit_send_at = SubmitField('Create Scheduled Send')
    submit_now = SubmitField('Create Send')

    def validate(self):
        return check_send_at_date(self)


class DispatcherConfirmForm(Form):
    send_at = HiddenField("send_at")
    submit_send_at = SubmitField('Send')
    submit_now = SubmitField('Send')

    def validate(self):
        return check_send_at_date(self)


def check_send_at_date(self):
    rv = Form.validate(self)
    if not rv:
        return False

    if self.submit_send_at.data:
        if not self.send_at.data:
            return False
        else:
            td = datetime.utcnow()
            if self.send_at.data <= (td + timedelta(minutes=2)):
                flash('Date must be in the future', 'warning')
                return False
            elif self.send_at.data > (td + timedelta(days=7)):
                flash('Date must be within 7 days', 'warning')
                return False
    return True

