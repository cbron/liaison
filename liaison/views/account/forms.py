from flask.ext.wtf import Form
from flask.ext.wtf.html5 import EmailField
from wtforms import SubmitField, TextAreaField
from wtforms.validators import Required, Email, Optional

class FooterForm(Form):
    footer_html = TextAreaField(u'Footer', [Required()])
    footer_text = TextAreaField(u'Footer', [Optional()])
    submit = SubmitField('Save')

    def validate(self):
        rv = Form.validate(self)
        if not rv:
            return False

        if not (("{{ UNSUBSCRIBE_LINK" in self.footer_html.data) or ("{{UNSUBSCRIBE_LINK" in self.footer_html.data) \
            or ("%7B%7B%20UNSUBSCRIBE_LINK" in self.footer_html.data) or ("%7B%7BUNSUBSCRIBE_LINK" in self.footer_html.data)):
            self.footer_html.errors.append('You must include the {{ UNSUBSCRIBE_LINK }} tag in your footer.')
            return False

        return True


class DefaultFromEmail(Form):
    default_from_email = EmailField(u'Default From Email', [Optional(), Email()])
    submit = SubmitField('Save')
