from sqlalchemy import Column
from sqlalchemy.orm import relationship
from flask.ext.security import UserMixin, RoleMixin

from basemodel import BaseMixin
from liaison.lib.extensions import db
from liaison.lib.constants import STRING_LEN


roles_users = db.Table('roles_users',
        db.Column('user_id', db.Integer(), db.ForeignKey('users.id')),
        db.Column('role_id', db.Integer(), db.ForeignKey('roles.id')))


class Role(db.Model, RoleMixin, BaseMixin):
    __tablename__ = 'roles'

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

    @classmethod
    def find_by_name(cls, name):
        return cls.query.filter_by(name=name).first()


class User(db.Model, UserMixin, BaseMixin):
    __tablename__ = 'users'

    id = Column(db.Integer, primary_key=True)
    account_id = Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    account = relationship("Account",
        primaryjoin="Account.id==User.account_id",
        foreign_keys="User.account_id")
    email = Column(db.String(STRING_LEN), nullable=False, unique=True)
    first_name = Column(db.String(STRING_LEN), nullable=False)
    last_name = Column(db.String(STRING_LEN), nullable=False)
    accepted_terms = Column(db.SmallInteger, default=0)
    activation_key = Column(db.String(STRING_LEN))
    password = Column(db.String(STRING_LEN), nullable=False)
    phone = Column(db.String(STRING_LEN))
    image = Column(db.String(STRING_LEN))
    confirmed_at = Column(db.DateTime(timezone=True))
    login_count = Column(db.Integer)
    current_login_at = Column(db.DateTime(timezone=True))
    last_login_at = Column(db.DateTime(timezone=True))
    current_login_ip = Column(db.String(STRING_LEN))
    last_login_ip = Column(db.String(STRING_LEN))
    active = db.Column(db.Boolean(), default=True)
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))
    created_at = Column(db.DateTime(timezone=True),  default=db.func.now())
    modified_at = Column(db.DateTime(timezone=True), default=db.func.now(), onupdate=db.func.now())

    def __repr__ (self):
        return '<User: %s>' % self.email

    @property
    def name(self):
        return ' '.join([self.first_name.capitalize(), self.last_name.capitalize()])

    @classmethod
    def get_by_id(cls, user_id):
        return cls.query.filter_by(id=user_id).first_or_404()
