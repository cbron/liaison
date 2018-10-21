import pystache
import urllib
from flask import current_app
from sqlalchemy import Column
from sqlalchemy.orm import relationship
from pystache.context import KeyNotFoundError

from liaison.lib.extensions import db
from liaison.lib.constants import STRING_LEN
from liaison.models.list import List
from basemodel import BaseMixin


class Email(db.Model, BaseMixin):
    __tablename__ = 'emails'

    id = Column(db.Integer, primary_key=True)
    account_id = Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    selector_col_val = Column(db.String(STRING_LEN))
    name = Column(db.String(STRING_LEN), nullable=False)
    subject = Column(db.String(STRING_LEN), nullable=True)
    preheader = Column(db.String(STRING_LEN))
    html = Column(db.Text())
    text = Column(db.Text())
    created_at = Column(db.DateTime(timezone=True),  default=db.func.now())
    modified_at = Column(db.DateTime(timezone=True), default=db.func.now(), onupdate=db.func.now())
    account = relationship("Account",
        primaryjoin="Account.id==Email.account_id",
        foreign_keys="Email.account_id")
    campaign_id = Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False)
    campaign = relationship("Campaign",
        primaryjoin="Campaign.id==Email.campaign_id",
        foreign_keys="Email.campaign_id")
    sends = relationship("Send",
        primaryjoin="Email.id==Send.email_id",
        foreign_keys="Send.email_id")


    def full_html(self):
        footer = self.account.footer_html
        html = self.html
        if footer or self.preheader:
            soup = BeautifulSoup(html)
            if soup.body:
                if footer:
                    soup.body.append(BeautifulSoup(footer))
                if self.preheader:
                    preheader = "<span class='preheader'>%s</span>" % self.preheader
                    soup.body.insert(0, preheader)
                html = unicode(soup.html)
            else:
                if footer:
                    html = "%s<br>%s" % (html,footer)
                if self.preheader:
                    preheader = "<span class='preheader'>%s</span>" % self.preheader
                    html = preheader + html
        return urllib.unquote(html)


    def full_text(self):
        footer = self.account.footer_text
        text = self.text
        if footer:
            text = "%s\n\n%s" % (text,footer)
        return urllib.unquote(text)


    def render_html_attr(self, data, hash_id):
        data = Email.add_additional_data(data, hash_id)
        html = self.full_html()
        return pystache.render(html, data)


    def render_text_attr(self, data, hash_id):
        data = Email.add_additional_data(data, hash_id)
        text = self.full_text()
        return pystache.render(text, data)


    def check_keys(self, list_id):
        list_ = List.find_by_id_anon(list_id)
        keys = list_.random_data_sample(1)[0]
        renderer = pystache.Renderer(missing_tags='strict')
        try:
            renderer.render(self.html, keys)
            return True, None
        except KeyNotFoundError, e:
            return False, e.key


    @classmethod
    def view_in_browser_link(cls, hash_id):
        return '%s/pf/vib/%s' % (current_app.config.get('EXTERNAL_VIEW_URL'), hash_id)


    @classmethod
    def unsubscribe_link(cls, hash_id):
        return '%s/pf/unsubscribe/%s' % (current_app.config.get('EXTERNAL_VIEW_URL'), hash_id)


    @classmethod
    def add_additional_data(cls, data, hash_id):
        data["VIEW_IN_BROWSER_LINK"] = Email.view_in_browser_link(hash_id)
        data["UNSUBSCRIBE_LINK"] = Email.unsubscribe_link(hash_id)
        return data

