
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
from ckanext.datavicmain.cli import get_commands

from ckan.common import config, request

_t = toolkit._

class RefreshDatasetDatastore(p.SingletonPlugin):

    p.implements(p.ITemplateHelpers)
    p.implements(p.IConfigurable, inherit=True)
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IActions)
    p.implements(p.IClick)
    
    toolkit.add_ckan_admin_tab(toolkit.config, 'datavicmain.datastore_refresh_config', 'Datastore refresh',
                               config_var='ckan.admin_tabs')

    def get_helpers(self):
        return {  
            'get_frequency_options': helpers.get_frequency_options,
            'get_datastore_refresh_configs': helpers.get_datastore_refresh_configs
        }

    def get_actions(self):
        return {
            'refresh_datastore_dataset_create': actions.refresh_datastore_dataset_create,
            'refresh_dataset_datastore_list': actions.refresh_dataset_datastore_list,
            'refresh_dataset_datastore_delete': actions.refresh_dataset_datastore_delete
        }
    
    ## IConfigurable interface ##

    def configure(self, config):
        ''' Apply configuration options to this plugin '''
        pass
    
    def get_commands(self):
        return get_commands()
