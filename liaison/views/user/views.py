import os
import hashlib
from datetime import datetime
import markdown
from flask import (Blueprint, render_template, current_app, request, jsonify,
                   flash, url_for, redirect, session, abort, Markup)
from flask.ext.mail import Message
from flask.ext.login import login_required, fresh_login_required, login_user, current_user
from flask.ext.security import login_required

from liaison.models.user import User
from liaison.lib.extensions import db, mail
from liaison.lib.utils import make_dir, flash_errors, get_cache, set_cache
from forms import ProfileForm, SubscribeForm, EulaForm

user = Blueprint('user', __name__)


@user.route('/', methods=['GET'])
@login_required
def index():
    if not current_user.accepted_terms:
        return redirect(url_for('user.terms'))
    return render_template('user/home.html', user=current_user)


@user.route('/guide', methods=['GET'])
@login_required
def guide():
    return render_template('user/guide.html')


@user.route('/spam', methods=['GET'])
@login_required
def spam():
    return render_template('user/spam.html')


@user.route('/contact', methods=['GET'])
@login_required
def contact():
    return render_template('user/contact.html')


@user.route('/terms', methods=['GET', 'POST'])
@login_required
def terms():
    form = EulaForm(request.form)
    if request.method == 'POST':
        if form.validate_on_submit():
            current_user.update(accepted_terms=1)
            flash("Terms Of Service Accepted")
            return redirect(url_for('user.index'))

    accepted = current_user.accepted_terms
    key = 'liaison_eula'
    content = get_cache(key)

    if content:
        content = Markup(content)
    else:
        path = os.path.abspath(os.path.join(current_app.config.get('PROJECT_ROOT'), '..', 'files', 'terms.md'))
        f = open(path, 'r')
        content = f.read()
        content = Markup(markdown.markdown(content))
        set_cache(key, content, 3600)

    return render_template('user/terms.html', content=content, form=form, accepted=accepted)


@user.route('/profile/', methods=['GET', 'POST'])
@fresh_login_required
def profile():
    user = User.query.filter_by(email=current_user.email).first_or_404()
    form = ProfileForm(obj=user)

    if request.method == 'POST':
        if form.validate_on_submit():
            user.save()
            flash('Profile updated.', 'success')

    return render_template('user/profile.html', user=user, form=form)


@user.route('/ping')
def ping():
    return jsonify({'ping':'ok'}), 200

@user.route('/app_status')
def status():
    db = False
    if User.query.first():
        db=True

    set_cache('status-check', 1, 10)
    cache = False
    if get_cache('status-check'):
        cache = True

    if db and cache:
        return jsonify({'status':'ok'}), 200
    else:
        return jsonify({'cache': cache, 'db': db}), 503

