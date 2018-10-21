import json
from sqlalchemy import Column
from sqlalchemy.orm import relationship
import pystache
from liaison.lib.extensions import db
from liaison.lib.constants import STRING_LEN
from liaison.lib.utils import get_cache, set_cache
from basemodel import BaseMixin


class Campaign(db.Model, BaseMixin):
    __tablename__ = 'campaigns'

    id = Column(db.Integer, primary_key=True)
    name = Column(db.String(STRING_LEN), nullable=False)
    account_id = Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    selector_col_name = Column(db.String(STRING_LEN))
    from_email_dd = Column(db.String(STRING_LEN)) # dd = dynamic data
    from_name_dd = Column(db.String(STRING_LEN))
    reply_to_dd = Column(db.String(STRING_LEN))
    to_email_dd = Column(db.String(STRING_LEN))
    to_name_dd = Column(db.String(STRING_LEN))
    from_email_ov = Column(db.String(STRING_LEN)) # ov = overwrite
    from_name_ov = Column(db.String(STRING_LEN))
    reply_to_ov = Column(db.String(STRING_LEN))
    to_email_ov = Column(db.String(STRING_LEN))
    to_name_ov = Column(db.String(STRING_LEN))
    created_at = Column(db.DateTime(timezone=True),  default=db.func.now())
    modified_at = Column(db.DateTime(timezone=True), default=db.func.now(), onupdate=db.func.now())
    account = relationship("Account",
        primaryjoin="Account.id==Campaign.account_id",
        foreign_keys="Campaign.account_id")
    list_id = Column(db.Integer)
    list_ = relationship("List",
        primaryjoin="List.id==Campaign.list_id",
        foreign_keys="Campaign.list_id")
    emails = relationship("Email",
        primaryjoin="Campaign.id==Email.campaign_id",
        foreign_keys="Email.campaign_id")
    dispatcher = relationship("Dispatcher",
        primaryjoin="Campaign.id==Dispatcher.campaign_id",
        foreign_keys="Dispatcher.campaign_id")


    def __repr__ (self):
        return '<Campaign: %s - %s>' % (self.id, self.name)


    def check_email_keys(self):
        for email in self.emails:
            valid, bad_key = email.check_keys(self.list_id)
            if not valid:
                return False, bad_key
        return True, None


    def render_attr(self, attr, data):
        return pystache.render("{{ %s }}" % getattr(self, attr), data)


    def email_determiner(self, data):
        ''' Find which of the campaign's email's this data runs with
            returns first one found
        '''
        if self.selector_col_name and len(self.selector_col_name) > 0:
            col_name_val = data.get(self.selector_col_name)
            if col_name_val and len(col_name_val) > 0:
                for email in self.emails:
                    if email.selector_col_val:
                        vals = json.loads(email.selector_col_val)
                        for val in vals:
                            if val and len(val) > 0 and col_name_val == val:
                                return email
        else:
            return self.emails[0] if len(self.emails) else None


    def get_selector_import_data(self):
        selector_data = []
        for data in self.list_.import_data:
            if self.email_determiner(data):
                selector_data.append(data)
        return selector_data


    def selector_send_count(self):
        key = 'selector_send_count_%s' % self.id
        val = get_cache(key)
        if val:
            return val
        else:
            count = 0
            for data in self.list_.import_data:
                if self.email_determiner(data):
                    count = count + 1
            set_cache(key, count, 10)
            return count


    def determiner_duplicates(self):
        ''' Used so one person doesn't get multiple emails.
            Returns (True, val) if dups or (false, None) if its ok.
        '''
        values = []
        for email in self.emails:
            if email.selector_col_val:
                vals = json.loads(email.selector_col_val)
                for val in vals:
                    if val and val in values:
                        return True,val
                    else:
                        values.append(val)
        return False, None


    def selector_missing(self):
        if len(self.emails) > 1 and not self.selector_col_name:
            return True
        return False
