# -*- coding: utf-8 -*-

import click
import ckan.plugins.toolkit as tk

import ckanext.datavicmain.datastore_config.model as datavic_model
import ckanext.datavicmain.datastore_config.helpers as helpers


@click.group(name=u'datastore_config', short_help=u'Manage datastore_config commands')
def datastore_config():
    """Example of group of commands.
    """
    pass

@datastore_config.command("init_db")
def init_db():
    """Initialise the database tables required for datastore refresh config
    """
    click.secho(u"Initializing Datastore Refresh Config tables", fg=u"green")

    try:
        datavic_model.setup()
    except Exception as e:
        tk.error_shout(str(e))

    click.secho(u"Datastore Refresh Config DB tables are setup", fg=u"green")

@datastore_config.command("call_cron_job")
@click.argument(u"frequency")
def call_cron_job(frequency):
    
    if not frequency:
        tk.error_shout("Please provide frequency")
    
    datasets = tk.get_action('refresh_dataset_datastore_by_frequency')({}, {"frequency": frequency})
    
    if not datasets:
        click.secho("No datasets with this criteria", fg="yellow")

    for dataset in datasets:
        resources = dataset.get('Package').resources
        #resources = data_dict.get('resource', [])
        for res in resources:
            res = tk.get_action('xloader_submit')({}, {"resource_id": res.id })

def get_commands():
    return [datastore_config]