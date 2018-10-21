from flask import (Blueprint, render_template, current_app, request,
                   flash, url_for, redirect, session, abort, jsonify)
from flask.ext.login import fresh_login_required, login_required, login_user, current_user, logout_user, confirm_login
from flask.ext.security import roles_accepted
import json

from forms import EndToEndForm
from liaison.lib.utils import check_redis, get_cache, get_count
from liaison.lib.extensions import db, redis_store as redis
from liaison.models.send import Send
from liaison.models.dispatcher import Dispatcher
from liaison.models.misc import Misc
from liaison.lib.tasks import end_to_end_task

admin = Blueprint('admin', __name__, url_prefix='/app_admin')



@admin.route('/', methods=['GET'])
@login_required
@roles_accepted('super')
def admin_index():
    redis_status = check_redis()
    default = get_count('default')
    mail = get_count('mail')
    beat = get_count('beat')
    dispatcher = get_count('dispatcher')
    vib_counter = get_cache('vib_counter')
    beat_retry_failues = get_cache('beat_retry_failues')
    beat_send_scheduled = get_cache('beat_send_scheduled')
    lock_violation_send_scheduled = get_cache('lock_violation_send_scheduled')
    lock_violation_retry_failures = get_cache('lock_violation_retry_failures')

    return render_template('admin/index.html',
        default=default,
        mail=mail,
        dispatcher=dispatcher,
        redis_status=redis_status,
        beat=beat,
        vib_counter=vib_counter,
        beat_retry_failues=beat_retry_failues,
        lock_violation_send_scheduled=lock_violation_send_scheduled,
        beat_send_scheduled=beat_send_scheduled,
        lock_violation_retry_failures=lock_violation_retry_failures)


@admin.route('/dispatches', methods=['GET'])
@login_required
@roles_accepted('super')
def dispatches():
    dispatches = Dispatcher.query.order_by('id desc').limit(100)
    return render_template('admin/dispatches.html', dispatches=dispatches)


@admin.route('/dispatches/<int:d_id>', methods=['GET'])
@login_required
@roles_accepted('super')
def dispatch(d_id):
    d = Dispatcher.find_by_id_anon(d_id)
    return render_template('admin/dispatch.html', d=d, r_up=check_redis())


@admin.route('/dispatches/<int:d_id>/next', methods=['POST'])
@login_required
@roles_accepted('super')
def dispatch_next(d_id):
    d = Dispatcher.find_by_id_anon(d_id)
    response = d.next()
    flash(response)
    return redirect(url_for('admin.dispatch', d_id=d.id))


@admin.route('/dispatches/<int:d_id>/retry_for_lost_tasks', methods=['POST'])
@login_required
@roles_accepted('super')
def dispatch_retry_for_lost_tasks(d_id):
    d = Dispatcher.find_by_id_anon(d_id)
    response = d.retry_for_lost_tasks()
    flash(response)
    return redirect(url_for('admin.dispatch', d_id=d.id))


@admin.route('/load_test', methods=['GET'])
@login_required
@roles_accepted('super')
def load_test():
    from liaison.lib.tasks import queue_load_test
    count = int(request.args.get('count') or 0)
    if count > 0:
        queue_load_test.delay(count)
        flash("%s queued" % count)
        return redirect(url_for('admin.admin_index'))
    redis.expire('load_test', 60)
    return render_template('admin/load_test.html', count=count)


@admin.route('/end_to_end', methods=['GET', 'POST'])
@login_required
@roles_accepted('super')
def end_to_end():
    if request.method == 'POST':
        end_to_end_task.delay()
        return redirect(url_for('admin.end_to_end'))
    form = EndToEndForm()
    status = get_cache('end_to_end_test')
    return render_template('admin/end_to_end.html', form=form, status=status)


@admin.route('/sends', methods=['GET'])
@admin.route('/sends/<int:dispatch_id>', methods=['GET'])
@login_required
@roles_accepted('super')
def sends(dispatch_id=None):
    count=request.args.get('count') or 100
    if dispatch_id:
        sends = Send.query.filter_by(dispatcher_id=dispatch_id).order_by('id desc').limit(count)
    else:
        sends = Send.query.order_by('id desc').limit(count)
    return render_template('admin/sends.html', sends=sends)


@admin.route('/send_detail/<string:hash_id>', methods=['GET'])
@admin.route('/send_detail/<int:id>', methods=['GET'])
@login_required
@roles_accepted('super')
def send_details(hash_id=None,id=None):
    if hash_id:
        send = Send.find_by_hash(hash_id)
    else:
        send = Send.find_by_id_anon(id)
    return render_template('admin/send_detail.html', send=send)


@admin.route('/status')
@login_required
@roles_accepted('super')
def status():
    """Check the database and cache, and report their status."""
    services = {}
    code = 200

    # DB
    if isinstance(Account.query.all(), list):
        services['db'] = 'ok'
    else:
        services['db'] = 'offline'
        code = 503

    # Cache. Offline is ok on dev. To test use SimpleCache instead of NullCache.
    redis.set('status-chck', 'a-ok')
    redis.expire('status-chck', 2)
    if redis.get('status-chck') == 'a-ok':
        services['cache'] = 'ok'
    else:
        services['cache'] = 'offline'
        code = 503
    services['status_code'] = code
    services['redis-online'] = check_redis()

    return jsonify(services), code


@admin.route('/err', methods = ['GET'])
@login_required
@roles_accepted('super')
def error_out():
    raise 1/0
    return jsonify({})
