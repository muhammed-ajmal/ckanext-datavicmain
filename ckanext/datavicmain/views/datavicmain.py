import logging
import json
from operator import itemgetter
import pdb

from flask import Blueprint
from flask.views import MethodView

import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.logic as logic
import ckan.model as model
from ckan.common import _, config, g, request
from ckan.lib.navl import dictization_functions
import ckan.plugins.toolkit as tk

import ckan.views.dataset as dataset


NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
#TemplateNotFound = logic.TemplateNotFound
check_access = logic.check_access
get_action = logic.get_action
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
parse_params = logic.parse_params
flatten_to_string_key = logic.flatten_to_string_key

render = base.render
abort = base.abort

log = logging.getLogger(__name__)

datavicmain = Blueprint('datavicmain', __name__)


def historical(id):
    #response.headers['Content-Type'] = "text/html; charset=utf-8"
    # package_type = _get_package_type(id.split('@')[0])
    import pdb;pdb.set_trace()
    package_type = dataset._get_package_type(id.split('@')[0]) #check for new function if necessary

    context = {'model': model, 'session': model.Session,
                'user': g.user or g.author, 'for_view': True,
                'auth_user_obj': g.userobj}
    data_dict = {'id': id}
    # check if package exists
    try:
        g.pkg_dict = get_action('package_show')(context, data_dict)
        g.pkg = context['package']
    except NotFound:
        abort(404, _('Dataset not found'))
    except NotAuthorized:
        abort(401, _('Unauthorized to read package %s') % id)

    # used by disqus plugin
    g.current_package_id = g.pkg.id
    # g.related_count = g.pkg.related_count
    # self._setup_template_variables(context, {'id': id},
    #                                 package_type=package_type)
    dataset._setup_template_variable(context, {'id': id},
                                      package_type=package_type)

    # package_saver.PackageSaver().render_package(c.pkg_dict, context)

    try:
        return render('package/read_historical.html')
    except base.TemplateNotFound:
        msg = _("Viewing {package_type} datasets in {format} format is "
                "not supported (template file {file} not found).".format(
                    package_type=package_type, format=format, file='package/read_historical.html'))
        abort(404, msg)

    assert False, "We should never get here"

def check_sysadmin(self):
    import ckan.authz as authz

    # Only sysadmin users can generate reports
    user = tk.g.userobj

    if not user or not authz.is_sysadmin(user.name):
        base.abort(403, _('You are not permitted to perform this action.'))

def create_core_groups(self):
    self.check_sysadmin()

    context = {'user': tk.g.user, 'model': model, 'session': model.Session, 'ignore_auth': True, 'return_id_only': True}

    output = '<pre>'

    groups_to_fetch = [
        'business',
        'communication',
        'community',
        'education',
        'employment',
        'environment',
        'general',
        'finance',
        'health',
        'planning',
        'recreation',
        'science-technology',
        'society',
        'spatial-data',
        'transport'
    ]

    from ckanapi import RemoteCKAN
    ua = 'ckanapiexample/1.0 (+http://example.com/my/website)'
    demo = RemoteCKAN('https://www.data.vic.gov.au/data', user_agent=ua)
    for group in groups_to_fetch:
        group_dict = demo.action.group_show(
            id=group,
            include_datasets=False,
            include_groups=False,
            include_dataset_count=False,
            include_users=False,
            include_tags=False,
            include_extras=False,
            include_followers=False
        )

        output += "\nRemote CKAN group:\n"
        output += json.dumps(group_dict)

        # Check for existence of a local group with the same name
        try:
            local_group_dict = tk.get_action('group_show')(context, {'id': group_dict['name']})
            output += "\nA local group called %s DOES exist" % group_dict['name']
        except NotFound:
            output += "\nA local group called %s does not exist" % group_dict['name']
            tk.check_access('group_create', context)
            local_group_dict = tk.get_action('group_create')(context, group_dict)
            output += "\nCreated group:\n"
            output += json.dumps(local_group_dict)

        output += "\n==============================\n"

    return output

def register_datavicmain_plugin_rules(blueprint):
    blueprint.add_url_rule('/dataset/{id}/historical', view_func=historical)
    blueprint.add_url_rule('/create_core_groups', view_func=create_core_groups)

register_datavicmain_plugin_rules(datavicmain)