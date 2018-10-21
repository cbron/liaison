from flask import current_app
from sqlalchemy import Column
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSON
import mandrill

from basemodel import BaseMixin
from liaison.lib.extensions import db
from liaison.lib.constants import STRING_LEN
from liaison.models.unsubscribe import Unsubscribe
from liaison.models.blacklist import Blacklist


class Send(db.Model, BaseMixin):
    __tablename__ = 'sends'

    id = Column(db.Integer, primary_key=True)
    hash_id = Column(db.String, index=True, unique=True)
    email_id = Column(db.Integer, db.ForeignKey('emails.id'), nullable=False)
    account_id = Column(db.Integer, db.ForeignKey('accounts.id'))
    dispatcher_id = Column(db.Integer, db.ForeignKey('dispatches.id'))
    data = Column(JSON) # from csv
    message = Column(JSON) # dynamically generated api request sent to mandril
    result = Column(JSON) #  result from mandril
    status = Column(db.String)
    state = Column(db.Integer, default=0)
    attempts = Column(db.Integer, default=0)
    created_at = Column(db.DateTime(timezone=True),  default=db.func.now())
    modified_at = Column(db.DateTime(timezone=True), default=db.func.now(), onupdate=db.func.now())
    account = relationship("Account",
        primaryjoin="Account.id==Send.account_id",
        foreign_keys="Send.account_id")
    email = relationship("Email",
        primaryjoin="Email.id==Send.email_id",
        foreign_keys="Send.email_id")
    dispatcher = relationship("Dispatcher",
        primaryjoin="Dispatcher.id==Send.dispatcher_id",
        foreign_keys="Send.dispatcher_id")

    # Send result
    STATES = {
        0: 'unsent',
        1: 'success',
        2: 'error',
        3: 'rejected',
        4: 'invalid',
        5: 'queued',
        6: 'unsubscribed',
        7: 'blacklisted',
        8: 'bad to_email',
        9: 'unknown',
        103: 'no hash_id'
    }

    def current_state(self):
        return self.STATES.get(self.state) if self.STATES.get(self.state) else ''

    @classmethod
    def find_by_hash(cls, hash_id):
        return cls.query.filter(cls.hash_id==str(hash_id)).first()


    @classmethod
    def hash_exists(cls, hash_id):
        return cls.query.with_entities(cls.id).filter(cls.hash_id==hash_id).first()

    @classmethod
    def delete_old_sends(cls):
        # TODO, delete sends over 2 months old
        pass


    def process(self):
        ''' the actual send '''

        self.update(attempts=self.attempts+1)
        if self.attempts == 1:
            self.dispatcher.incr_sent()

        if self.state == 0 or self.state == 2:
            try:
                if not self.hash_id:
                    self.update(state=103)
                else:
                    campaign = self.dispatcher.campaign
                    data = self.data
                    to_email = campaign.to_email_ov if campaign.to_email_ov else campaign.render_attr('to_email_dd', data)
                    if Unsubscribe.check(self.account_id, to_email):
                        self.update(state=6) #they already unsubscribed
                    elif Blacklist.check(self.account_id, to_email):
                        self.update(state=7) #they are blacklisted
                    elif not to_email or len(to_email) < 6:
                        self.update(state=8)
                    else:
                        email = self.email
                        from_email = campaign.from_email_ov if campaign.from_email_ov else campaign.render_attr('from_email_dd', data)
                        from_name = campaign.from_name_ov if campaign.from_name_ov else campaign.render_attr('from_name_dd', data)
                        auto_text = self.account.auto_text
                        message = {
                            "html": email.render_html_attr(data, data['hash_id']),
                            "subject": email.subject,
                            "from_email": from_email,
                            "from_name": from_name,
                            "to": [{
                                "email": to_email,
                                "name": campaign.to_name_ov if campaign.to_name_ov else campaign.render_attr('to_name_dd', data),
                                "type": "to"
                            }],
                            'headers': {
                                "Reply-To": campaign.reply_to_ov if campaign.reply_to_ov else campaign.render_attr('reply_to_dd', data)
                            },
                            'important': False,
                            'track_opens': True,
                            'track_clicks': True,
                            "auto_text": auto_text,
                            "auto_html": False,
                            "inline_css": False,
                            "url_strip_qs": False,
                            "preserve_recipients": False,
                            "view_content_link": False,
                            "signing_domain": self.account.domain,
                            "merge": False,
                            "metadata": {
                                "hash_id": self.hash_id,
                                "dispatcher_id": self.dispatcher_id
                            },
                            "recipient_metadata": [{
                                "rcpt": to_email
                            }]
                        }
                        if not auto_text:
                            message['text'] = email.render_text_attr(data, data['hash_id'])

                        if not current_app.debug:
                            mc = mandrill.Mandrill(self.account.api_key)
                            self.result = mc.messages.send(message=message, async=False, ip_pool=self.account.ip_pool())
                            self.status = self.result[0].get('status') if (self.result and self.result[0]) else None

                            if self.status == 'sent':
                                self.state = 1
                            elif self.status == 'rejected':
                                self.state = 3
                            elif self.status == 'invalid':
                                self.state = 4
                            elif self.status == 'queued' or self.status == 'scheduled':
                                self.state = 5
                            else:
                                self.state = 9
                        else:
                            self.state = 1 #fake success in debug mode

                        self.message = message
                        self.save()

            except mandrill.Error, e:
                self.update(state=2)
                # Mandrill errors are thrown as exceptions
                print "mandrill_error: %s - %s" % (e.__class__, e)
                raise
