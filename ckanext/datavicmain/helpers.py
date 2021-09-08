import os
import pkgutil
import inspect

from flask import Blueprint, request

import ckan.model as model
import ckan.authz as authz
from ckan.common import config
from ckan.lib.navl.dictization_functions import unflatten
from ckan.logic import clean_dict, tuplize_dict, parse_params
from urllib.parse import urlsplit

import ckan.plugins.toolkit as toolkit
import logging
import ckan.lib.helpers as h
import datetime
import ckan.lib.mailer as mailer

from ckan.lib.base import render_jinja2
from ckanext.datavicmain import schema as custom_schema
from ckanext.harvest.model import HarvestObject


# Conditionally import the the workflow extension helpers if workflow extension enabled in .ini
if "workflow" in config.get('ckan.plugins', False):
    from ckanext.workflow import helpers as workflow_helpers
    workflow_enabled = True


log = logging.getLogger(__name__)


WORKFLOW_STATUS_OPTIONS = ['draft', 'ready_for_approval', 'published', 'archived']


def add_package_to_group(pkg_dict, context):
    group_id = pkg_dict.get('category', None)
    if group_id:
        group = model.Group.get(group_id)
        groups = context.get('package').get_groups('group')
        if group not in groups:
            group.add_package_by_name(pkg_dict.get('name'))


def set_data_owner(owner_org):
    data_owner = ''
    if owner_org:
        organization = model.Group.get(owner_org)
        if organization:
            parents = organization.get_parent_group_hierarchy('organization')
            if parents:
                data_owner = parents[0].title
            else:
                data_owner = organization.title
    return data_owner.strip()


def is_dataset_harvested(package_id):
    if not package_id:
        return None

    harvested = model.Session.query(model.Session.query(HarvestObject).filter_by(package_id=package_id).filter_by(state='COMPLETE').exists()).scalar()

    return harvested


def is_user_account_pending_review(user_id):
    # get_action('user_show') does not return the 'reset_key' so the only way to get this field is from the User model
    user = model.User.get(user_id)
    return user and user.is_pending() and user.reset_key is None


def send_email(user_emails, email_type, extra_vars):
    if not user_emails or len(user_emails) == 0:
        return

    subject = toolkit.render('emails/subjects/{0}.txt'.format(email_type), extra_vars)
    body = toolkit.render('emails/bodies/{0}.txt'.format(email_type), extra_vars)
    for user_email in user_emails:
        try:
            log.debug('Attempting to send {0} to: {1}'.format(email_type, user_email))
            # Attempt to send mail.
            mail_dict = {
                'recipient_name': user_email,
                'recipient_email': user_email,
                'subject': subject,
                'body': body
            }
            mailer.mail_recipient(**mail_dict)
        except (mailer.MailerException) as ex:
            log.error(u'Failed to send email {email_type} to {user_email}.'.format(email_type=email_type, user_email=user_email))
            log.error('Error: {ex}'.format(ex=ex))


def set_private_activity(pkg_dict, context, activity_type):
    pkg = model.Package.get(pkg_dict['id'])
    user = context['user']
    session = context['session']
    user_obj = model.User.by_name(user)

    if user_obj:
        user_id = user_obj.id
    else:
        user_id = str('not logged in')

    activity = pkg.activity_stream_item(activity_type, user_id)
    session.add(activity)
    return pkg_dict


def user_is_registering():
    #    return toolkit.c.controller in ['user'] and toolkit.c.action in ['register']
    (controller, action) = toolkit.get_endpoint()
    return controller in ['datavicuser'] and action in ['register']


def _register_blueprints():
    u'''Return all blueprints defined in the `views` folder
    '''
    blueprints = []

    def is_blueprint(mm):
        return isinstance(mm, Blueprint)

    path = os.path.join(os.path.dirname(__file__), 'views')

    for loader, name, _ in pkgutil.iter_modules([path]):
        module = loader.find_module(name).load_module(name)
        for blueprint in inspect.getmembers(module, is_blueprint):
            blueprints.append(blueprint[1])
            log.info(u'Registered blueprint: {0!r}'.format(blueprint[0]))
    return blueprints


def option_value_to_label(field, value):
    for extra in custom_schema.DATASET_EXTRA_FIELDS:
        if extra[0] == field:
            for option in extra[1]['options']:
                if option['value'] == value:
                    return option['text']


def group_list():
    return toolkit.get_action('group_list')({}, {'all_fields': True})


def workflow_status_options(current_workflow_status, owner_org):
    options = []
    if "workflow" in config.get('ckan.plugins', False):
        user = toolkit.g.user

        #log1.debug("\n\n\n*** workflow_status_options | current_workflow_status: %s | owner_org: %s | user: %s ***\n\n\n", current_workflow_status, owner_org, user)
        for option in workflow_helpers.get_available_workflow_statuses(current_workflow_status, owner_org, user):
            options.append({'value': option, 'text': option.replace('_', ' ').capitalize()})

        return options
    else:
        return [{'value': 'draft', 'text': 'Draft'}]


def autoselect_workflow_status_option(current_workflow_status):
    selected_option = 'draft'
    user = toolkit.g.user
    if authz.is_sysadmin(user):
        selected_option = current_workflow_status
    return selected_option


def workflow_status_pretty(workflow_status):
    return workflow_status.replace('_', ' ').capitalize()


def get_organisations_allowed_to_upload_resources():
    orgs = toolkit.config.get('ckan.organisations_allowed_to_upload_resources', ['victorian-state-budget'])
    return orgs


def get_user_organizations(username):
    user = model.User.get(username)
    return user.get_groups('organization')


def user_org_can_upload(pkg_id):
    user = toolkit.g.user
    context = {'user': user}
    org_name = None
    if pkg_id is None:
        request_path = urlsplit(request.url)
        if request_path.path is not None:
            fragments = request_path.path.split('/')
            if fragments[1] == 'dataset':
                pkg_id = fragments[2]

    if pkg_id is not None:
        dataset = toolkit.get_action('package_show')(context, {'name_or_id': pkg_id})
        org_name = dataset.get('organization').get('name')
    allowed_organisations = get_organisations_allowed_to_upload_resources()
    user_orgs = get_user_organizations(user)
    for org in user_orgs:
        if org.name in allowed_organisations and org.name == org_name:
            return True
    return False

def get_frequency_options():
    return [
        {'value':'ten_minutes', 'text':'10 minutes'},
        { 'value':'two_hours',  'text': '2 hours'},
        { 'value':'daily', 'text':'Daily'}]
        
def clean_params(params):
    return clean_dict(unflatten(tuplize_dict(parse_params(params))))


def get_datastore_refresh_configs():
    user = toolkit.g.user
    context = {'user': user}
    return toolkit.get_action('refresh_dataset_datastore_list')(context, {})

def get_datasore_refresh_config_option(frequency):
    options = get_frequency_options()
    return [option['text'] for option in options if option['value'] == frequency]