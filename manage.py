import os
from flask.ext.script import Manager
from flask.ext.migrate import MigrateCommand
from flask.ext.security import SQLAlchemyUserDatastore

from liaison import app
from liaison.lib.extensions import db
from liaison.models.account import Account
from liaison.models.user import User, Role
from liaison.models.list import List
from liaison.models.email import Email
from liaison.models.campaign import Campaign
from liaison.models.template import Template


manager = Manager(app)
manager.add_command('db', MigrateCommand)

@manager.command
def run():
    """Run in local machine."""
    app.run()


if __name__ == "__main__":
    manager.run()

