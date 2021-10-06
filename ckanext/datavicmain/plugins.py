# Plugins for ckanext-datavicmain

import json
import time
import calendar
import copy
import logging
import ckan.authz as authz

import ckan.model           as model
import ckan.plugins         as p
import ckan.plugins.toolkit as toolkit
import ckan.logic           as logic

from ckanext.datavicmain import actions
from ckanext.datavicmain import schema as custom_schema
from ckanext.datavicmain import helpers
from ckanext.datavicmain import validators

from ckan.common import config, request

_t = toolkit._

log1 = logging.getLogger(__name__)

from ckan import lib
from ckan.lib import base
from ckan.logic.auth.update import package_update as ckan_package_update
from six import text_type


workflow_enabled = False

# Conditionally import the the workflow extension helpers if workflow extension enabled in .ini
if "workflow" in config.get('ckan.plugins', False):
    from ckanext.workflow import helpers as workflow_helpers
    workflow_enabled = True


def parse_date(date_str):
    try:
        return calendar.timegm(time.strptime(date_str, "%Y-%m-%d"))
    except Exception as e:
        return None


def release_date(pkg_dict):
    """
    Copied from https://github.com/salsadigitalauorg/datavic_ckan_2.2/blob/develop/iar/src/ckanext-datavic/ckanext/datavic/plugin.py#L296
    :param pkg_dict:
    :return:
    """
    dates = []
    dates.append(pkg_dict['metadata_created'])
    for resource in pkg_dict['resources']:
        if 'release_date' in resource and resource['release_date'] != '' and resource['release_date'] != '1970-01-01':
            dates.append(resource['release_date'])
    dates.sort()
    return dates[0].split("T")[0]


def validator_email_not_in_use(user_email, context):
    user = context['user_obj']

    # If there is no change to email, no need to check it further..
    if not user.email == user_email:
        result = actions.email_in_use(user_email, context)
        if result:
            raise lib.navl.dictization_functions.Invalid(user_email + ' is already in use.')

    return user_email


#   Need this decorator to force auth function to be checked for sysadmins aswell
#   (ref.: ckan/default/src/ckan/ckan/logic/__init__.py)
@toolkit.auth_sysadmins_check
@toolkit.auth_allow_anonymous_access
def datavic_user_update(context, data_dict=None):
    if toolkit.g and toolkit.g.controller == 'user' and toolkit.g.action == 'perform_reset':
        # Allow anonymous access to the user/reset path, i.e. password resets.
        return {'success': True}
    elif 'save' in context and context['save']:
        if 'email' in request.params:
            schema = context.get('schema')
            if not validator_email_not_in_use in schema['email']:
                schema['email'].append(validator_email_not_in_use)

    return {'success': True}


def datavic_package_update(context, data_dict):
    if toolkit.g and toolkit.g.controller in ['dataset', 'package'] and toolkit.g.action in ['read', 'edit', 'resource_read', 'resource_edit']:
        # Harvested dataset are not allowed to be updated, apart from sysadmins
        package_id = data_dict.get('id') if data_dict else toolkit.g.pkg_dict.get('id') if 'pkg_dict' in toolkit.g else None
        if package_id and helpers.is_dataset_harvested(package_id):
            return {'success': False,
                    'msg': _t('User %s not authorized to edit this harvested package') %
                    (str(context.get('user')))}

    return ckan_package_update(context, data_dict)


@toolkit.auth_allow_anonymous_access
def datavic_user_reset(context, data_dict):
    if helpers.is_user_account_pending_review(context.get('user', None)):
        return {'success': False,
                'msg': _t('User %s not authorized to reset password') %
                (str(context.get('user')))}
    else:
        return {'success': True}


def is_iar():
    return toolkit.asbool(config.get('ckan.iar', False))


#   The code in this class was copied (& adjusted) from the CKAN 2.2 repository
class AuthMiddleware(object):
    def __init__(self, app, app_conf):
        self.app = app
    def __call__(self, environ, start_response):
        # DATAVIC-160 Changes site URL from directory.iar.vic.gov.au to directory.data.vic.gov.au
        if environ['HTTP_HOST'] and environ['HTTP_HOST'] == 'directory.iar.vic.gov.au':
            headers = [('Location', 'https://directory.data.vic.gov.au' + environ['PATH_INFO'])]
            status = "301 Moved Permanently"
            start_response(status, headers)
            return ['']

        # if logged in via browser cookies or API key, all pages accessible
        if 'repoze.who.identity' in environ or self._get_user_for_apikey(environ) or not is_iar():
            return self.app(environ,start_response)
        else:
            # otherwise only login/reset and front pages are accessible
            if (environ['PATH_INFO'] == '/'
            or environ['PATH_INFO'] == '/user/login'
            or environ['PATH_INFO'] == '/user/_logout'
            or '/user/reset' in environ['PATH_INFO']
            or environ['PATH_INFO'] == '/user/logged_out'
            or environ['PATH_INFO'] == '/user/logged_in'
            or environ['PATH_INFO'] == '/user/logged_out_redirect'
            or environ['PATH_INFO'] == '/user/register'
            or environ['PATH_INFO'].startswith('/api')
            or environ['PATH_INFO'].startswith('/base')
            or environ['PATH_INFO'].startswith('/webassets')
            or environ['PATH_INFO'].startswith('/images')
            or environ['PATH_INFO'].startswith('/css')
            or environ['PATH_INFO'].startswith('/js')
            or environ['PATH_INFO'].startswith('/_debug')
            or environ['PATH_INFO'].startswith('/uploads')
            or environ['PATH_INFO'].startswith('/fonts')
            or environ['PATH_INFO'].startswith('/assets')
            or environ['PATH_INFO'].endswith('svg')):
                return self.app(environ, start_response)
            else:
                log1.debug(f"Unauthorized page accessed: {environ['PATH_INFO']}")
                # Status code needs to be 3xx (redirection) for Location header to be used
                status = "302 Unauthorized"
                location = '/user/login'
                headers = [('Location', location),
                           ('Content-Length', '0')]
                log1.debug(f"Redirecting to: {location}")
                start_response(status, headers)
                # Return now as we want to end the request
                return []


    def _get_user_for_apikey(self, environ):
        # Adapted from https://github.com/ckan/ckan/blob/625b51cdb0f1697add59c7e3faf723a48c8e04fd/ckan/lib/base.py#L396
        apikey_header_name = config.get(base.APIKEY_HEADER_NAME_KEY,
                                        base.APIKEY_HEADER_NAME_DEFAULT)
        apikey = environ.get(apikey_header_name, '')
        if not apikey:
            # For misunderstanding old documentation (now fixed).
            apikey = environ.get('HTTP_AUTHORIZATION', '')
        if not apikey:
            apikey = environ.get('Authorization', '')
            # Forget HTTP Auth credentials (they have spaces).
            if ' ' in apikey:
                apikey = ''
        if not apikey:
            return None
        apikey = str(apikey)
        # check if API key is valid by comparing against keys of registered users
        query = model.Session.query(model.User)
        user = query.filter_by(apikey=apikey).first()
        return user

class DatasetForm(p.SingletonPlugin, toolkit.DefaultDatasetForm):
    ''' A plugin that provides some metadata fields and
    overrides the default dataset form
    '''
    p.implements(p.ITemplateHelpers)
    p.implements(p.IConfigurable, inherit=True)
    p.implements(p.IConfigurer, inherit=True)
    # p.implements(p.IDatasetForm, inherit=True)
    p.implements(p.IPackageController, inherit=True)
    # p.implements(p.IResourceController, inherit=True)
    p.implements(p.IRoutes, inherit=True)
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)
    p.implements(p.IMiddleware, inherit=True)
    p.implements(p.IBlueprint)
    p.implements(p.IValidators)


    def make_middleware(self, app, config):
        return AuthMiddleware(app, config)

    # IBlueprint
    def get_blueprint(self):
        return helpers._register_blueprints()

    # IValidators
    def get_validators(self):
        return {
            'datavic_tag_string': validators.datavic_tag_string
        }

    # IAuthFunctions
    def get_auth_functions(self):
        return {
            'user_update': datavic_user_update,
            'package_update': datavic_package_update,
            'user_reset': datavic_user_reset,
        }

    # IActions
    def get_actions(self):
        return {
            # DATAVICIAR-42: Override CKAN's core `user_create` method
            'user_create': actions.datavic_user_create,
            'refresh_datastore_dataset_create': actions.refresh_dataset_datastore_create,
            'refresh_dataset_datastore_list': actions.refresh_dataset_datastore_list,
            'refresh_dataset_datastore_delete': actions.refresh_dataset_datastore_delete
        }


    ## helper methods ## 


    @classmethod
    def organization_list_objects(cls, org_names = []):
        ''' Make a action-api call to fetch the a list of full dict objects (for each organization) '''
        context = {
            'model': model,
            'session': model.Session,
            'user': toolkit.g.user,
        }

        options = { 'all_fields': True }
        if org_names and len(org_names):
            t = type(org_names[0])
            if   t is str:
                options['organizations'] = org_names
            elif t is dict:
                options['organizations'] = map(lambda org: org.get('name'), org_names)

        return logic.get_action('organization_list') (context, options)

    @classmethod
    def organization_dict_objects(cls, org_names = []):
        ''' Similar to organization_list_objects but returns a dict keyed to the organization name. '''
        results = {}
        for org in cls.organization_list_objects(org_names):
            results[org['name']] = org
        return results

    @classmethod
    def is_admin(cls, owner_org):
        if workflow_enabled:
            user = toolkit.g.userobj
            if authz.is_sysadmin(user.name):
                return True
            else:
                role = workflow_helpers.role_in_org(owner_org, user.name)
                if role == 'admin':
                    return True

    def is_sysadmin(self):
        user = toolkit.g.user
        if authz.is_sysadmin(user):
            return True


    def historical_resources_list(self, resource_list):
        sorted_resource_list = {}
        i = 0
        for resource in resource_list:
            i += 1
            if resource.get('period_start') is not None and resource.get('period_start') != 'None' and resource.get(
                    'period_start') != '':
                key = parse_date(resource.get('period_start')[:10]) or '9999999999' + str(i)
            else:
                key = '9999999999' + str(i)
            resource['key'] = key
            # print parser.parse(resource.get('period_start')).strftime("%Y-%M-%d") + " " + resource.get('period_start')
            sorted_resource_list[key] = resource

        list = sorted(sorted_resource_list.values(), key=lambda item: int(item.get('key')), reverse=True)
        # for item in list:
        #    print item.get('period_start') + " " + str(item.get('key'))
        return list

    def historical_resources_range(resource_list):
        range_from = ""
        from_ts = None
        range_to = ""
        to_ts = None
        for resource in resource_list:

            if resource.get('period_start') is not None and resource.get('period_start') != 'None' and resource.get(
                    'period_start') != '':
                ts = parse_date(resource.get('period_start')[:10])
                if ts and (from_ts is None or ts < from_ts):
                    from_ts = ts
                    range_from = resource.get('period_start')[:10]
            if resource.get('period_end') is not None and resource.get('period_end') != 'None' and resource.get(
                    'period_end') != '':
                ts = parse_date(resource.get('period_end')[:10])
                if ts and (to_ts is None or ts > to_ts):
                    to_ts = ts
                    range_to = resource.get('period_end')[:10]

        if range_from != "" and range_to != "":
            return range_from + " to " + range_to
        elif range_from != "" or range_to != "":
            return range_from + range_to
        else:
            return None

    def is_historical(self):
        if toolkit.g.action == 'historical':
            return True

    def get_formats(self, limit=100):
        try:
            # Get any additional formats added in the admin settings
            additional_formats = [x.strip() for x in config.get('ckan.datavic.authorised_resource_formats', []).split(',')]
            q = request.GET.get('q', '')
            list_of_formats = [x.encode('utf-8') for x in
                               logic.get_action('format_autocomplete')({}, {'q': q, 'limit': limit}) if x] + additional_formats
            list_of_formats = sorted(list(set(list_of_formats)))
            dict_of_formats = []
            for item in list_of_formats:
                if item == ' ' or item == '':
                    continue
                else:
                    dict_of_formats.append({'value': item.lower(), 'text': item.upper()})
            dict_of_formats.insert(0, {'value': '', 'text': 'Please select'})

        except Exception as e:
            return []
        else:
            return dict_of_formats

    def repopulate_user_role(self):
        if 'submit' in request.params:
            return request.params['role']
        else:
            return 'member'



    ## ITemplateHelpers interface ##

    def get_helpers(self):
        ''' Return a dict of named helper functions (as defined in the ITemplateHelpers interface).
        These helpers will be available under the 'h' thread-local global object.
        '''
        return {
            'organization_list_objects': self.organization_list_objects,
            'organization_dict_objects': self.organization_dict_objects,
            'dataset_extra_fields': custom_schema.DATASET_EXTRA_FIELDS,
            'resource_extra_fields': custom_schema.RESOURCE_EXTRA_FIELDS,
            'workflow_status_options': helpers.workflow_status_options,
            'is_admin': self.is_admin,
            'workflow_status_pretty': helpers.workflow_status_pretty,
            'historical_resources_list': self.historical_resources_list,
            'historical_resources_range': self.historical_resources_range,
            'is_historical': self.is_historical,
            'get_formats': self.get_formats,
            'is_sysadmin': self.is_sysadmin,
            'repopulate_user_role': self.repopulate_user_role,
            'group_list': helpers.group_list,
            'get_option_label': custom_schema.get_option_label,
            'autoselect_workflow_status_option': helpers.autoselect_workflow_status_option,
            'release_date': release_date,
            'is_dataset_harvested': helpers.is_dataset_harvested,
            'is_user_account_pending_review': helpers.is_user_account_pending_review,
            'option_value_to_label': helpers.option_value_to_label,
            'user_org_can_upload': helpers.user_org_can_upload,
        }

    ## IConfigurer interface ##
    def update_config_schema(self, schema):
        schema.update({
            'ckan.datavic.authorised_resource_formats': [
                toolkit.get_validator('ignore_missing'),
                text_type
            ],
            'ckan.datavic.request_access_review_emails': [
                toolkit.get_validator('ignore_missing'),
                text_type
            ]
        })

        return schema

    def update_config(self, config):
        ''' Setup the (fanstatic) resource library, public and template directory '''
        p.toolkit.add_public_directory(config, 'public')
        p.toolkit.add_template_directory(config, 'templates')
        p.toolkit.add_resource('public', 'ckanext-datavicmain')
        p.toolkit.add_resource('webassets', 'ckanext-datavicmain')

    ## IConfigurable interface ##

    def configure(self, config):
        ''' Apply configuration options to this plugin '''
        pass

    ## IDatasetForm interface ##

    def is_fallback(self):
        '''
        Return True to register this plugin as the default handler for
        package types not handled by any other IDatasetForm plugin.
        '''
        return True

    def package_types(self):
        '''
        This plugin doesn't handle any special package types, it just
        registers itself as the default (above).
        '''
        return []

    def _modify_package_schema(self, schema):
        ''' Override CKAN's create/update schema '''

        # Define some closures as custom callbacks for the validation process

        from ckan.lib.navl.dictization_functions import missing, StopOnError, Invalid

        for field in custom_schema.DATASET_EXTRA_FIELDS:
            schema.update({
                field[0]: [toolkit.get_validator('ignore_missing'),
                            toolkit.get_converter('convert_to_extras')]
            })

        # DATAVIC-245: this code removed
        # DataVic: Helper function for adding extra dataset fields
        # def append_field(extras_list, data, key):
        #     items = list(filter(lambda t: t['key'] == key, extras_list))
        #     if items:
        #         items[0]['value'] = data.get((key,))
        #     else:
        #         extras_list.append({ 'key': key, 'value': data.get((key,)) })
        #     return

        def after_validation_processor(key, data, errors, context):
            assert key[0] == '__after', 'This validator can only be invoked in the __after stage'
            #raise Exception ('Breakpoint after_validation_processor')
            # Demo of howto create/update an automatic extra field 
            extras_list = data.get(('extras',))
            if not extras_list:
                extras_list = data[('extras',)] = []

            # DataVic: Append extra fields as dynamic (not registered under modify schema) field
            # DATAVIC-245: this code removed
            # for field in custom_schema.DATASET_EXTRA_FIELDS:
                #append_field(extras_list, data, field[0])

            # DATAVIC-56
            if workflow_enabled:
                # Get the current workflow_status value for comparison..
                pkg = model.Package.get(data.get(('id',)))

                if pkg and 'workflow_status' in pkg.extras:
                    user = toolkit.g.userobj

                    adjusted_workflow_status = workflow_helpers.get_workflow_status_for_role(
                        pkg.extras['workflow_status'],
                        data.get(('workflow_status',), None),
                        user.name,
                        data.get(('owner_org',), None)
                    )

                    items = filter(lambda t: t['key'] == 'workflow_status', extras_list)
                    if items:
                        items[0]['value'] = adjusted_workflow_status
                    else:
                        extras_list.append({'key': 'workflow_status', 'value': adjusted_workflow_status})

            #Validate our custom schema fields based on the rules set in schema.py

        
    # IPackageController  

    def after_create(self, context, pkg_dict):
        # Only add packages to groups when being created via the CKAN UI (i.e. not during harvesting)
        if toolkit.g and toolkit.g.controller in ['dataset', 'package']:
            # Add the package to the group ("category")
            pkg_group = pkg_dict.get('category', None)
            pkg_name = pkg_dict.get('name', None)
            pkg_type = pkg_dict.get('type', None)
            if pkg_group and pkg_type in ['dataset', 'package']:
                group = model.Group.get(pkg_group)
                group.add_package_by_name(pkg_name)
                 # DATAVIC-251 - Create activity for private datasets
                helpers.set_private_activity(pkg_dict, context, str('new'))
        pass

    def after_update(self, context, pkg_dict):
        # Only add packages to groups when being updated via the CKAN UI (i.e. not during harvesting)
        if toolkit.g and toolkit.g.controller in ['dataset', 'package']:
            if 'type' in pkg_dict and pkg_dict['type'] in ['dataset', 'package']:
                helpers.add_package_to_group(pkg_dict, context)
                # DATAVIC-251 - Create activity for private datasets
                helpers.set_private_activity(pkg_dict, context, str('changed'))
        pass

    def after_show(self, context, pkg_dict):
        '''Convert dataset_type-typed parts of pkg_dict to a nested dict or an object.

        This is for display (template enviroment and api results) purposes only, 
        and should *not* affect the way the read schema is being used.

        :param context: The context under which this hook is invoked
        :type context: dict
        :param pkg_dict: The package dict  
        :type pkg_dict: dict

        :returns: None
        :raises: None
        
        '''

        is_validated = context.get('validate', True)
        for_view = context.get('for_view', False)
        
        #log1.debug('after_show: Package %s is shown: view=%s validated=%s api=%s',
        #    pkg_dict.get('name'), for_view, is_validated, context.get('api_version'))
        
        if not is_validated:
            # Noop: the extras are not yet promoted to 1st-level fields
            return

        # Add more (computed) items to pkg_dict ... 

        return
        #return pkg_dict
     
    def before_search(self, search_params):
        #search_params['q'] = 'extras_qoo:*';
        #search_params['extras'] = { 'ext_qoo': 'far' }
        return search_params
   
    def after_search(self, search_results, search_params):
        #raise Exception('Breakpoint')
        return search_results

    def before_index(self, pkg_dict):
        return pkg_dict

    def before_view(self, pkg_dict):
        log1.debug('before_view: Package %s is prepared for view', pkg_dict.get('name'))

        # This hook can add/hide/transform package fields before sent to the template.
        
        # add some extras to the 2-column table
        
        dt = pkg_dict.get('dataset_type')

        extras = pkg_dict.get('extras', [])
        if not extras:
            pkg_dict['extras'] = extras

        # extras.append({ 'key': 'Music Title', 'value': pkg_dict.get('music_title', 'n/a') })
        # extras.append({ 'key': 'Music Genre', 'value': pkg_dict.get('music_genre', 'n/a') })

        # or we can translate keys ...
        
        field_key_map = {
            u'updated_at': _t(u'Updated'),
            u'created_at': _t(u'Created'),
        }
        for item in extras:
            k = item.get('key')
            item['key'] = field_key_map.get(k, k)
        
        return pkg_dict

class RefreshDatasetDatastore(p.SingletonPlugin):

    p.implements(p.ITemplateHelpers)
    p.implements(p.IConfigurable, inherit=True)
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IRoutes, inherit=True)
    p.implements(p.IActions)
    
    toolkit.add_ckan_admin_tab(toolkit.config, 'datastore_refresh_config', 'Datastore refresh',
                               config_var='ckan.admin_tabs')

    def get_helpers(self):
        return {}

    def get_actions(self):
        return {}
    
    ## IConfigurable interface ##

    def configure(self, config):
        ''' Apply configuration options to this plugin '''
        pass

    #IRoutes
    def before_map(self, m):
        m.connect(
            u'datastore_refresh_config',
            u'/ckan-admin/datastore_refresh_config',
            controller=u'ckanext.datavicmain.controller:DataVicAdminController',
            action=u'datastore_refresh_config')
        return m