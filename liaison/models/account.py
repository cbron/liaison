from sqlalchemy import Column
from sqlalchemy.orm import relationship
from liaison.lib.extensions import db
from liaison.lib.constants import STRING_LEN
from basemodel import BaseMixin

class Account(db.Model, BaseMixin):
    __tablename__ = 'accounts'

    id = Column(db.Integer, primary_key=True)
    name = Column(db.String(STRING_LEN), nullable=False, unique=True)
    domain = Column(db.String(STRING_LEN), nullable=False)
    subaccount_name = Column(db.String(STRING_LEN))
    api_key = Column(db.String(STRING_LEN))
    dedicated_ip = Column(db.String(STRING_LEN))
    active = Column(db.SmallInteger, default=1)
    default_from_email = Column(db.String(STRING_LEN))
    contact_email = Column(db.String(STRING_LEN))
    phone = Column(db.String(STRING_LEN))
    address = Column(db.String(STRING_LEN))
    city = Column(db.String(STRING_LEN))
    state = Column(db.String(STRING_LEN))
    zip_code = Column(db.String(STRING_LEN))
    country = Column(db.Integer)
    auto_text = Column(db.Integer)
    footer_html = Column(db.Text())
    footer_text = Column(db.Text())
    created_at = Column(db.DateTime(timezone=True),  default=db.func.now())
    modified_at = Column(db.DateTime(timezone=True), default=db.func.now(), onupdate=db.func.now())


    def ip_pool(self):
        return self.dedicated_ip or None


    @classmethod
    def find_by_name(cls, name):
        return cls.query.filter_by(name=name).first()

