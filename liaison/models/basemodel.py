import arrow
from sqlalchemy.ext.declarative import as_declarative
from sqlalchemy.inspection import inspect
from flask.ext.sqlalchemy import _BoundDeclarativeMeta
from flask.ext.login import current_user
from flask import current_app
from liaison.lib.extensions import db


class ModelDeclarativeMeta(_BoundDeclarativeMeta):
    pass


@as_declarative(name='Model',metaclass=ModelDeclarativeMeta)
class BaseMixin(object):

    @classmethod
    def first(cls):
        return cls.query.filter(cls.account_id==current_user.account_id).first()

    @classmethod
    def first_anon(cls):
        return cls.query.first()

    @classmethod
    def last(cls):
        return cls.query.filter(cls.account_id==current_user.account_id).order_by('id desc').first()

    @classmethod
    def find_all(cls):
        return cls.query.filter(cls.account_id==current_user.account_id)

    @classmethod
    def find_all_desc(cls):
        return cls.find_all().order_by(cls.id.desc())

    @classmethod
    def find_by_id(cls, id):
        if any(
            (isinstance(id, basestring) and id.isdigit(),
             isinstance(id, (int, float))),
        ):
            return cls.query.filter(cls.account_id==current_user.account_id, cls.id==id).first()
        return None

    @classmethod
    def find_by_id_anon(cls, id):
        if any(
            (isinstance(id, basestring) and id.isdigit(),
             isinstance(id, (int, float))),
        ):
            return cls.query.filter(cls.id==id).first()
        return None

    @classmethod
    def create(cls, **kwargs):
        '''Article.create(name="My Title", site_id=42)'''
        instance = cls(**kwargs)
        success = instance.save()
        if success:
            return instance
        else:
            return False

    def update(self, commit=True, **kwargs):
        for attr, value in kwargs.iteritems():
            setattr(self, attr, value)
        return commit and self.save() or self

    def save(self, commit=True):
        try:
            db.session.add(self)
            if commit:
                db.session.commit()
        except Exception, e:
            current_app.logger.exception('Exception: %s'%e)
            return False
        return self

    def delete(self, commit=True):
        db.session.delete(self)
        return commit and db.session.commit()

    def created(self):
        if not self.created_at:
            return ''
        ot = arrow.get(self.created_at)
        ot = ot.to('US/Arizona')
        return ot.format('MM/DD/YY hh:mm:ss a');

    def created_humanize(self):
        if not self.created_at:
            return ''
        ot = arrow.get(self.created_at)
        ot = ot.to('US/Arizona')
        return ot.humanize()

    def modified(self):
        if not self.created_at:
            return ''
        ot = arrow.get(self.created_at)
        ot = ot.to('US/Arizona')
        return ot.format('MM/DD/YY hh:mm:ss a');

    def modified_humanize(self):
        if not self.created_at:
            return ''
        ot = arrow.get(self.created_at)
        ot = ot.to('US/Arizona')
        return ot.humanize()

    def __repr__(self):
        val = None
        for col in ['name', 'id', 'title', 'award_name']:
            if not val and col in self.__table__.c.keys():
                val = self.__getattribute__(col)
        if val:
            return '<%s: %s>' % (self.__table__, val)
        else:
            return '<%s>' % (self.__table__)

    def attrs(self):
        cols = {col: getattr(self, col) for col in self.__class__.__table__.columns._data.keys()}
        cols = '\n'.join(['%s: %s' % (key, str(value)[:75]) for (key, value) in sorted(cols.items())])
        rels = '\n'.join([key for key in sorted(inspect(self.__class__).relationships.keys())])
        print '\n'.join(['%s' % self.__class__, cols, '\nrelationships:', rels])
