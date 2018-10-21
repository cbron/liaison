import csv
from flask import (Blueprint, render_template, current_app, request,
                   flash, url_for, redirect, session, abort, jsonify)
from flask.ext.login import fresh_login_required, login_required, login_user, current_user, logout_user, confirm_login
from liaison.lib.utils import flash_errors, limit_content_length, allowed_import_file, get_cache, del_cache
from liaison.lib.constants import ALLOWED_IMPORT_EXTENSIONS
from forms import  BlacklistForm
from liaison.models.blacklist import Blacklist
from liaison.lib.tasks import run_blacklist_import

blacklist = Blueprint('blacklist', __name__, url_prefix='/blacklist')

@blacklist.route('/', methods=['GET'])
@login_required
def index():
    key = 'blacklist_import_%s' % current_user.account_id
    if get_cache(key):
        flash(get_cache(key), 'warning')
        del_cache(key)
    form = BlacklistForm()
    page = int(request.args.get('page', 1))
    pagination = Blacklist.find_all_desc().paginate(page=page, per_page=20)
    return render_template('blacklist/index.html', pagination=pagination, form=form)


@blacklist.route('/upload', methods=['POST'])
@login_required
@limit_content_length(100 * 1024 * 1024)
def upload(file_size_ok):
    '''import a contact file to uploads/imports/{account_id}/{list_id}/filename '''
    file = request.files['file']
    if not file_size_ok:
        flash("File is limited to 100MB. Contact support for more info.", 'warning')
        return redirect(url_for('blacklist.index'))
    if file and allowed_import_file(file.filename):
        a_id = current_user.account.id
        fname = Blacklist.save_file(a_id, file)
        run_blacklist_import.delay(a_id, fname)
        flash('File uploaded. After processing, data will be displayed below.')
    else:
        flash("File type not allowed, Please upload files with extensions: %s" % ", ".join(ALLOWED_IMPORT_EXTENSIONS), 'warning')
    return redirect(url_for('blacklist.index'))
