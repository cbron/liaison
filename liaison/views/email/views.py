import json
import random
from flask import (Blueprint, render_template, current_app, request,
                   flash, url_for, redirect, session, abort, jsonify)
from flask.ext.login import login_required, login_user, current_user, logout_user, confirm_login, login_fresh
from werkzeug import secure_filename

from liaison.lib.utils import allowed_image_file, allowed_import_file, flash_errors, limit_content_length
from liaison.models.email import Email
from liaison.models.list import List
from liaison.models.template import Template
from liaison.models.campaign import Campaign
from liaison.lib.aws import upload_email_image
from forms import NewEmailForm, EditEmailForm

email = Blueprint('email', __name__, url_prefix='/campaigns/<int:campaign_id>/emails')


@email.route('/new', methods=['GET'])
@login_required
def new(campaign_id=None):
    campaign = Campaign.find_by_id(campaign_id) if campaign_id else None
    if not campaign:
        return abort(404)
    email = None
    form = NewEmailForm()
    templates = Template.get_all_choices()
    keys = []
    if campaign.list_id:
        keys = campaign.list_.get_import_data_keys()
        form.selector_col_val.choices = campaign.list_.get_unique_col_values(campaign.selector_col_name, True)
        if email and email.selector_col_val:
            form.selector_col_val.data = email.selector_col_val
    return render_template('email/new.html', form=form, campaign=campaign, email=email, keys=keys, templates=templates)


@email.route('/create', methods=['POST'])
@email.route('/<int:email_id>/create', methods=['POST'])
@login_required
def create(campaign_id=None):
    campaign = Campaign.find_by_id(campaign_id) if campaign_id else None
    if not campaign:
        return abort(404)

    form = NewEmailForm(request.form)

    if campaign.list_id:
        keys = campaign.list_.get_import_data_keys()
        form.selector_col_val.choices = campaign.list_.get_unique_col_values(campaign.selector_col_name, True)
    else:
        keys = []

    templates = Template.get_all_choices()

    if form.validate_on_submit():
        params = {
            'name': form.name.data,
            'subject': form.subject.data,
            'preheader': form.preheader.data,
            'selector_col_val': form.selector_col_val.data
        }
        if form.template.data:
            params['html'] = Template.get_html(form.template.data)
        params['account_id']=current_user.account_id
        params['campaign_id']=campaign.id
        email = Email.create(**params)
        if email:
            flash('Email Created')
            return redirect(url_for('email.edit', email_id=email.id, campaign_id=campaign.id))
    flash_errors(form)
    return render_template('email/new.html', form=form, campaign=campaign, keys=keys, templates=templates)


@email.route('/<int:email_id>/edit', methods=['GET'])
@login_required
def edit(campaign_id=None, email_id=None):
    campaign = Campaign.find_by_id(campaign_id) if campaign_id else None
    if not campaign:
        return abort(404)

    email = Email.find_by_id(email_id)
    if not email:
        flash('Email not found')
        return redirect(url_for('campaign.edit', campaign_id=campaign.id))

    form = EditEmailForm(obj=email)
    keys = []
    if campaign.list_id:
        keys = campaign.list_.get_import_data_keys()
        form.selector_col_val.choices = campaign.list_.get_unique_col_values(campaign.selector_col_name, True)
        if email and email.selector_col_val:
            form.selector_col_val.data = email.selector_col_val
    return render_template('email/edit.html', form=form, campaign=campaign, email=email, keys=keys, auto_text=current_user.account.auto_text)


@email.route('/update', methods=['POST'])
@email.route('/<int:email_id>/update', methods=['POST'])
@login_required
def update(campaign_id=None, email_id=None):
    campaign = Campaign.find_by_id(campaign_id) if campaign_id else None
    if not campaign:
        return abort(404)
    email = Email.find_by_id(email_id)
    if not email:
        return abort(404)

    form = EditEmailForm(request.form)
    if campaign.list_id:
        keys = campaign.list_.get_import_data_keys()
        form.selector_col_val.choices = campaign.list_.get_unique_col_values(campaign.selector_col_name, True)
    else:
        keys = []

    if form.validate_on_submit():
        params = {
            'name': form.name.data,
            'subject': form.subject.data,
            'preheader': form.preheader.data,
            'html': form.html.data,
            'text': form.text.data,
            'selector_col_val': json.dumps(filter(None,form.selector_col_val.data))
        }
        email.update(**params)
        flash('Email Updated')
        return redirect(url_for('email.edit', email_id=email.id, campaign_id=campaign.id))

    flash_errors(form)
    return render_template('email/new.html', form=form, campaign=campaign, email=email, keys=keys)


@email.route('/<int:email_id>/preview', methods=['GET'])
@login_required
def preview(campaign_id=None, email_id=None):
    campaign = Campaign.find_by_id(campaign_id) if campaign_id else None
    if not campaign:
        return abort(404)
    email = Email.find_by_id(email_id)
    if not email:
        return abort(404)
    list_id = email.campaign.list_id if email.campaign.list_id else request.args.get('list_id', None)
    l = List.find_by_id(list_id)
    if l:
        s_data = campaign.get_selector_import_data()
        rando_set = range(len(s_data))
        if rando_set:
            rando = random.sample(rando_set, 1)[0]
            rando = s_data[rando]
            html = email.render_html_attr(rando, 'preview') # fake hash id
            if not email.text:
                email.text = 'No content.'
            text = email.render_text_attr(rando, 'preview')
            return render_template('email/preview.html', email=email, html=html, text=text, email_id=email_id, campaign_id=campaign_id)
        else:
            flash("No valid data available for preview. You may need to set a selector value.")
            return redirect(url_for('email.edit', email_id=email_id, campaign_id=campaign.id))
    else:
        flash("Preview is not available until a list is selected.")
        return redirect(url_for('email.edit', email_id=email_id, campaign_id=campaign.id))


@email.route('/<int:email_id>/upload_image', methods=['POST'])
@login_required
@limit_content_length(2 * 1024 * 1024)
def image_upload(file_size_ok, campaign_id=None, email_id=None):
    email = Email.find_by_id(email_id)
    campaign = Campaign.find_by_id(campaign_id)
    if campaign and email and current_user.account_id == campaign.account_id and current_user.account_id == email.account_id:
        file = request.files['image_file']
        if not file_size_ok:
            return jsonify({'error': 'File is too large.' })
        if file and allowed_image_file(secure_filename(file.filename.lower())):
            filename = secure_filename(file.filename)
            url = upload_email_image(current_user.account_id, campaign_id, email_id, filename, file)
            return jsonify({ 'link': url})
        else:
            return jsonify({'error': 'Invalid image type.'})
    return jsonify({'error': 'Could not upload image.' })


@email.route('/<int:email_id>/delete', methods=['POST'])
@login_required
def delete(campaign_id, email_id):
    email = Email.find_by_id(email_id)
    if email and email.campaign_id == campaign_id:
        if email.sends:
            flash("Email has been sent, and therefore cannot be deleted.")
        else:
            try:
                email.delete()
                flash('Email deleted')
            except Exception, e:
                flash('Exception: %s'%e)
    else:
        flash("Email not found")
    return redirect(url_for('campaign.edit', campaign_id=campaign_id))

