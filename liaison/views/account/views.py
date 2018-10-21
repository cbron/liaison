from flask import (Blueprint, render_template, current_app, request,
                   flash, url_for, redirect, session, abort, jsonify)
from flask.ext.login import fresh_login_required, login_required, login_user, current_user, logout_user, confirm_login
import json

from forms import FooterForm, DefaultFromEmail
from liaison.lib.utils import flash_errors, get_cache, set_cache, check_redis
from liaison.lib.extensions import db, redis_store as redis
from liaison.models.account import Account
from liaison.models.send import Send
from liaison.models.unsubscribe import Unsubscribe
from liaison.lib.tasks import end_to_end_task

account = Blueprint('account', __name__, url_prefix='/accounts')

# Fix antipattern
DEFAULT_FOOTER = "<p><a href=\"%7B%7BUNSUBSCRIBE_LINK%7D%7D\">Unsubscribe</a></p>\n<p><a href=\"%7B%7BVIEW_IN_BROWSER_LINK%7D%7D\">View In Browser</a></p>\n"

@account.route('/', methods=['GET'])
@login_required
def index():
    unsub_count = Unsubscribe.find_all().count()
    form=DefaultFromEmail(obj=current_user.account)
    return render_template('account/index.html',
        user=current_user,
        unsub_count=unsub_count,
        form=form,
        account=current_user.account,
        auto_text=current_user.account.auto_text)


@account.route('/footer', methods=['GET', 'POST'])
@fresh_login_required
def footer():
    account = current_user.account
    form = FooterForm(obj=account)
    if not form.footer_html.data:
        form.footer_html.data = DEFAULT_FOOTER
    if request.method == 'POST':
        if form.validate_on_submit():
            account.update(**{
                'footer_html': form.footer_html.data,
                'footer_text': form.footer_text.data
            })
            flash("Updated")
        else:
            flash_errors(form)
    return render_template('account/footer.html', user=current_user, form=form, auto_text=account.auto_text)


@account.route('/unsubscribes.csv', methods=['GET'])
@login_required
def download_unsubscribes():
    return Unsubscribe.generate_csv()


@account.route('/submit_default_from', methods=['POST'])
@login_required
def submit_default_from():
    form = DefaultFromEmail(request.form)
    if form.validate_on_submit():
        current_user.account.update(**{
            'default_from_email': form.default_from_email.data
        })
        flash("Default From address updated")
    else:
        flash_errors(form)
    return redirect(url_for('account.index'))


@account.route('/auto_text', methods=['POST'])
@login_required
def update_auto_text():
    result = request.form.get("auto_text")
    current_user.account.update(auto_text=result)
    return jsonify({'auto_text': result}), 200
