import csv
import StringIO
import arrow
from datetime import datetime
from flask import current_app, make_response
from sqlalchemy import Column, func
from liaison.lib.extensions import db
from liaison.lib.constants import STRING_LEN
from basemodel import BaseMixin

class Unsubscribe(db.Model, BaseMixin):
    __tablename__ = 'unsubscribes'

    id = Column(db.Integer, primary_key=True)
    account_id = Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    email = Column(db.String(STRING_LEN), index=True)
    manual = Column(db.Integer,default=0)
    created_at = Column(db.DateTime(timezone=True),  default=db.func.now())

    @classmethod
    def check(cls, account_id, email):
        return cls.query.with_entities(cls.id).filter(cls.account_id==account_id, cls.email==email).count() or 0

    @classmethod
    def get_all_emails(cls):
        unsubscribes = cls.find_all().all()
        emails = []
        for unsub in unsubscribes:
            emails.append(unsub.email)
        return emails

    @classmethod
    def generate_csv(cls):
        content = StringIO.StringIO()
        cw = csv.writer(content)

        unsubscribes = cls.find_all().all()

        for unsub in unsubscribes:
            created = arrow.get(unsub.created_at).to('US/Arizona').format('MM/DD/YY HH:mm:ss')
            cw.writerow([unsub.email, created])


        ot = arrow.get(datetime.utcnow())
        ot = ot.to('US/Arizona').format('MM/DD/YY HH:mm:ss')
        filename = "unsubscribes-{}.csv".format(ot)
        response = make_response(content.getvalue())
        response.headers["Content-Disposition"] = "attachment; filename=%s" % filename
        response.headers["Content-type"] = "text/csv"
        return response

