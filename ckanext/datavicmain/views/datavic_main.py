import logging
from operator import itemgetter

from flask import Blueprint
from flask.views import MethodView

import ckan.lib.helpers as h
import ckan.model as model
from ckan.common import _,  g
import ckan.plugins.toolkit as toolkit

import ckan.views.dataset as dataset
import ckanext.datavicmain.helpers as helpers


NotFound = toolkit.ObjectNotFound
NotAuthorized = toolkit.NotAuthorized
ValidationError = toolkit.ValidationError
check_access = toolkit.check_access
get_action = toolkit.get_action


render = toolkit.render
abort = toolkit.abort

log = logging.getLogger(__name__)

datavicmain = Blueprint('datavicmain', __name__)


def historical(id):
    package_type = dataset._get_package_type(id.split('@')[0]) #check for new function if necessary

    context = {'model': model, 'session': model.Session,
                'user': g.user or g.author, 'for_view': True,
                'auth_user_obj': g.userobj}
    
    data_dict = {'id': id}
    # check if package exists
    try:
        pkg_dict = get_action('package_show')(context, data_dict)
        pkg = context['package']
    except NotFound:
        abort(404, _('Dataset not found'))
    except NotAuthorized:
        abort(401, _('Unauthorized to read package %s') % id)

    # used by disqus plugin
    g.current_package_id = pkg.id
    dataset._setup_template_variables(context, data_dict,
                                      package_type=package_type)

    extra_vars = {'pkg_dict': pkg_dict, 'pkg': pkg}

    try:
        return render('package/read_historical.html', extra_vars)
    # TemplateNotFound is not added to toolkit
    except NotFound as e:
        msg = _("Viewing {package_type} datasets in {format} format is "
                "not supported (template file {file} not found).".format(
                    package_type=package_type, format=format, file='package/read_historical.html'))
        abort(404, msg)

    assert False, "We should never get here"

def purge(id):
    try:
        # Only sysadmins can purge
        toolkit.check_access('sysadmin', {})
        toolkit.get_action('dataset_purge')({}, {'id': id})
        toolkit.h.flash_success('Successfully purged dataset ID: %s' % id)
    except Exception as e:
        print(str(e))
        toolkit.h.flash_error('Exception')

    return toolkit.h.redirect_to('/ckan-admin/trash')


class DatastoreRefreshConfigView(MethodView):

    def _setup_extra_template_variables(self):
        user = toolkit.g.userobj
        context = {u'for_view': True, u'user': user.name, u'auth_user_obj': user}
        #data_dict = {u'user_obj': user, u'include_datasets': True}
        return context

    def _get_context(self):
        return {
            'model': model,
            'session': model.Session,
            'user': toolkit.g.user,
            'auth_user_obj': toolkit.g.userobj
    }

    
    def get(self, context=None, errors=None, error_summary=None):
        context = self._get_context()
        
        extra_vars = self._setup_extra_template_variables()
        extra_vars['errors'] = errors
        extra_vars['error_summary'] = error_summary
        
        return toolkit.render('admin/datastore_refresh.html', extra_vars=extra_vars)
    
    def post(self):
        context = self._get_context()
        params = helpers.clean_params(toolkit.request.form)
        if params.get('delete_config'):
            toolkit.get_action('refresh_dataset_datastore_delete')(context, {'id': params.get('delete_config')})
            h.flash_success(toolkit._("Succesfully deleted configuration"))
            return self.get()

        if not params.get('dataset'):
            h.flash_error(toolkit._('Please select dataset'))
            return self.get()

        config_dict = {
            "dataset_id": params.get('dataset'),
            "frequency": params.get('frequency')
        }
        try:
            dataset = toolkit.get_action('package_show')(context, {'id': config_dict.get('dataset_id')})
        except NotFound as e:
            h.flash_error(toolkit._('Selected dataset does not exists'))
            return self.get()
        results = toolkit.get_action('refresh_datastore_dataset_create')(context, config_dict)
        extra_vars = self._setup_extra_template_variables()
        extra_vars["data"] = results
        return toolkit.render('admin/datastore_refresh.html', extra_vars=extra_vars)

def register_datavicmain_plugin_rules(blueprint):
    blueprint.add_url_rule('/dataset/<id>/historical', view_func=historical)
    blueprint.add_url_rule('/dataset/purge/<id>', view_func=purge)
    blueprint.add_url_rule('/ckan-admin/datastore-refresh-config',
                view_func=DatastoreRefreshConfigView.as_view(str('datastore_refresh_config')))

register_datavicmain_plugin_rules(datavicmain)