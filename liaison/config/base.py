import os
from datetime import timedelta
from liaison.lib.utils import make_dir


class BaseConfig(object):

    DEBUG = True
    TESTING = False
    SECRET_KEY = 'changeme'
    EXTERNAL_VIEW_URL = "http://localhost:5000"
    SQLALCHEMY_ECHO = True
    SQLALCHEMY_DATABASE_URI = "postgresql://localhost/liaison"
    REDIS_URL = "redis://@localhost:6379/0"
    BOX_TYPE = "WEB"
    PROJECT = "liaison"
    PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    SESSION_TYPE = 'redis'

    # Flask-mail
    # http://pythonhosted.org/flask-mail/
    MAIL_DEBUG = DEBUG
    MAIL_SERVER = 'smtp.mandrillapp.com'
    MAIL_PORT = 587
    # MAIL_USE_SSL = True
    # MAIL_USE_TLS = True
    MAIL_USERNAME = ''
    MAIL_PASSWORD = ''
    MAIL_FROM = ''
    MAIL_DEFAULT_SENDER = ''

    # Flask-Security
    # https://pythonhosted.org/Flask-Security/configuration.html
    SECURITY_URL_PREFIX = '/user'
    SECURITY_PASSWORD_HASH = 'pbkdf2_sha512'
    SECURITY_PASSWORD_SALT = 'changeme'
    SECURITY_EMAIL_SENDER = ''
    SECURITY_RECOVERABLE = True
    SECURITY_TRACKABLE = True
    SECURITY_CHANGEABLE = True

    # Celery
    # https://celery.readthedocs.org/en/latest/configuration.html
    BROKER_URL = 'redis://localhost:6379/0'
    ADMINS = (('', ''),)
    CELERY_TASK_RESULT_EXPIRES = 1
    CELERY_IGNORE_RESULT = True
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_ACCEPT_CONTENT=['json']
    CELERY_CREATE_MISSING_QUEUES = True
    CELERY_ENABLE_UTC = True
    # Celery Redis
    BROKER_TRANSPORT_OPTIONS = {
        'fanout_patterns': True,
        'fanout_prefix': True
    }
    EMAIL_HOST = 'smtp.mandrillapp.com'
    EMAIL_PORT = 587
    EMAIL_HOST_USER = ''
    EMAIL_HOST_PASSWORD = ''

    CELERY_DEFAULT_QUEUE = 'default'
    CELERY_ROUTES = {
        'liaison.lib.tasks.prep_data_task': {'queue': 'dispatcher'},
        'liaison.lib.tasks.queue_emails_task': {'queue': 'dispatcher'},
        'liaison.lib.tasks.send_email_task': {'queue': 'mail'},
        'liaison.lib.tasks.update_dispatches_status': {'queue': 'default'},
        'liaison.lib.tasks.send_scheduled': {'queue': 'beat'},
        'liaison.lib.tasks.retry_failures': {'queue': 'beat'},
        'liaison.lib.tasks.retry_send': {'queue': 'mail'},
        'liaison.lib.tasks.run_import': {'queue': 'default'},
        'liaison.lib.tasks.run_blacklist_import': {'queue': 'default'}
    }
    CELERYBEAT_SCHEDULE = {
        'retry failed or unprocessed mail': {
            'task': 'liaison.lib.tasks.retry_failures',
            'schedule': timedelta(hours=1)
        },
        'send scheduled dispatches': {
            'task': 'liaison.lib.tasks.send_scheduled',
            'schedule': timedelta(minutes=10)
        },
    }

    CONTENT_FOLDER = os.path.abspath(os.path.join(PROJECT_ROOT, '..', 'content'))
    make_dir(CONTENT_FOLDER)
    IMPORT_FOLDER = os.path.abspath(os.path.join(PROJECT_ROOT, '..', 'content', 'imports'))
    make_dir(IMPORT_FOLDER)
    LOG_FOLDER = os.path.abspath(os.path.join(PROJECT_ROOT, '..', 'content', 'logs'))
    make_dir(LOG_FOLDER)
