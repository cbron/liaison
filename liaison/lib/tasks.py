import csv
import json
import time
import os
import traceback
from datetime import datetime, timedelta
from sqlalchemy import or_, and_
from celery.utils.log import get_task_logger

from liaison import app
from liaison.lib.extensions import make_celery

celery = make_celery(app)
logger = get_task_logger(__name__)

###
# Dispatcher state-machine methods
###


@celery.task()
def prep_data_task(dispatcher_id):
    ''' state 1'''
    from liaison.models.dispatcher import Dispatcher
    dispatcher = Dispatcher.find_by_id_anon(dispatcher_id)
    try:
        dispatcher.prep_data()
    except:
        dispatcher.update(state=101)
        raise


@celery.task()
def queue_emails_task(dispatcher_id):
    '''state 2'''
    from liaison.models.dispatcher import Dispatcher
    dispatcher = Dispatcher.find_by_id_anon(dispatcher_id)
    dispatcher.queue_emails()


@celery.task()
def send_email_task(dispatcher_id, data):
    ''' state 3 '''
    from liaison.models.dispatcher import Dispatcher
    dispatcher = Dispatcher.find_by_id_anon(dispatcher_id)
    dispatcher.send_email_from_data(data)


###
# Beat methods
###


@celery.task()
def send_scheduled():
    '''
        Run by celery beat
        Send scheduled dispatches
        cmd: celery -A liaison.lib.tasks.celery beat -l info -f {logdir}/beat.log
        mechanism: http://loose-bits.com/2010/10/distributed-task-locking-in-celery.html
    '''
    from liaison.models.dispatcher import Dispatcher
    from liaison.lib.extensions import redis_store as redis

    lock = redis.lock('beat_send_scheduled', timeout=(60*5))
    try:
        have_lock = lock.acquire(blocking=False)
        if have_lock:
            # start logic
            dispatches = Dispatcher.query.filter(and_(Dispatcher.send_at < datetime.utcnow(), Dispatcher.state == 15)).all()
            for dispatch in dispatches:
                dispatch.update(state=0)
                dispatch.send()
            # end logic
        else:
            redis.incr('lock_violation_send_scheduled')
    finally:
        if have_lock:
            lock.release()


@celery.task()
def retry_failures():
    '''
        Run by celery beat
        If there is a Send object and it was not sent or is failed, and is older than N minutes, resend it.
        celery -A liaison.lib.tasks.celery beat -l info -f {logdir}/beat.log
    '''
    from liaison.models.send import Send
    from liaison.lib.extensions import redis_store as redis

    lock = redis.lock('beat_retry_failues', timeout=(60*5))
    try:
        have_lock = lock.acquire(blocking=False)
        if have_lock:
            # start logic
            time_limit = datetime.utcnow() - timedelta(minutes=30)
            failed_sends = Send.query.filter(and_(Send.created_at < time_limit, or_(Send.state == 2, Send.state == 0), (Send.attempts < 3))).all()
            for send in failed_sends:
                retry_send.delay(send.id)
            # end logic
        else:
            redis.incr('lock_violation_retry_failures')
    finally:
        if have_lock:
            lock.release()


@celery.task()
def retry_send(send_id):
    from liaison.models.send import Send
    send = Send.find_by_id_anon(send_id)
    if send:
        logger.info("retry_send is resending: %s" % send.id)
        send.process()


###
# Helper Methods
###


@celery.task()
def run_import(list_id):
    from liaison.models.list import List
    from liaison.lib.aws import get_contents_as_string
    from liaison.lib.extensions import redis_store as redis

    key = 'list_%s_import' % list_id
    list_ = List.find_by_id_anon(list_id)
    if list_:
        filename = list_.filename
        logger.info("\n filename: %s \n" % str(filename))
        if "lists/" in filename:
            f = get_contents_as_string(filename)
        else:
            f = open(filename, 'rt')

        data = []
        try:
            data = [row for row in csv.DictReader(f.read().splitlines(), restkey='rk', restval='rv')]
            list_.import_data = data
            result = list_.save()
            if result:
                redis.set(key, 'Upload Successful.')
            else:
                redis.set(key, 'List failed to save, the data may be corrupted.')
        except Exception, e:
            logger.info("Error: import_failure_list: %s: \n %s" % (e, traceback.format_exc()) )
            redis.set(key, 'List failed to save, the data may be corrupted.')
            raise e
        finally:
            redis.expire(key, 1000)
            if not filename.startswith("imports/"):
                f.close()


@celery.task()
def run_blacklist_import(account_id, filename):
    from liaison.models.blacklist import Blacklist
    from liaison.lib.aws import get_contents_as_string
    from liaison.lib.extensions import redis_store as redis

    key = 'blacklist_import_%s' % account_id
    if "Users/" in filename:
        f = open(filename, 'rt')
    else:
        f = get_contents_as_string(filename)

    try:
        data = [row for row in csv.DictReader(f.read().splitlines(), restkey='rk', restval='rv')]
        ok_key = True
        for row in data:
            if ok_key:
                spellings = ('email', 'Email', 'email_address', 'Email_Address', 'email address', 'Email Address', 'EmailAddress')
                intersect = set(spellings).intersection(row.keys())
                intersect = intersect.pop() if intersect else None
                if intersect:
                    email = row.get(intersect)
                    reason = row.get('reason')
                    detail = row.get('detail')
                    Blacklist.insert(account_id, email, reason, detail)
                else:
                    ok_key = False
        if ok_key:
            redis.set(key, 'Upload Successful.')
    except Exception, e:
        logger.info("Error: import_failure_blacklist: %s: \n %s" % (e, traceback.format_exc()) )
        redis.set(key, 'Upload failed, the data may be corrupted.')
        raise e
    finally:
        redis.expire(key, 1000)
        if "Users/" in filename:
            f.close()

@celery.task()
def load_test():
    from liaison.models.misc import Misc
    import time
    time.sleep(0.33)
    Misc.do_stuff()


@celery.task()
def queue_load_test(count):
    for _ in range(count):
        load_test.delay()


@celery.task()
def end_to_end_task():
    from liaison.lib.utils import set_cache
    set_cache('end_to_end_test', 'worked', 5)

