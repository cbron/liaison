from flask.ext.security import SQLAlchemyUserDatastore
from liaison.lib.extensions import db
from liaison.models.account import Account
from liaison.models.user import User, Role
from liaison.models.list import List
from liaison.models.email import Email
from liaison.models.campaign import Campaign
from liaison.models.dispatcher import Dispatcher
from liaison.models.send import Send

###
# Helpers
###

def create_account():
    a = Account.find_by_name("Demo Account")
    if a:
        return a.id
    else:
        return Account.create(
            name="Demo Account",
            domain='example.com',
            default_from_email='demo@example.com',
            contact_email='demo@example.com',
            footer_html='{{VIEW_IN_BROWSER_LINK}}, {{UNSUBSCRIBE_LINK}}',
            footer_text='Contact Us - {{VIEW_IN_BROWSER_LINK}}, {{UNSUBSCRIBE_LINK}}'
        )

def create_user(a_id):
    role = Role.find_by_name("user")
    if not role:
        role = Role.create(name='user')
    user = User.query.filter_by(email='admin@example.com').first()
    if not user:
        user_datastore = SQLAlchemyUserDatastore(db, User, Role)
        user = user_datastore.create_user(
            account_id=a_id,
            email=u'admin@example.com',
            first_name=u'jake',
            last_name=u'smith',
            password=u'asdfasdf'
        )
        user_datastore.add_role_to_user(user, role)
    return user

def create_list(a_id=None):
    if not a_id:
        a_id = create_account()
    return List.create(
        name='not-your-list',
        account_id=a_id,
        import_data=[{'test':'data'}]
    )

def create_campaign(a_id, l_id):
    return Campaign.create(
        account_id=a_id,
        name='campaign example',
        to_email_dd='Email Address',
        list_id=l_id
    )

def create_email(a_id,c_id):
    return Email.create(
        account_id=a_id,
        name="Test Email ONe",
        html="<b>Body here, Hi {{ First Name }}</b>",
        text='text only here {{First Name}}',
        subject='Test Subject',
        campaign_id=c_id
    )

def create_dispatch(a_id, c_id, l_id):
    return Dispatcher.create(
        account_id=a_id,
        user_id=1,
        campaign_id=c_id,
        list_id=l_id,
        import_data=[{'name':'bob'}, {'name': 'sally'}]
    )

def create_send(a_id, e_id, d_id):
    return Send.create(
        account_id=a_id,
        dispatcher_id=d_id,
        email_id=e_id,
        hash_id='azyx',
        data={}
    )

def create_stack():
    stack = {}

    a_id = create_account().id
    stack['account_id'] = a_id

    u_id = create_user(a_id).id
    stack['user_id'] = u_id

    l_id = create_list(a_id).id
    stack['list_id'] = l_id

    c_id = create_campaign(a_id, l_id).id
    stack['campaign_id'] = c_id

    e_id = create_email(a_id, c_id).id
    stack['email_id'] = e_id

    d_id = create_dispatch(a_id, c_id, l_id).id
    stack['dispatcher_id'] = d_id

    s_id = create_send(a_id, e_id, d_id).id
    stack['send_id'] = s_id

    return stack

