import os
import random
from flask import current_app
from sqlalchemy import Column
from sqlalchemy.orm import relationship, deferred
from sqlalchemy.dialects.postgresql import JSON
from werkzeug import secure_filename
from basemodel import BaseMixin
from liaison.lib.extensions import db
from liaison.lib.utils import make_dir
from liaison.lib.constants import STRING_LEN
from liaison.lib.aws import upload_list


class List(db.Model, BaseMixin):
    __tablename__ = 'lists'

    id = Column(db.Integer, primary_key=True)
    account_id = Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    name = Column(db.String(STRING_LEN), nullable=False)
    filename = Column(db.String(STRING_LEN))
    import_data = deferred(db.Column(JSON))
    created_at = Column(db.DateTime(timezone=True),  default=db.func.now())
    modified_at = Column(db.DateTime(timezone=True), default=db.func.now(), onupdate=db.func.now())
    account = relationship("Account",
        primaryjoin="Account.id==List.account_id",
        foreign_keys="List.account_id")
    campaigns = relationship("Campaign",
        primaryjoin="Campaign.list_id==List.id",
        foreign_keys="Campaign.list_id")

    def __repr__ (self):
        return '<List: %s - %s>' % (self.id, self.name)

    @classmethod
    def save_file(cls, file, list_id, curr_acct_id):
        if current_app.debug:
            # Local Save
            filename = secure_filename(file.filename)
            account_path = os.path.join(current_app.config['IMPORT_FOLDER'], str(curr_acct_id))
            make_dir(account_path)
            list_path = os.path.join(account_path, str(list_id))
            make_dir(list_path)
            file_path = os.path.join(list_path,  filename)
            file.save(file_path)
            return file_path
        else:
            # S3 Save
            filename = secure_filename(file.filename)
            return upload_list(curr_acct_id, list_id, filename, file)


    def total_send_count(self):
        return len(self.import_data) if self.import_data else 0


    def get_import_data_keys(self):
        if self.import_data:
            keys = []
            for k,v in self.import_data[0].iteritems():
                if k != "hash_id":
                    keys.append(k)
            keys.sort()
            return keys
        else:
            return []


    def get_unique_col_values(self, col, tup=False):
        if self.import_data:
            vals = set([])
            for row in self.import_data:
                if row.get(col):
                    vals.add(row.get(col))
            if tup:
                cover = [('','')]
                for v in vals:
                    cover.append((v, v))
                return cover
            else:
                return vals
        else:
            return []


    def random_data_sample(self, sample_size=15):
        if self.import_data:
            random_set = range(len(self.import_data))
            sample_size = sample_size if len(self.import_data) >= 15 else len(self.import_data)
            randos = random.sample(random_set, sample_size)
            random_data = []
            for r in randos:
                random_data.append(self.import_data[r])
            return random_data
        else:
            return None
