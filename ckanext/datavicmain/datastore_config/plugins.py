import ckan.plugins as p
import ckan.plugins.toolkit as toolkit

from ckanext.datavicmain.datastore_config import actions, helpers, cli, view


class RefreshDatasetDatastore(p.SingletonPlugin):
    p.implements(p.ITemplateHelpers)
    p.implements(p.IActions)
    p.implements(p.IConfigurer)
    p.implements(p.IClick)
    p.implements(p.IBlueprint)

    # ITemplateHelpers
    def get_helpers(self):
        return {
            'get_frequency_options': helpers.get_frequency_options,
            'get_datastore_refresh_configs': helpers.get_datastore_refresh_configs,
            'get_datasore_refresh_config_option': helpers.get_datasore_refresh_config_option,
        }

    # IActions
    def get_actions(self):
        return {
            'refresh_datastore_dataset_create': actions.refresh_datastore_dataset_create,
            'refresh_dataset_datastore_list': actions.refresh_dataset_datastore_list,
            'refresh_dataset_datastore_delete': actions.refresh_dataset_datastore_delete,
            'refresh_dataset_datastore_by_frequency': actions.refresh_dataset_datastore_by_frequency
        }

    # IConfigurer
    def update_config(self, config):
        # Add extension templates directory
        toolkit.add_template_directory(config, u'templates')
        # Add a new ckan-admin tabs for our extension
        toolkit.add_ckan_admin_tab(
            config,
            'datastore_config.datastore_refresh_config',
            'Datastore refresh',
            config_var='ckan.admin_tabs'
        )

    # IClick
    def get_commands(self):
        return cli.get_commands()

    # IBlueprint
    def get_blueprint(self):
        return view.datastore_config
