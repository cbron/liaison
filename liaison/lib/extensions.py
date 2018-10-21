# -*- coding: utf-8 -*-

from flask.ext.sqlalchemy import SQLAlchemy
db = SQLAlchemy()

from flask.ext.mail import Mail
mail = Mail()

from flask.ext.migrate import Migrate
migrate = Migrate()

from flask_redis import Redis
redis_store = Redis()

from boto.s3.connection import S3Connection
s3 = S3Connection()

from flask.ext.security import Security
security = Security()

from flask.ext.session import Session
redis_session = Session()

from celery import Celery
def make_celery(app):
    celery = Celery(app.import_name)
    celery.conf.update(app.config)
    TaskBase = celery.Task
    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery
