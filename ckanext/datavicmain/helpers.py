import os
import pkgutil
import inspect

from flask import Blueprint

import ckan.model as model
import ckan.plugins.toolkit as toolkit
import logging
import ckan.lib.helpers as h
import datetime
import ckan.lib.mailer as mailer

from ckan.lib.base import render_jinja2
from ckanext.datavicmain import schema as custom_schema

log = logging.getLogger(__name__)


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


#TODO: Find a way to determine if the daset is harvested
#TODO: We will use `package_activity_list` for now 

def is_dataset_harvested(package_id):
    if not package_id:
        return None
    return any(package_revision for package_revision in toolkit.get_action('package_activity_list')(data_dict={'id': package_id})
               if 'REST API: Create object' in package_revision.get('activity_type') and h.date_str_to_datetime(package_revision.get('timestamp')) > datetime.datetime(2019, 4, 24, 10, 30))


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
     return controller in ['user'] and action in ['register']

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
