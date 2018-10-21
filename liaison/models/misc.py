import json
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSON
from liaison.lib.extensions import db
from liaison.lib.constants import STRING_LEN
from liaison.lib.extensions import redis_store as redis
from basemodel import BaseMixin

class Misc(db.Model, BaseMixin):
    __tablename__ = 'misc'

    id = Column(db.Integer, primary_key=True)
    name = Column(db.String(STRING_LEN))
    data = Column(JSON)
    count = Column(db.Integer)
    created_at = Column(db.DateTime(timezone=True),  default=db.func.now())
    modified_at = Column(db.DateTime(timezone=True), default=db.func.now(), onupdate=db.func.now())

    @classmethod
    def do_stuff(self):
        '''
        Used for load testing
        '''
        r = self.create(
            name='create_random',
            data = {'dog': 'cat', 'black': 'white'}
        )
        r2 = Misc.find_by_id_anon(r.id)
        r2.update(data={})
        r2.update(data={'yes': 'no'})
        r2.save()
        r2.delete()
        r2 = Misc.find_by_id_anon(r.id)
        redis.incr('load_test')
