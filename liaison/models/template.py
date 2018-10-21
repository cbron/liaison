import os
import sys
from flask import current_app
from sqlalchemy import Column
from liaison.lib.extensions import db
from liaison.lib.constants import STRING_LEN
from basemodel import BaseMixin

class Template(db.Model, BaseMixin):
    __tablename__ = 'templates'

    id = Column(db.Integer, primary_key=True)
    display_name = Column(db.String(STRING_LEN))
    file_name = Column(db.String(STRING_LEN))
    html = Column(db.Text())
    url = Column(db.String(STRING_LEN))
    active = Column(db.Integer)
    order = Column(db.Integer)
    created_at = Column(db.DateTime(timezone=True),  default=db.func.now())
    modified_at = Column(db.DateTime(timezone=True), default=db.func.now(), onupdate=db.func.now())

    @classmethod
    def get_all(cls):
        return [x for x in cls.query.order_by(cls.order.asc()).all()]

    @classmethod
    def get_all_choices(cls):
        return [(t.id, t.file_name, t.display_name) for t in cls.get_all()]

    @classmethod
    def get_html(cls, template_id):
        template = cls.query.filter_by(id=template_id).first()
        if template:
            path = os.path.abspath(os.path.join(current_app.config.get('PROJECT_ROOT'), 'static', 'templates', template.file_name + ".html"))
            with open(path) as myfile:
                html=myfile.read()
            return html
        else:
            return None
