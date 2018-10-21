import string
import random
import os
import traceback
from constants import ALLOWED_IMAGE_EXTENSIONS, ALLOWED_IMPORT_EXTENSIONS
from flask import flash, abort, request as __request
from functools import wraps
from flask_mail import Mail as __Mail
from flask_mail import Message as __Message
from redis import ConnectionError
from liaison.lib.extensions import mail, redis_store as redis


def allowed_image_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_IMAGE_EXTENSIONS

def allowed_import_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_IMPORT_EXTENSIONS

def id_generator(size=10, chars=string.ascii_letters + string.digits):
    # return base64.urlsafe_b64encode(os.urandom(size))
    return ''.join(random.choice(chars) for x in range(size))

def make_dir(dir_path):
    try:
        if not os.path.exists(dir_path):
            os.mkdir(dir_path)
    except Exception, e:
        raise e

def flash_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            flash(u"Error in the %s field - %s" % (
                getattr(form, field).label.text,
                error
            ))

def print_list(l, name):
    response = ""
    for i,item in enumerate(l):
        if (i + 1) < len(l):
            response += ("%s, " % getattr(item, name))
        else:
            response += ("%s" % getattr(item, name))
    return response

def email_exception(exception):
    '''Handles the exception message from Flask by sending an email to the
    recipients defined in the call to mail_on_500.
    '''
    msg = __Message("[Liaison:Exception]: %s" % exception.message,
        recipients=['']
    )
    msg_contents = [
        'Traceback:',
        '='*80,
        traceback.format_exc(),
    ]
    msg_contents.append('\n')
    msg_contents.append('Request Information:')
    msg_contents.append('='*80)
    environ = __request.environ
    environkeys = sorted(environ.keys())
    for key in environkeys:
        msg_contents.append('%s: %s' % (key, environ.get(key)))
    msg.body = '\n'.join(msg_contents) + '\n'
    mail.send(msg)

def limit_content_length(max_length):
    """ This takes the place of MAX_CONTENT_LENGTH,
    as different views need different values. """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            cl = __request.content_length
            if cl is not None and cl > max_length:
                kwargs['file_size_ok'] = False
            else:
                kwargs['file_size_ok'] = True
            return f(*args, **kwargs)
        return wrapper
    return decorator

##
# Redis methods
##

def get_cache(key):
    if check_redis():
        return redis.get(key)

def set_cache(key, data, expiring=None):
    if check_redis():
        response = redis.set(key, data)
        if expiring:
            redis.expire(key, expiring)
        return response

def setnx_cache(key, data, expiring=None):
    if check_redis():
        response = redis.setnx(key, data)
        if expiring:
            redis.expire(key, expiring)
        return response

def del_cache(key):
    if check_redis():
        return redis.delete(key)

def get_count(key):
    if check_redis():
        return redis.llen(key) or 0

def check_redis():
    try:
        redis.ping()
        return True
    except ConnectionError:
        return False
