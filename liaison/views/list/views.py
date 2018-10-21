from flask import (Blueprint, render_template, request, flash, url_for, redirect)
from flask.ext.login import login_required, login_user, current_user, logout_user, confirm_login, login_fresh

from forms import ListForm
from liaison.models.list import List
from liaison.lib.utils import allowed_import_file, flash_errors, limit_content_length, get_cache, del_cache
from liaison.lib.constants import ALLOWED_IMPORT_EXTENSIONS
from liaison.lib.tasks import run_import

list_ = Blueprint('list_', __name__, url_prefix='/lists')


@list_.route('/', methods=['GET'])
@login_required
def index():
    form = ListForm()
    page = int(request.args.get('page', 1))
    pagination = List.find_all_desc().paginate(page=page, per_page=20)
    return render_template('list/index.html', user=current_user, pagination=pagination, form=form)


@list_.route('/<int:list_id>', methods=['GET'])
@login_required
def edit(list_id):
    l = List.find_by_id(list_id)
    if l:
        key = 'list_%s_import' % list_id
        if get_cache(key):
            flash(get_cache(key), 'warning')
            del_cache(key)
        random_data = l.random_data_sample()
        length =  l.total_send_count()
        form = ListForm(obj=l)
        return render_template('list/edit.html', form=form, list=l, data=random_data, length=length)
    else:
        flash('List not found')
        return redirect(url_for('list_.index'))


@list_.route('/<int:list_id>/upload_file', methods=['POST'])
@login_required
@limit_content_length(100 * 1024 * 1024)
def upload_file(list_id, file_size_ok):
    '''import a contact file to uploads/imports/{account_id}/{list_id}/filename '''
    file = request.files['file']
    if not file_size_ok:
        flash("File is limited to 100MB. Contact support for more info.", 'warning')
        return redirect(url_for('list_.edit', list_id=list_id))
    l = List.find_by_id(list_id)
    if file and allowed_import_file(file.filename):
        l.filename = List.save_file(file, list_id, current_user.account.id)
        l.save()
        run_import.delay(list_id)
        flash('File uploaded. Data may take some time to load, when finished it will be displayed below.')
    else:
        flash("File type not allowed, Please upload files with extensions: %s" % ", ".join(ALLOWED_IMPORT_EXTENSIONS), 'warning')
    return redirect(url_for('list_.edit', list_id=list_id))


@list_.route('/submit', methods=['POST'])
@list_.route('/<int:list_id>/submit', methods=['POST'])
@login_required
def submit(list_id=None):
    l = List.find_by_id(list_id)
    form = ListForm(request.form)

    if form.validate_on_submit():
        if l:
            l.update(name=form.name.data)
            flash('List Updated')
            return redirect(url_for('list_.index'))
        else:
            l = List.create(
                name=form.name.data,
                account_id=current_user.account_id
            )
            if l:
                flash('List Created')
                return redirect(url_for('list_.edit', list_id=l.id))
    else:
        page = int(request.args.get('page', 1))
        flash_errors(form)

    pagination = List.find_all_desc().paginate(page=page, per_page=20)
    return render_template('list/index.html', form=form, list=l, user=current_user, pagination=pagination)


@list_.route('/<int:list_id>/delete', methods=['POST'])
@login_required
def delete(list_id):
    l = List.find_by_id(list_id)
    if l:
        if l.campaigns:
            flash('Cannot delete, attached to one or more campaigns', 'warning')
            return redirect(url_for('list_.index'))
        try:
            l.delete()
            flash('List deleted')
        except Exception, e:
            flash('Exception: %s'%e)
    return redirect(url_for('list_.index'))

