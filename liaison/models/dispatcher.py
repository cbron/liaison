import os
import time
import arrow
from sqlalchemy import Column, and_
from sqlalchemy.orm import relationship, deferred
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy import or_, and_
from flask import current_app
from datetime import datetime, timedelta

from liaison.models.basemodel import BaseMixin
from liaison.lib.extensions import db, redis_store as redis
from liaison.lib.tasks import prep_data_task, queue_emails_task, send_email_task
from liaison.models.send import Send


class Dispatcher(db.Model, BaseMixin):
    __tablename__ = 'dispatches'

    id = Column(db.Integer, primary_key=True)
    state = Column(db.Integer, default=0)
    send_at = Column(db.DateTime(timezone=True))
    percent_complete = Column(db.Integer, default=0)
    import_data = deferred(db.Column(JSON))
    adjusted_data = deferred(db.Column(JSON))
    queued_count = Column(db.Integer, default=0)
    sent_count = Column(db.Integer, default=0)
    skipped_count = Column(db.Integer, default=0)
    account_id = Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    user_id = Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    campaign_id = Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False)
    list_id = Column(db.Integer, db.ForeignKey('lists.id'), nullable=False)
    created_at = Column(db.DateTime(timezone=True), default=db.func.now())
    modified_at = Column(db.DateTime(timezone=True), default=db.func.now(), onupdate=db.func.now())

    account = relationship("Account",
        primaryjoin="Account.id==Dispatcher.account_id",
        foreign_keys="Dispatcher.account_id")
    user = relationship("User",
        primaryjoin="User.id==Dispatcher.user_id",
        foreign_keys="Dispatcher.user_id")
    list_ = relationship("List",
        primaryjoin="List.id==Dispatcher.list_id",
        foreign_keys="Dispatcher.list_id")
    campaign = relationship("Campaign",
        primaryjoin="Campaign.id==Dispatcher.campaign_id",
        foreign_keys="Dispatcher.campaign_id")
    sends = relationship("Send",
        primaryjoin="Dispatcher.id==Send.dispatcher_id",
        foreign_keys="Send.dispatcher_id")

    ###
    # State Machine
    #
    # 0. Pending - a dispatcher object is created
    # 1. Preparing data - run prep_data on dispatchers import_data
    # 2. After prep_data is finished it calls queue_emails which updates to stage 2 and
    #    creates the Send objects from the import_data. Is indempotent, can be run again.
    # 3. Sending Emails - stage 2 is done and so is dispatcher, now it moves it to stage 3 which is just
    #    the Send objects going out.
    # 4. We run a beat job to see if all sends are out, if they are we move to this 'complete' stage.
    #
    # Failures:
    #
    # 101: really means the import data failed in prep_data. Just call send() again to move forward, may need a data fix.
    # 102: somewhere in the middle of creating the Send objects we errored out, call send() which calls queue_emails again
    # Alt: After we are done we could call queue_emails again to double check all sends were created, and also
    #      beat Will run retry_mail() to retry any failed Send objects.
    #
    ###

    STATES = {
     0: 'Pending',
     1: 'Preparing Data',
     2: 'Queueing Emails',
     3: 'Sending Emails',
     10: 'Complete',
     15: 'Scheduled Send',
     100: 'Too soon for a resend, try again in a few minutes.',
     101: 'Failed to load data correctly. Please contact support.',
     102: 'Failed to queue all emails for sending. Please contact support.',
     103: 'Data not prepared correctly. Please contact support.',
     104: 'Invalid List Data.'
    }

    def current_state(self):
        if self.state == 15:
            dt = arrow.get(self.send_at)
            dt = dt.to('US/Arizona')
            return "%s %s" % (self.STATES.get(self.state), dt.humanize())
        else:
            return self.STATES.get(self.state) if self.STATES.get(self.state) else ''

    def send(self):
        if Dispatcher.check_for_recent(self.campaign_id, self.id):
            self.update(state=100)
        elif self.state==0 or self.state==15:
            prep_data_task.delay(self.id)
        else:
            current_app.logger.info("\n send cannot send in current state dispatch: %s, state: %s \n" % (self.id, self.state) )

    def next(self):
        if (self.state==0):
            self.send()
            print 'send()'
            return 'send()'
        elif (self.state==1):
            self.send()
            print 'send()'
            return 'send()'
        elif (self.state==2):
            queue_emails_task.delay(self.id)
            print 'queue_emails()'
            return 'queue_emails()'
        elif (self.state==3):
            print "Nothing to do"
            return 'Nothing to do'
        elif (self.state==10):
            print "Complete, nothing to do"
            return 'Complete, Nothing to do'
        elif (self.state==100):
            print "Nothing to do"
            return 'Nothing to do'
        elif (self.state==101):
            self.send()
            print 'send()'
            return 'send()'
        elif (self.state==102):
            self.expire_counts()
            queue_emails_task.delay(self.id)
            print 'queue_emails()'
            return 'queue_emails()'
        else:
            print "Bad state"
            return "Bad State"

    ###
    # 3 Primary State Machine Methods
    ###

    def prep_data(self):
        ''' Add a hash_id to every row. Thats it. '''
        self.update(state=1)
        new_data = []
        for index,customer in enumerate(self.import_data):
            if not customer.get('hash_id'):
                hash_id = os.urandom(32).encode('hex')
                while Send.find_by_hash(hash_id):
                  hash_id = os.urandom(32).encode('hex')
                customer['hash_id'] = hash_id
                new_data.append(customer)
        self.set_adjusted_data(new_data)
        queue_emails_task.delay(self.id)


    def queue_emails(self):
        ''' If first and last row have hash_id, create a task for each row, and incr_queued.
            Lastly, set the final queued_count and update state.
        '''
        self.update(state=2)
        try:
            data = self.adjusted_data
            if data and len(data) > 0 and type(data[0]) is dict:
                count = len(data) - 1
                if count >= 0 and (not data[0].get('hash_id') or not data[count].get('hash_id')):
                    self.update(state=103) # if first or last rows don't have hash_id, don't send any
                else:
                    for customer_data in data:
                        send_email_task.delay(self.id, customer_data)
                        self.incr_queued()
                    self.state=3
                    self.queued_count = self.get_queued() # final tally
                    self.save()
            else:
                self.update(state=104)
        except:
            self.update(state=102)
            raise


    def send_email_from_data(self, data):
        ''' Given a row of data, make sure this hash_id doesn't exist, and has email.
            If so, create a send and process it.
        '''
        hash_id = data.get('hash_id') # no dups, this way its idempotent
        send = Send.find_by_hash(hash_id)
        if send:
            # This is used for retry_for_lost_tasks and 102's. (Counts should have been expired.)
            # If half the sends are already sent then we mark those here, but we want send.process() to mark actual send.
            if send.attempts > 0:
                self.incr_sent() # else: it will handle itself below when calling process()
        else:
            email = self.campaign.email_determiner(data)
            if not email:
                self.incr_skipped()
            else:
                send = Send.create(
                    email_id=email.id,
                    dispatcher_id=self.id,
                    account_id=self.account_id,
                    data=data,
                    hash_id=hash_id
                )
                if send:
                    # If there is an email and the send was created...
                    send.process()
                else:
                    current_app.logger.info("\n send_email_from_data: send failed to create: %s \n" % hash_id )

    ###
    # Minor State Machine Methods
    ###


    def incr_queued(self):
        return redis.incr('dispatcher_%s_queued' % self.id)

    def get_queued(self):
        return redis.get('dispatcher_%s_queued' % self.id) or 0

    def incr_skipped(self):
        return redis.incr('dispatcher_%s_skipped' % self.id)

    def get_skipped(self):
        return redis.get('dispatcher_%s_skipped' % self.id) or 0

    def incr_sent(self):
        return redis.incr('dispatcher_%s_sent' % self.id)

    def get_sent(self):
        return redis.get('dispatcher_%s_sent' % self.id) or 0

    def expire_counts(self, timed=None):
        if timed:
            redis.expire('dispatcher_%s_percent' % self.id, timed)
            redis.expire('dispatcher_%s_queued' % self.id, timed)
            redis.expire('dispatcher_%s_sent' % self.id, timed)
            redis.expire('dispatcher_%s_skipped' % self.id, timed)
        else:
            redis.delete('dispatcher_%s_percent' % self.id)
            redis.delete('dispatcher_%s_queued' % self.id)
            redis.delete('dispatcher_%s_sent' % self.id)
            redis.delete('dispatcher_%s_skipped' % self.id)


    def get_percent_complete(self):
        '''
        This method calculates how many sends/queues exist and makes a percentage
        If percentage is 100 it saves the dispatch as completed
        If not its cached for 15 seconds
        '''
        if self.percent_complete == 100:
            return 100
        else:
            key = ('dispatcher_%s_percent' % self.id)
            if redis.exists(key):
                return int(redis.get(key))
            else:
                curr_sent_count = int(self.get_sent())
                queued = int(self.queued_count if self.queued_count else self.get_queued())
                processed = curr_sent_count + int(self.get_skipped())
                percent = int((float(processed)/queued) * 100) if queued > 0 else 0

                # Note: self.queued_count is only set after queuing is done
                # percent needs to be >98 to allow old/dead jobs to run an hour or two later, data updates then too.
                if percent > 98  and self.queued_count:
                    self.sent_count = curr_sent_count
                    self.skipped_count = int(self.get_skipped())
                    self.percent_complete = 100
                    self.state = 10
                    self.save()
                    self.expire_counts(86400)
                else:
                    self.update(sent_count=curr_sent_count)
                    redis.set(key, percent)
                    redis.expire(key, 15) # cache current percent done for 15 seconds
                return percent

    ###
    # Other Helper Methods
    ###


    def set_adjusted_data(self, new_data):
        self.update(adjusted_data=[]) # fixes flask-sqlalchemy bug (ticket open)
        self.update(adjusted_data=new_data)


    @classmethod
    def check_for_recent(cls, campaign_id, dispatch_id=None):
        time_limit = datetime.utcnow() - timedelta(minutes=2)
        if dispatch_id:
            return cls.query.filter(and_(cls.campaign_id==campaign_id, cls.created_at>time_limit, cls.id!=dispatch_id)).count() > 0
        else:
            return cls.query.filter(and_(cls.campaign_id==campaign_id, cls.created_at>time_limit)).count() > 0


    # If nothing in mail queue and percent < 100, maybe check unattempted.
    # Todo: automate this with beat
    def retry_for_lost_tasks(self):
        '''
        Note: Try retry_failures first before this.
        Situation:
            - Count is 100 queued, 88 sent, 2 skipped, and lets say 10 were lost silently
            - Now we are stuck at 88%, and _no_ jobs left in mail queue, no idea how many failed (but here its 10)
            - Or: redis goes down and we loose all counts
        Solution:
            - find all created sends, reset redis counts to that, then retry all and 10 lost tasks are queued
        '''
        if self.state == 3 or self.state == 10:
            already_sent_count = int(Send.query.filter_by(dispatcher_id=self.id).count())
            unattempted = int(Send.query.filter(and_(Send.dispatcher_id==self.id, Send.attempts==0)).count())
            self.expire_counts()
            self.update(percent_complete=0)
            self.queue_emails()
            time.sleep(.5)
            new_get_queued = int(self.get_queued())
            result = "\n Already Sent: %s \n Unattempted: %s \n" % (already_sent_count, unattempted)
            print result
            return result
        else:
            return "Can't find lost tasks in current state"
