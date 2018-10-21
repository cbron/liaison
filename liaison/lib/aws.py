import boto
from boto.s3.key import Key
import StringIO
from liaison.lib.extensions import db, s3
from flask import current_app

# S3 Methods: https://boto.readthedocs.org/en/latest/ref/s3.html

PRIVATE_BUCKET_NAME = ''
PUBLIC_BUCKET_NAME = ''


def upload_email_image(acct_id, campaign_id, email_id, filename, file):
    path = "%s/images/emails/%s/%s/%s/%s" % (get_env(), acct_id, campaign_id, email_id, filename)
    result = s3_set_contents_from_file(path, file, 0)
    return s3_generate_url(path, 0)


def upload_list(acct_id, list_id, filename, file):
    path = "%s/lists/%s/%s/%s" % (get_env(), acct_id, list_id, filename)
    result = s3_set_contents_from_file(path, file, 1)
    return path


def upload_blacklist(acct_id, filename, file):
    path = "%s/blacklists/%s/%s" % (get_env(), acct_id, filename)
    result = s3_set_contents_from_file(path, file, 1)
    return path

# Helpers

def get_env():
    return 'dev' if current_app.debug else 'prod'


def s3_set_contents_from_file(path, file, private=1):
    '''
    `file` is a file descriptor
    '''
    bucket = s3.get_bucket(PRIVATE_BUCKET_NAME) if private else s3.get_bucket(PUBLIC_BUCKET_NAME)
    k = Key(bucket)
    k.key = path
    k.set_metadata('Content-Type', file.content_type)
    file.seek(0)
    return k.set_contents_from_file(file)


def s3_generate_url(path, private=1):
    bucket = s3.get_bucket(PRIVATE_BUCKET_NAME) if private else s3.get_bucket(PUBLIC_BUCKET_NAME)
    k = Key(bucket)
    k.key = path
    return k.generate_url(expires_in=0, query_auth=False)


def get_contents_as_string(path, private=1):
    bucket = s3.get_bucket(PRIVATE_BUCKET_NAME) if private else s3.get_bucket(PUBLIC_BUCKET_NAME)
    k = Key(bucket)
    k.key = path
    f = k.get_contents_as_string(headers=None, cb=None, num_cb=10, torrent=False)
    return StringIO.StringIO(f)
