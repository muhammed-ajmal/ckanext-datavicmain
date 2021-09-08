import logging
import ckan.model as model
import ckan.plugins.toolkit as toolkit

from flask import Blueprint
from flask.views import MethodView
from ckanext.datavicmain.datastore_config import helpers

NotFound = toolkit.ObjectNotFound
get_action = toolkit.get_action
h = toolkit.h
render = toolkit.render
log = logging.getLogger(__name__)
datastore_config = Blueprint('datastore_config', __name__)


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

        return render('admin/datastore_refresh.html', extra_vars=extra_vars)

    def post(self):
        context = self._get_context()
        params = helpers.clean_params(toolkit.request.form)
        if params.get('delete_config'):
            get_action('refresh_dataset_datastore_delete')(context, {'id': params.get('delete_config')})
            h.flash_success(toolkit._("Succesfully deleted configuration"))
            return self.get()

        if not params.get('dataset'):
            h.flash_error(toolkit._('Please select dataset'))
            return self.get()
        try:
            dataset = get_action('package_show')(context, {'id': params.get('dataset')})
        except NotFound as e:
            h.flash_error(toolkit._(f'Selected dataset {params.get("dataset")} does not exists'))
            return self.get()

        frequency = helpers.get_datasore_refresh_config_option(params.get('frequency'))
        config_dict = {
            "dataset_id": dataset.get('id'),
            "frequency": frequency.pop()
        }
        results = get_action('refresh_datastore_dataset_create')(context, config_dict)
        extra_vars = self._setup_extra_template_variables()
        extra_vars["data"] = results
        return render('admin/datastore_refresh.html', extra_vars=extra_vars)


def register_plugin_rules(blueprint):
    blueprint.add_url_rule('/ckan-admin/datastore-refresh-config',
                           view_func=DatastoreRefreshConfigView.as_view(str('datastore_refresh_config')))


register_plugin_rules(datastore_config)
