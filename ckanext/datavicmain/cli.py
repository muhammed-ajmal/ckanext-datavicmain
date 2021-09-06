# -*- coding: utf-8 -*-

import click
import ckan.plugins.toolkit as tk
import ckan.model as model

import ckanext.datavicmain.model as datavic_model


@click.group(name=u'datavicmain', short_help=u'Manage datavicmain commands')
def datavicmain():
    """Example of group of commands.
    """
    pass

@datavicmain.command("init_db")
def init_db():
    """Initialise the database tables required for datastore refresh config
    """
    click.secho(u"Initializing Datastore Refresh Config tables", fg=u"green")

    try:
        datavic_model.setup()
    except Exception as e:
        tk.error_shout(str(e))

    click.secho(u"Datastore Refresh Config DB tables are setup", fg=u"green")

def get_commands():
    return [datavicmain]