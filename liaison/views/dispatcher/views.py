from flask import Blueprint, render_template, request, flash
from flask.ext.login import login_required
from liaison.lib.utils import check_redis
from liaison.models.dispatcher import Dispatcher

dispatcher = Blueprint('dispatcher', __name__, url_prefix='/dispatcher')


@dispatcher.route('/', methods=['GET'])
@login_required
def index():
    if check_redis():
        redis = True
    else:
        redis = False
        flash('Cache is offline, percentage complete may be incorrect, please contact support.', 'warning')
    page = int(request.args.get('page', 1))
    pagination = Dispatcher.find_all_desc().paginate(page=page, per_page=20)
    return render_template('dispatcher/index.html', pagination=pagination, redis=redis)
