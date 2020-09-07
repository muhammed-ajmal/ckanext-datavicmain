import ckan
import ckan.logic as logic
import ckan.lib.dictization.model_dictize as model_dictize
import ckan.lib.dictization.model_save as model_save
import ckan.plugins.toolkit as toolkit
import ckanext.datavic_iar_theme.helpers as theme_helpers
import logging

from ckan import lib
from ckan.common import c, request
from ckanext.datavicmain import helpers

_validate = ckan.lib.navl.dictization_functions.validate
_check_access = logic.check_access
config = toolkit.config
h = toolkit.h
log1 = logging.getLogger(__name__)
user_is_registering = helpers.user_is_registering
ValidationError = logic.ValidationError


def email_in_use(user_email, context):
    model = context['model']
    session = context['session']
    return session.query(model.User).filter_by(email=user_email).first()


def user_email_unique(user_email, context):
    result = email_in_use(user_email, context)
    if result:
        raise lib.navl.dictization_functions.Invalid('Email address ' + user_email + ' already in use for user: ' + result.name)

    return user_email


def datavic_user_create(context, data_dict):
    model = context['model']
    schema = context.get('schema') or logic.schema.default_user_schema()
    # DATAVICIAR-42: Add unique email validation
    schema['email'].append(user_email_unique)
    session = context['session']

    _check_access('user_create', context, data_dict)

    if user_is_registering():
        # DATAVIC-221: If the user registers set the state to PENDING where a sysadmin can activate them
        data_dict['state'] = ckan.model.State.PENDING

    data, errors = _validate(data_dict, schema, context)

    create_org_member = False

    if user_is_registering():
        # DATAVIC-221: Validate the organisation_id
        organisation_id = data_dict.get('organisation_id', None)

        # DATAVIC-221: Ensure the user selected an orgnisation
        if not organisation_id:
            errors['organisation_id'] = [u'Please select an Organisation']
        # DATAVIC-221: Ensure the user selected a valid top-level organisation
        elif organisation_id not in theme_helpers.get_parent_orgs('list'):
            errors['organisation_id'] = [u'Invalid Organisation selected']
        else:
            create_org_member = True

    if errors:
        session.rollback()
        raise ValidationError(errors)

    # user schema prevents non-sysadmins from providing password_hash
    if 'password_hash' in data:
        data['_password'] = data.pop('password_hash')

    user = model_save.user_dict_save(data, context)

    # Flush the session to cause user.id to be initialised, because
    # activity_create() (below) needs it.
    session.flush()

    activity_create_context = {
        'model': model,
        'user': context['user'],
        'defer_commit': True,
        'ignore_auth': True,
        'session': session
    }
    activity_dict = {
        'user_id': user.id,
        'object_id': user.id,
        'activity_type': 'new user',
    }
    logic.get_action('activity_create')(activity_create_context, activity_dict)

    if user_is_registering() and create_org_member:
        # DATAVIC-221: Add the new (pending) user as a member of the organisation
        logic.get_action('member_create')(activity_create_context, {
            'id': organisation_id,
            'object': user.id,
            'object_type': 'user',
            'capacity': 'member'
        })

    if not context.get('defer_commit'):
        model.repo.commit()

    # A new context is required for dictizing the newly constructed user in
    # order that all the new user's data is returned, in particular, the
    # api_key.
    #
    # The context is copied so as not to clobber the caller's context dict.
    user_dictize_context = context.copy()
    user_dictize_context['keep_apikey'] = True
    user_dictize_context['keep_email'] = True
    user_dict = model_dictize.user_dictize(user, user_dictize_context)

    context['user_obj'] = user
    context['id'] = user.id

    model.Dashboard.get(user.id)  # Create dashboard for user.

    if user_is_registering():
        # DATAVIC-221: Send new account requested emails
        user_emails = [x.strip() for x in config.get('ckan.datavic.request_access_review_emails', []).split(',')]
        helpers.send_email(
            user_emails,
            'new_account_requested',
            {
                "user_name": user.name,
                "user_url": toolkit.url_for(controller='user', action='read', id=user.name, qualified=True),
                "site_title": config.get('ckan.site_title'),
                "site_url": config.get('ckan.site_url')
            }
        )

        h.flash_success(toolkit._('Your requested account has been submitted for review'))

        h.redirect_to(controller='home', action='index')

    log1.debug('Created user {name}'.format(name=user.name))
    return user_dict
