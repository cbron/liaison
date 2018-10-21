import os
from flask import Flask, render_template, jsonify, redirect, url_for, flash, request
from flask.ext.login import logout_user
from config.base import BaseConfig
from lib.extensions import db, mail, migrate, redis_store, security, redis_session
from werkzeug.contrib.fixers import ProxyFix
from flask.ext.security import SQLAlchemyUserDatastore

app = Flask(BaseConfig.PROJECT)


def configure_app(app):
    # for gunicorn on nginx
    app.wsgi_app = ProxyFix(app.wsgi_app)


def configure_configs(app, config=None):
    # http://flask.pocoo.org/docs/api/#configuration
    app.config.from_object(BaseConfig)
    app.config.from_pyfile('config/production.py', silent=True)

    if config:
        app.config.from_object(config)


def configure_extensions(app):
    # flask-sqlalchemy
    db.init_app(app)

    # flask-mail
    mail.init_app(app)

    #flask-migrate
    migrate.init_app(app, db)

    #redis
    redis_store.init_app(app)

    #session
    app.config['SESSION_REDIS'] = redis_store
    redis_session.init_app(app)

def configure_logging(app):
    if app.debug or app.testing:
        # Skip debug and test mode. Just check standard output.
        return None

    import logging
    from logging.handlers import SMTPHandler
    from logentries import LogentriesHandler

    # Set info level on logger, which might be overwritten by handers. Suppress DEBUG messages.
    app.logger.setLevel(logging.INFO)

    # Main log
    info_log = os.path.join(app.config['LOG_FOLDER'], 'flask_app.log')
    info_file_handler = logging.handlers.RotatingFileHandler(info_log, maxBytes=100000, backupCount=10)
    info_file_handler.setLevel(logging.INFO)
    info_file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]')
    )
    app.logger.addHandler(info_file_handler)

    # Log Entries
    if app.config.get('BOX_TYPE') == 'WEB':
        le_log = logging.getLogger('logentries')
        le_log.setLevel(logging.INFO)
        le_log.addHandler(LogentriesHandler('changeme'))
        app.logger.addHandler(le_log)


def configure_error_handlers(app):
    from liaison.lib.utils import email_exception

    @app.errorhandler(403)
    def forbidden_page(error):
        # this is a hack to make flask-security work with flask-login
        flash('Please login to view this page.')
        logout_user()
        return redirect(url_for('security.login', next=request.url))

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template("errors/page_not_found.html"), 404

    @app.errorhandler(500)
    def server_error_page(error):
        email_exception(error)
        return render_template("errors/server_error.html"), 500


def configure_blueprints(app):
    """Configure blueprints in views."""
    from views.user import user
    from views.account import account
    from views.campaign import campaign
    from views.email import email
    from views.list import list_
    from views.dispatcher import dispatcher
    from views.pf import pf
    from views.admin import admin
    from views.blacklist import blacklist

    blueprints = (
        user,
        account,
        campaign,
        email,
        list_,
        dispatcher,
        pf,
        admin,
        blacklist
    )

    for blueprint in blueprints:
        app.register_blueprint(blueprint)


def configure_auth(app):
    from liaison.models.user import User,Role
    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    security.init_app(app, user_datastore)


configure_app(app)
configure_configs(app)
configure_extensions(app)
configure_logging(app)
configure_error_handlers(app)
configure_blueprints(app)
configure_auth(app)
