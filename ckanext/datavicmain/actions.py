import ckan.plugins.toolkit as toolkit
import ckanext.datavic_iar_theme.helpers as theme_helpers
import logging

from ckan.model import State
from ckan.lib.dictization import model_dictize, model_save, table_dictize
from ckan.lib.navl.validators import not_empty
from ckan.logic import schema as ckan_schema
from ckanext.datavicmain import helpers

_check_access = toolkit.check_access
config = toolkit.config
log = logging.getLogger(__name__)
user_is_registering = helpers.user_is_registering
ValidationError = toolkit.ValidationError
get_action = toolkit.get_action
_validate = toolkit.navl_validate
_get_or_bust = toolkit.get_or_bust


def datavic_user_create(context, data_dict):
    model = context['model']
    schema = context.get('schema') or ckan_schema.default_user_schema()
    # DATAVICIAR-42: Add unique email validation
    # unique email validation is their by default now in CKAN 2.9 email_is_unique
    # But they have removed not_empty so lets insert it back in
    schema['email'].insert(0, not_empty)
    session = context['session']

    _check_access('user_create', context, data_dict)

    if user_is_registering():
        # DATAVIC-221: If the user registers set the state to PENDING where a sysadmin can activate them
        data_dict['state'] = State.PENDING

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
    get_action('activity_create')(activity_create_context, activity_dict)

    if user_is_registering() and create_org_member:
        # DATAVIC-221: Add the new (pending) user as a member of the organisation
        get_action('member_create')(activity_create_context, {
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

    log.debug('Created user {name}'.format(name=user.name))
    return user_dict

def datavic_nominate_resource_view(context, data_dict):
    package_id = _get_or_bust(data_dict, 'package_id')
    view_id = _get_or_bust(data_dict, 'view_id')
    resource_id = _get_or_bust(data_dict,'resource_id')
    pkg_dict = get_action('package_show')(context, {'id': package_id})

    pkg_dict['nominated_view_id'] = view_id
    pkg_dict['nominated_view_resource'] = resource_id
    get_action('package_update')(context, pkg_dict)

    return pkg_dict

