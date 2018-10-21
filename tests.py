import unittest
import logging
from flask.ext.testing import TestCase
from flask.ext.migrate import upgrade
import logging
from datetime import datetime, timedelta
import pytz

from liaison.lib.extensions import db, redis_store as redis
import liaison.lib.test_helpers as helpers
from liaison import app

from liaison.models.user import User
from liaison.models.email import Email
from liaison.models.campaign import Campaign
from liaison.models.dispatcher import Dispatcher
from liaison.models.list import List
from liaison.models.send import Send
from liaison.models.unsubscribe import Unsubscribe
from liaison.models.blacklist import Blacklist
import manage


class MyTest(TestCase):

    '''
    Requires postgresql and redis to be running locally
    '''

    def create_app(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://localhost/liaisontesting"
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_ECHO'] = False
        app.config['DEBUG'] = True
        logging.disable(logging.CRITICAL)
        return app

    def setUp(self):
        with app.app_context():
            upgrade()
            if len(User.query.all()) < 1:
                manage.seed()

    def tearDown(self):
        with app.app_context():
            db.session.commit() # sqlalchemy bug fixer
            db.reflect()
            db.drop_all()

    ###
    # Send.py
    ###

    def test_current_state(self):
        s = Send(state=9)
        self.assertEqual(s.current_state(), 'unknown')

    def test_find_by_hash(self):
        stack = helpers.create_stack()
        self.assertEqual(Send.find_by_hash('azyx').id, stack['send_id'])

    def test_process_skip_bad_state(self):
        stack = helpers.create_stack()
        send = Send.query.first()
        redis.delete('dispatcher_%s_sent' % send.dispatcher_id)
        send.state = -1
        send.process()
        self.assertEqual(send.attempts, 1)
        self.assertEqual(send.dispatcher.get_sent(), '1')
        send.process()
        self.assertEqual(send.attempts, 2)
        self.assertEqual(send.dispatcher.get_sent(), '1')
        redis.delete('dispatcher_%s_sent' % send.dispatcher_id)

    def test_process_skip_no_hash(self):
        stack = helpers.create_stack()
        send = Send.query.first()
        send.state = 0
        send.hash_id = None
        send.save()
        send.process()
        self.assertEqual(send.state, 103)

    def test_process_skip_bad_to_email(self):
        stack = helpers.create_stack()
        send = Send.query.first()

        #try blank column
        data = send.data
        send.update(data={})
        send.state=0
        data['Email Address'] = ''
        send.data = data
        send.save()
        send.process()
        self.assertEqual(send.state, 8)

        #try no column
        data = send.data
        send.update(data={})
        send.state=0
        data.pop("Email Address")
        send.data = data
        send.save()
        send.process()
        self.assertEqual(send.state, 8)

    def test_process_skip_unsubscribed(self):
        stack = helpers.create_stack()
        send = Send.query.first()
        self.assertEqual(send.state, 0)
        Unsubscribe.create(account_id=stack['account_id'], email=send.data.get("Email Address"))
        send.process()
        self.assertEqual(send.state, 6)

    def test_process_skip_blacklisted(self):
        stack = helpers.create_stack()
        send = Send.query.first()
        self.assertEqual(send.state, 0)
        Blacklist.create(account_id=stack['account_id'], email=send.data.get("Email Address"))
        send.process()
        self.assertEqual(send.state, 7)

    def test_process_success(self):
        stack = helpers.create_stack()
        send = Send.query.first()
        self.assertEqual(send.message, None)
        send.process()
        p_send = Send.query.first()
        self.assertEqual(p_send.state, 1)
        self.assertEqual(p_send.message.get('recipient_metadata')[0].get('rcpt'), p_send.data.get("Email Address"))

    def test_process_success_keys(self):
        stack = helpers.create_stack()
        send = Send.query.first()
        send.process()
        self.assertEqual(send.message.keys(), [u'from_name', u'recipient_metadata', u'to', u'track_opens', u'text', u'subject', u'inline_css', u'track_clicks', u'from_email', u'headers', u'html', u'auto_html', u'merge', u'preserve_recipients', u'signing_domain', u'metadata', u'auto_text', u'view_content_link', u'important', u'url_strip_qs'])

    ###
    # Emails
    ###

    def test_full_html(self):
        stack = helpers.create_stack()
        e = Email.find_by_id_anon(stack['email_id'])
        e.html = '<h1>this is the new test html, {{ First Name }}</h1>'
        e.preheader = "I am a preheader"
        check = "<span class='preheader'>%s</span>%s<br>%s" % (e.preheader, e.html, e.account.footer_html)
        self.assertEqual(e.full_html(), check)

    def test_full_text(self):
        stack = helpers.create_stack()
        e = Email.find_by_id_anon(stack['email_id'])
        e.html = '<h1>this is the new test html, {{ First Name }}</h1>'
        e.text = 'text only test'
        e.preheader = "I am a preheader"
        check = "%s\n\n%s" % (e.text, e.account.footer_text)
        self.assertEqual(e.full_text(), check)

    def test_render_html_attr(self):
        stack = helpers.create_stack()
        e = Email.find_by_id_anon(stack['email_id'])
        data = {
            'First Name': 'Bobby Lee'
        }
        check = '<b>Body here, Hi Bobby Lee</b><br>http://localhost:5000/pf/vib/12345, http://localhost:5000/pf/unsubscribe/12345'
        self.assertEqual(e.render_html_attr(data,'12345'), check)

    def test_render_text_attr(self):
        stack = helpers.create_stack()
        e = Email.find_by_id_anon(stack['email_id'])
        data = {
            'First Name': 'Bobby Lee'
        }
        check = 'text only here Bobby Lee\n\nContact Us - http://localhost:5000/pf/vib/12345, http://localhost:5000/pf/unsubscribe/12345'
        self.assertEqual(e.render_text_attr(data,'12345'), check)

    def test_check_keys(self):
        stack = helpers.create_stack()
        e = Email.find_by_id_anon(stack['email_id'])
        mylist = List.find_by_id_anon(stack['list_id'])
        e.html = "cats and {{dogs}}"
        e.save()
        mylist.import_data="{['cats': 'no_dogs']}"
        mylist.save()
        self.assertEqual( e.check_keys(stack['list_id']), (False, 'dogs') )

    def test_email_view_in_browser_link(self):
        self.assertEqual(Email.unsubscribe_link('abc'), 'http://localhost:5000/pf/unsubscribe/abc')

    def test_email_unsubscribe_link(self):
        self.assertEqual(Email.view_in_browser_link('abc'), 'http://localhost:5000/pf/vib/abc')

    def test_add_additional_data(self):
        result = {
            'UNSUBSCRIBE_LINK': 'http://localhost:5000/pf/unsubscribe/abc',
            'VIEW_IN_BROWSER_LINK': 'http://localhost:5000/pf/vib/abc'
        }
        self.assertEqual(Email.add_additional_data({},'abc'), result)


    ###
    # Dispatcher
    ###

    def test_dispatcher_current_state(self):
        stack = helpers.create_stack()
        d = Dispatcher.find_by_id_anon(stack['dispatcher_id'])
        self.assertEqual(d.current_state(), 'Pending')
        d.update(state=10)
        self.assertEqual(d.current_state(), 'Complete')


    def test_dispatcher_send_bad_state(self):
        stack = helpers.create_stack()
        d = Dispatcher.find_by_id_anon(stack['dispatcher_id'])
        disp_count = redis.llen("dispatcher")
        d.update(state=1)
        d.send()
        self.assertEqual(redis.llen("dispatcher"), disp_count)
        self.assertEqual(d.state, 1)

    def test_dispatcher_send(self):
        stack = helpers.create_stack()
        d = Dispatcher.find_by_id_anon(stack['dispatcher_id'])
        disp_count = redis.llen("dispatcher")
        d.send()
        self.assertEqual(redis.llen("dispatcher"), disp_count + 1)
        redis.delete("dispatcher")


    def test_dispatcher_prep_data(self):
        stack = helpers.create_stack()
        d = Dispatcher.find_by_id_anon(stack['dispatcher_id'])
        orig_data = d.import_data
        disp_count = redis.llen("dispatcher")
        d.prep_data()
        self.assertEqual(d.state, 1)
        self.assertEqual(redis.llen("dispatcher"), disp_count + 1)
        self.assertEqual(d.import_data, orig_data)
        self.assertEqual(d.adjusted_data[0].keys(), ['name', 'hash_id'])
        self.assertEqual(len(d.adjusted_data[1].get('hash_id')), 64)
        self.assertEqual(len(d.adjusted_data), len(orig_data))
        redis.delete("dispatcher")


    def test_dispatcher_queue_emails_bad_data(self):
        stack = helpers.create_stack()
        d = Dispatcher.find_by_id_anon(stack['dispatcher_id'])
        d.queue_emails()
        self.assertEqual(d.state, 104)

    def test_dispatcher_queue_emails_bad_data_2(self):
        stack = helpers.create_stack()
        d = Dispatcher.find_by_id_anon(stack['dispatcher_id'])
        d.update(adjusted_data="[{}]")
        d.queue_emails()
        self.assertEqual(d.state, 104)

    def test_dispatcher_queue_emails_bad_no_hash(self):
        stack = helpers.create_stack()
        d = Dispatcher.find_by_id_anon(stack['dispatcher_id'])
        d.update(adjusted_data=d.import_data)
        d.queue_emails()
        self.assertEqual(d.state, 103)

    def test_dispatcher_queue_emails(self):
        stack = helpers.create_stack()
        d = Dispatcher.find_by_id_anon(stack['dispatcher_id'])
        d.expire_counts()
        d.prep_data()
        count = len(d.adjusted_data)
        mail_count = redis.llen("mail")
        d.queue_emails()
        self.assertEqual(d.state, 3)
        self.assertEqual(redis.llen("mail"), mail_count + count)
        self.assertEqual(d.get_queued(), str(count))
        self.assertEqual(d.queued_count, count)
        redis.delete("dispatcher")


    def test_dispatcher_send_email_from_data_already_exists(self):
        stack = helpers.create_stack()
        d = Dispatcher.find_by_id_anon(stack['dispatcher_id'])
        send = Send.find_by_id_anon(stack['send_id'])
        sent_count_cache = int(d.get_sent())
        send_cnt = Send.query.count()
        d.send_email_from_data({'hash_id': send.hash_id})
        self.assertEqual(send_cnt, Send.query.count())
        self.assertEqual(sent_count_cache, int(d.get_sent()))

    def test_dispatcher_send_email_from_data_already_exists_with_attempt(self):
        stack = helpers.create_stack()
        d = Dispatcher.find_by_id_anon(stack['dispatcher_id'])
        send = Send.find_by_id_anon(stack['send_id'])
        send.update(attempts=send.attempts+1)
        sent_cnt_cache = int(d.get_sent())
        send_cnt = Send.query.count()
        d.send_email_from_data({'hash_id': send.hash_id})
        self.assertEqual(d.get_sent(), str(sent_cnt_cache + 1))
        self.assertEqual(send_cnt, Send.query.count())

    def test_dispatcher_send_email_from_data_no_email(self):
        stack = helpers.create_stack()
        d = Dispatcher.find_by_id_anon(stack['dispatcher_id'])
        c = Campaign.find_by_id_anon(stack['campaign_id'])
        e = Email.find_by_id_anon(stack['email_id'])
        c.update(selector_col_name='dog')
        e.update(selector_col_val='["false"]')
        send_cnt = Send.query.count()
        sk_cnt = int(d.get_skipped())
        d.send_email_from_data({'dog': 'cat'})
        self.assertEqual(send_cnt, Send.query.count())
        self.assertEqual(str(sk_cnt + 1), d.get_skipped())

    def test_dispatcher_send_email_from_data_success(self):
        stack = helpers.create_stack()
        d = Dispatcher.find_by_id_anon(stack['dispatcher_id'])
        sent_cnt_db = Send.query.count()
        sent_cnt_cache = int(d.get_sent())
        d.send_email_from_data({'dog': 'cat'})
        self.assertEqual(sent_cnt_db + 1, Send.query.count())
        self.assertEqual(str(sent_cnt_cache + 1), d.get_sent())

    def test_expire_counts(self):
        stack = helpers.create_stack()
        d = Dispatcher.find_by_id_anon(stack['dispatcher_id'])
        d.expire_counts()
        d.incr_sent()
        d.incr_skipped()
        d.incr_queued()
        self.assertEqual(int(d.get_sent()), 1)
        d.expire_counts()
        self.assertEqual(int(d.get_sent()), 0)

    def test_get_percent_complete_already(self):
        stack = helpers.create_stack()
        d = Dispatcher.find_by_id_anon(stack['dispatcher_id'])
        d.percent_complete = 100
        self.assertEqual(d.get_percent_complete(), 100)

    def test_get_percent_complete_cache(self):
        stack = helpers.create_stack()
        d = Dispatcher.find_by_id_anon(stack['dispatcher_id'])
        d.expire_counts()
        redis.set('dispatcher_%s_percent' % d.id, 15)
        self.assertEqual(d.get_percent_complete(), 15)
        redis.delete('dispatcher_%s_percent' % d.id)

    def test_get_percent_complete_not_ready(self):
        stack = helpers.create_stack()
        d = Dispatcher.find_by_id_anon(stack['dispatcher_id'])
        d.expire_counts()
        [d.incr_sent() for _ in range(5)]
        [d.incr_skipped() for _ in range(2)]
        self.assertEqual(d.get_percent_complete(), 0)
        redis.delete('dispatcher_%s_percent' % d.id)

    def test_get_percent_complete_under_90(self):
        stack = helpers.create_stack()
        d = Dispatcher.find_by_id_anon(stack['dispatcher_id'])
        d.expire_counts()
        [d.incr_queued() for _ in range(10)]
        [d.incr_sent() for _ in range(5)]
        [d.incr_skipped() for _ in range(2)]
        self.assertEqual(d.get_percent_complete(), 70)
        self.assertEqual(redis.exists('dispatcher_%s_percent' % d.id), True)
        d.expire_counts()
        redis.delete('dispatcher_%s_percent' % d.id)

    def test_get_percent_complete_done(self):
        stack = helpers.create_stack()
        d = Dispatcher.find_by_id_anon(stack['dispatcher_id'])
        d.update(queued_count=10)
        d.expire_counts()
        [d.incr_queued() for _ in range(10)]
        [d.incr_sent() for _ in range(6)]
        [d.incr_skipped() for _ in range(4)]
        self.assertEqual(d.get_percent_complete(), 100)
        self.assertEqual(d.percent_complete, 100)
        self.assertEqual(d.state, 10)
        self.assertEqual(d.sent_count, 6)
        self.assertEqual(d.skipped_count, 4)
        redis.delete('dispatcher_%s_percent' % d.id)

    def test_set_adjusted_data(self):
        stack = helpers.create_stack()
        d = Dispatcher.find_by_id_anon(stack['dispatcher_id'])
        self.assertEqual(d.adjusted_data, None)
        d.set_adjusted_data({'dog':'Nova'})
        self.assertEqual(d.adjusted_data, {'dog':'Nova'})

    def test_check_for_recent_none(self):
        stack = helpers.create_stack()
        d = Dispatcher.find_by_id_anon(stack['dispatcher_id'])
        limit = pytz.utc.localize(datetime.utcnow() - timedelta(minutes=5))
        d.update(created_at=limit)
        self.assertEqual(d.check_for_recent(d.campaign_id), False)

    def test_check_for_recent_found(self):
        stack = helpers.create_stack()
        d = Dispatcher.find_by_id_anon(stack['dispatcher_id'])
        limit = pytz.utc.localize(datetime.utcnow())
        Dispatcher.create(
            campaign_id=d.campaign_id,
            created_at=limit,
            account_id=d.account_id,
            user_id=d.user_id,
            list_id=d.list_id
        )
        limit = limit - timedelta(minutes=5) # so d doesn't trip it
        d.update(created_at=limit)
        self.assertEqual(d.check_for_recent(d.campaign_id), True)


    ###
    # Campaign
    ###

    def test_campaign_check_email_keys_bad(self):
        stack = helpers.create_stack()
        e = Email.find_by_id_anon(stack['email_id'])
        e.update(html="{{test}}")
        c = Campaign.find_by_id_anon(stack['campaign_id'])
        self.assertEqual(c.check_email_keys(),(True,None))

    def test_campaign_check_email_keys_good(self):
        stack = helpers.create_stack()
        e = Email.find_by_id_anon(stack['email_id'])
        e.update(html="{{bad_test}}")
        c = Campaign.find_by_id_anon(stack['campaign_id'])
        self.assertEqual(c.check_email_keys(),(False,"bad_test"))

    def test_campaign_render_attr(self):
        stack = helpers.create_stack()
        c = Campaign.find_by_id_anon(stack['campaign_id'])
        c.update(from_email_dd="Email Address")
        data = {'Email Address':'test@example.com'}
        self.assertEqual(c.render_attr('from_email_dd', data), "test@example.com")

    def test_campaign_selector_send_count(self):
        stack = helpers.create_stack()
        c = Campaign.find_by_id_anon(stack['campaign_id'])
        redis.delete('selector_send_count_%s' % c.id)
        self.assertEqual(c.selector_send_count(),1)

    def test_campaign_determiner_duplicates_false(self):
        stack = helpers.create_stack()
        c = Campaign.find_by_id_anon(stack['campaign_id'])
        e = Email.find_by_id_anon(stack['email_id'])
        e.update(selector_col_val='["dog"]')
        e2 = Email.create(account_id=c.account_id, name="EmailTwo", campaign_id=c.id)
        e2.update(selector_col_val='["cat"]')
        self.assertEqual(c.determiner_duplicates(),(False,None))

    def test_campaign_determiner_duplicates_true(self):
        stack = helpers.create_stack()
        c = Campaign.find_by_id_anon(stack['campaign_id'])
        e = Email.find_by_id_anon(stack['email_id'])
        e.update(selector_col_val='["dog"]')
        e2 = Email.create(account_id=c.account_id, name="EmailTwo", campaign_id=c.id)
        e2.update(selector_col_val='["dog"]')
        self.assertEqual(c.determiner_duplicates(),(True,'dog'))

    def test_campaign_selector_missing_false(self):
        stack = helpers.create_stack()
        c = Campaign.find_by_id_anon(stack['campaign_id'])
        self.assertEqual(c.selector_missing(),False)

    def test_campaign_selector_missing_true(self):
        stack = helpers.create_stack()
        c = Campaign.find_by_id_anon(stack['campaign_id'])
        e2 = Email.create(account_id=c.account_id, name="EmailTwo", campaign_id=c.id)
        self.assertEqual(c.selector_missing(),True)

    def test_campaign_email_determiner_no_specification(self):
        stack = helpers.create_stack()
        c = Campaign.find_by_id_anon(stack['campaign_id'])
        e = Email.find_by_id_anon(stack['email_id'])
        e2 = Email.create(account_id=c.account_id, name="EmailTwo", campaign_id=c.id)
        self.assertEqual(c.email_determiner({}), e)

    def test_campaign_email_determiner_single(self):
        stack = helpers.create_stack()
        c = Campaign.find_by_id_anon(stack['campaign_id'])
        c.update(selector_col_name='dog')
        e = Email.find_by_id_anon(stack['email_id'])
        e.update(selector_col_val='["woof"]')
        e2 = Email.create(account_id=c.account_id, name="EmailTwo", campaign_id=c.id)
        e2.update(selector_col_val='["cat"]')
        self.assertEqual(c.email_determiner({'dog': 'cat'}), e2)

    def test_campaign_email_determiner_no_selector_val(self):
        stack = helpers.create_stack()
        c = Campaign.find_by_id_anon(stack['campaign_id'])
        c.update(selector_col_name='dog')
        e = Email.find_by_id_anon(stack['email_id'])
        e.update(selector_col_val='[""]')
        e2 = Email.create(account_id=c.account_id, name="EmailTwo", campaign_id=c.id)
        e2.update(selector_col_val='[""]')
        self.assertEqual(c.email_determiner({'dog': 'cat'}), None)

    def test_campaign_email_determiner_none(self):
        stack = helpers.create_stack()
        c = Campaign.find_by_id_anon(stack['campaign_id'])
        c.update(selector_col_name='dog')
        e = Email.find_by_id_anon(stack['email_id'])
        e.update(selector_col_val='["woof"]')
        e2 = Email.create(account_id=c.account_id, name="EmailTwo", campaign_id=c.id)
        e2.update(selector_col_val='["heina"]')
        self.assertEqual(c.email_determiner({'dog': 'cat'}), None)


    def test_campaign_get_selector_import_data(self):
        stack = helpers.create_stack()
        l = List.find_by_id_anon(stack['list_id'])
        l.import_data = [{"dog": "cat"}, {"dog": "bird"}]
        l.save()
        c = Campaign.find_by_id_anon(stack['campaign_id'])
        c.selector_col_name = 'dog'
        c.save()
        e = Email.find_by_id_anon(stack['email_id'])
        e.selector_col_val = '["cat"]'
        e.save()
        self.assertEqual(c.get_selector_import_data(), [{'dog': 'cat'}])


if __name__ == '__main__':
    unittest.main()

