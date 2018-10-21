import os
from datetime import datetime
from flask import current_app
from sqlalchemy import Column, func
from sqlalchemy.orm import relationship
from liaison.lib.extensions import db
from liaison.lib.constants import STRING_LEN
from basemodel import BaseMixin
from werkzeug import secure_filename
from liaison.lib.utils import make_dir
from liaison.lib.aws import upload_blacklist

class Blacklist(db.Model, BaseMixin):
    __tablename__ = 'blacklists'

    id = Column(db.Integer, primary_key=True)
    account_id = Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    email = Column(db.String(STRING_LEN), index=True)
    detail = Column(db.String(STRING_LEN))
    reason = Column(db.String(STRING_LEN))
    manual = Column(db.Integer,default=0)
    created_at = Column(db.DateTime(timezone=True),  default=db.func.now())

    @classmethod
    def check(cls, account_id, email):
        return cls.query.with_entities(cls.id).filter(cls.account_id==account_id, cls.email==email).count() or 0

    @classmethod
    def insert(cls, account_id, email, reason, detail):
        if not Blacklist.check(account_id, email):
            if detail:
                detail = (detail[:240] + '..') if len(detail) > 240 else detail
            if reason:
                reason = (reason[:240] + '..') if len(reason) > 240 else reason
            Blacklist.create(account_id=account_id, email=email, reason=reason, detail=detail)
            return True
        else:
            return False

    @classmethod
    def save_file(cls, account_id, file):
        filename = secure_filename(file.filename)
        if current_app.debug:
            # Local Save
            account_path = os.path.join(current_app.config['IMPORT_FOLDER'], str(account_id))
            make_dir(account_path)
            blacklist_path = os.path.join(account_path, 'blacklists')
            make_dir(blacklist_path)
            file_path = os.path.join(blacklist_path,  filename)
            file.save(file_path)
            return file_path
        else:
            # S3 Save
            return upload_blacklist(account_id, filename, file)

