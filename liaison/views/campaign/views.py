import json
import random
from datetime import datetime, date, timedelta
from flask import (Blueprint, render_template, current_app, request,
                   flash, url_for, redirect, session, abort, jsonify)
from flask.ext.login import login_required, login_user, current_user, logout_user, fresh_login_required

from liaison.lib.utils import flash_errors, print_list
from liaison.models.email import Email
from liaison.models.list import List
from liaison.models.campaign import Campaign
from liaison.models.dispatcher import Dispatcher
from forms import NewCampaignForm, CampaignForm, CampaignListForm, DispatcherForm, DispatcherConfirmForm

campaign = Blueprint('campaign', __name__, url_prefix='/campaigns')
DT_FORMAT = '%Y-%m-%dT%H:%M'

@campaign.route('/', methods=['GET'])
@login_required
def index():
    page = int(request.args.get('page', 1))
    pagination = Campaign.find_all_desc().paginate(page=page, per_page=20)
    form = NewCampaignForm()
    return render_template('campaign/index.html', user=current_user, pagination=pagination, form=form)


@campaign.route('/create', methods=['POST'])
@login_required
def create(campaign_id=None):
    form = NewCampaignForm(request.form)
    if form.validate_on_submit():
        params = {
            'name': form.name.data,
            'account_id': current_user.account_id
        }
        c = Campaign.create(**params)
        if c:
            flash('Campaign Created')
            return redirect(url_for('campaign.edit', campaign_id=c.id))
        flash_errors(form)
    return redirect(url_for('campaign.index'))


@campaign.route('/<int:campaign_id>/edit', methods=['GET'])
@login_required
def edit(campaign_id=None):
    if campaign_id:
        campaign = Campaign.find_by_id(campaign_id)
        if campaign:
            form = CampaignForm(obj=campaign)
            form = setup_campaign_select_choices(form, campaign.list_id) if campaign.list_id else form
            if not form.from_email_ov.data:
                form.from_email_ov.data = current_user.account.default_from_email
        else:
            flash('Campaign not found')
            return redirect('/campaigns/')

    list_form = CampaignListForm()
    list_form.list_id.choices = [('','')] + [(str(h.id), h.name) for h in List.find_all()]
    return render_template('campaign/edit.html', form=form, campaign=campaign, list_form=list_form, emails=campaign.emails)


@campaign.route('/<int:campaign_id>/update', methods=['POST'])
@login_required
def update(campaign_id=None):
    form = CampaignForm(request.form)
    list_id = request.form.get('list_id', None)
    form = setup_campaign_select_choices(form, list_id)
    campaign = Campaign.find_by_id(campaign_id)
    if form.validate_on_submit():
        params = {
            'name': form.name.data,
            'from_email_dd': form.from_email_dd.data,
            'from_name_dd': form.from_name_dd.data,
            'reply_to_dd': form.reply_to_dd.data,
            'to_email_dd': form.to_email_dd.data,
            'to_name_dd': form.to_name_dd.data,
            'from_email_ov': form.from_email_ov.data,
            'from_name_ov': form.from_name_ov.data,
            'reply_to_ov': form.reply_to_ov.data,
            'to_email_ov': form.to_email_ov.data,
            'to_name_ov': form.to_name_ov.data,
            'selector_col_name': form.selector_col_name.data
        }
        if campaign.selector_col_name and campaign.selector_col_name != params['selector_col_name']:
            flash("Selector column changed, all emails have had selector values removed.", 'warning')
            for email in campaign.emails:
                email.update(selector_col_val=None)
        campaign.update(**params)
        flash('Campaign Updated')
        return redirect(url_for('campaign.edit', campaign_id=campaign.id))
    flash_errors(form)
    list_form = CampaignListForm()
    list_form.list_id.choices = [('','')] + [(str(h.id), h.name) for h in List.find_all()]
    return render_template('campaign/edit.html', form=form, campaign=campaign, list_form=list_form)


@campaign.route('/<int:campaign_id>/list_update', methods=['POST'])
@login_required
def list_update(campaign_id=None):
    campaign = Campaign.find_by_id(campaign_id)
    list_id = request.form.get('list_id')
    l = List.find_by_id(list_id) if list_id else None
    acct_id = current_user.account_id

    if campaign and acct_id == campaign.account_id and l and acct_id == l.account_id:
        campaign.update(list_id=list_id)
        return jsonify({'success': 'true'})
    else:
        return jsonify({'success': 'false'})


@campaign.route('/<int:campaign_id>/delete', methods=['POST'])
@login_required
def delete(campaign_id):
    campaign = Campaign.find_by_id(campaign_id)
    if campaign:
        if campaign.emails or campaign.dispatcher:
            flash('This campaign has emails or a dispatch attached to it, and cannot be deleted', 'warning')
        else:
            try:
                campaign.delete()
                flash('Campaign deleted')
            except Exception, e:
                flash('Exception: %s'%e)
    return redirect(url_for('campaign.index'))

###########
# dispatcher
###########

@campaign.route('/<int:campaign_id>/dispatcher', methods=['GET'])
@fresh_login_required
def dispatcher(campaign_id):
    campaign = Campaign.find_by_id(campaign_id) if campaign_id else None
    if not campaign:
        return abort(404)

    if not current_user.accepted_terms:
        flash("You must accept the terms of this site before you can send emails.", 'warning')
        return redirect(url_for('user.terms'))

    if not current_user.account.active:
        flash("Your account is inactive, please contact support.", 'warning')
        return redirect(url_for('campaign.edit', campaign_id=campaign.id))

    if not current_user.account.api_key:
        flash("Your account does not have an api key, please contact support.", 'warning')
        return redirect(url_for('campaign.edit', campaign_id=campaign.id))

    # Must have list and emails
    if not campaign.list_id or not campaign.emails:
        flash("A campaign must have an associated list and at least one email.", 'warning')
        return redirect(url_for('campaign.edit', campaign_id=campaign.id))

    # List must have data
    if not campaign.list_.total_send_count() > 0:
        flash("List contains no data, cannot begin send process.", 'warning')
        return redirect(url_for('campaign.edit', campaign_id=campaign.id))

    # Must have footer
    if not current_user.account.footer_html:
        flash("This account does not have a footer, please add one before you initiate a send.", 'warning')
        return redirect(url_for('campaign.edit', campaign_id=campaign.id))

    # Don't allow dup sends
    if Dispatcher.check_for_recent(campaign.id):
        flash("To safeguard from duplication, a campaign may not be sent more than once in a 2 minute span.", 'warning')
        return redirect(url_for('campaign.edit', campaign_id=campaign.id))

    if campaign.selector_missing():
        flash("There is more than one email, but no selector. Please choose a selector or have only one email.", 'warning')
        return redirect(url_for('campaign.edit', campaign_id=campaign.id))


    valid_keys, bad_key = campaign.check_email_keys()
    selector_dups,bad_selector = campaign.determiner_duplicates()
    form = DispatcherForm()

    email_list = print_list(campaign.emails, 'name')

    d = datetime.utcnow() - timedelta(hours=7) # localize utc
    d_value = d.strftime(DT_FORMAT)
    d_min = d_value
    d_max = (d + timedelta(days=7)).strftime(DT_FORMAT)

    return render_template('campaign/dispatcher.html',
        form=form,
        campaign=campaign,
        valid_keys=valid_keys,
        bad_key=bad_key,
        selector_dups=selector_dups,
        bad_selector=bad_selector,
        email_list=email_list,
        d_min=d_min,
        d_max=d_max,
        d_value=d_value
    )


@campaign.route('/<int:campaign_id>/dispatcher/confirm', methods=['POST'])
@login_required
def confirm_dispatch(campaign_id):
    campaign = Campaign.find_by_id(campaign_id) if campaign_id else None
    if not campaign:
        return abort(404)

    form = DispatcherForm(request.form)
    display_time = form.send_at.data.strftime('%m-%d-%Y %I:%M %p')
    form.send_at.data = form.send_at.data + timedelta(hours=7) # localize utc

    if not form.validate_on_submit():
        flash_errors(form)
        return redirect(url_for('campaign.dispatcher', campaign_id=campaign.id))

    current_form=DispatcherConfirmForm()
    if form.data.get('submit_now'):
        current_form.send_at.data = display_time = None
    else:
        current_form.send_at.data = form.send_at.data
    return render_template('campaign/confirm_dispatch.html',
        campaign=campaign,
        form=current_form,
        display_time=display_time
    )


@campaign.route('/<int:campaign_id>/dispatcher/submit', methods=['POST'])
@login_required
def submit_dispatch(campaign_id):
    campaign = Campaign.find_by_id(campaign_id) if campaign_id else None
    if not campaign:
        return abort(404)

    form = DispatcherConfirmForm(request.form)
    form.send_at.data = datetime.strptime(form.send_at.data, '%Y-%m-%d %H:%M:%S') if form.send_at.data else None
    if form.validate_on_submit():
        params = {
            'campaign_id': campaign.id,
            'account_id': current_user.account_id,
            'user_id': current_user.id,
            'list_id': campaign.list_id,
            'import_data': campaign.list_.import_data
        }
        if form.submit_send_at.data:
            params['send_at'] = form.send_at.data
            params['state'] = 15
            scheduled = 1
        else:
            params['send_at'] = None
            scheduled = 0

        d = Dispatcher.create(**params)
        if d and d.id:
            if not d.send_at:
                d.send() # fire emails => celery

            return redirect(url_for('campaign.success', campaign_id=campaign_id, scheduled=scheduled))
        else:
            flash('There was an error beginning the send, none have been sent.', 'warning')
    else:
        flash_errors(form)
    return redirect(url_for('campaign.edit', campaign_id=campaign_id))


@campaign.route('/<int:campaign_id>/dispatcher/success', methods=['GET'])
@login_required
def success(campaign_id=None):
    return render_template('campaign/dispatch_success.html', scheduled=request.args.get('scheduled'))


###########


@campaign.route('/list_select', methods=['GET'])
@login_required
def list_select():
    list_id = request.args.get('list_id')
    keys = []
    if list_id.isdigit():
        list_ = List.find_by_id(int(list_id))
        if list_:
            keys = list_.get_import_data_keys()
    return json.dumps(keys)


def setup_campaign_select_choices(form, list_id):
    l = List.find_by_id(list_id)
    if l:
        keys = l.get_import_data_keys()
    else:
        keys = []
    key_list = [('','')] + [(str(key), str(key)) for key in keys]

    form.from_email_dd.choices = key_list
    form.reply_to_dd.choices = key_list
    form.from_name_dd.choices = key_list
    form.to_email_dd.choices = key_list
    form.to_name_dd.choices = key_list
    form.selector_col_name.choices = key_list

    return form

