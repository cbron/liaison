from flask import (Blueprint, render_template, current_app, request,
                   flash, url_for, redirect, session, abort, jsonify)
from bs4 import BeautifulSoup
from flask.ext.login import login_required
from liaison.models.send import Send
from liaison.lib.utils import check_redis, get_cache, set_cache
from liaison.lib.extensions import redis_store as redis
from liaison.models.unsubscribe import Unsubscribe

pf = Blueprint('pf', __name__, url_prefix='/pf')

@pf.route('/unsubscribe/', methods=["POST"])
@pf.route('/unsubscribe/<string:hash_id>', methods=["GET"])
def unsubscribe(hash_id=None):
    found = send = unsubscribed = False
    send = Send.find_by_hash(hash_id)
    if send and send.message:
        email = send.message.get('to')[0].get('email')
        if email:
            Unsubscribe.create(email=email, account_id=send.account_id)
            found = True
    if not found:
        current_app.logger.info("Email Not Found for hash: %s "%hash_id)
    return render_template('pf/unsubscribe.html', found=found, unsubscribed=unsubscribed)


@pf.route('/vib/<string:hash_id>')
def vib(hash_id):
    redis.incr('vib_counter')
    redis_result = redis.get(hash_id)
    if redis_result:
        return redis_result
    send = Send.find_by_hash(hash_id)
    if send:
        data = send.message
        response = data['html']
        if response:
            soup = BeautifulSoup(response)
            if soup.find('span', 'preheader'):
                soup.find('span', 'preheader').extract()
                response = unicode(soup)

            if check_redis():
                set_cache(hash_id, response, 86400) # 1 day
            return response
    abort(404)


@pf.route('/vib/preview')
@login_required
def preview():
    return render_template('pf/preview.html')
