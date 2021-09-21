from __future__ import print_function
from __future__ import absolute_import
import argparse
import json
import os


from ckan.common import config
import sqlalchemy

import ckan.logic as logic
from ckan.lib.dictization.model_dictize import package_dictize

import ckan.lib.jobs as jobs
import ckan.lib.navl.dictization_functions
import ckan.model as model

import ckan.plugins as plugins
import ckan.lib.search as search
import ckan.lib.plugins as lib_plugins


from ckan.common import _

NotFound = logic.NotFound
ValidationError = logic.ValidationError


_context = None
url = os.environ['LAGOON_ROUTE']

spatial_datasets = []

datasets_failed = []
datasets_errors = []

def get_context():
    global _context
    if not _context:
        user = logic.get_action(u'get_site_user')(
            {u'model': model, u'ignore_auth': True}, {})
        _context = {u'model': model, u'session': model.Session,
                    u'user': user[u'name']}
    return _context

def get_full_metadata_url(extras):
    for extra in extras:
        if extra['key'] == 'full_metadata_url':
            return extra['value']

def get_datasets():
    data_dict = {}
    packages = model.Session.query(model.Package).all()
    print("Collected {0} datasets".format(len(packages)))
    for package in packages:
        for group in package.get_groups():
            if group.name.lower() == 'spatial-data':
                spatial_datasets.append(package_dictize(package, get_context())) 
    print(len(spatial_datasets))

    delete_datasets(spatial_datasets)
    #print_datasets(spatial_datasets)

def print_datasets(spatial_datasets):
    with open('wms_datasets_after_deletion.csv', 'w') as csv:
        header = "title,url,full_metadata_url\n"
        csv.write(header)
        for dataset in spatial_datasets:
            full_metadata_url = get_full_metadata_url(dataset.get('extras'))
            row = "{0},{1}/dataset/{2},{3}\n".format(dataset.get('title').replace(',',''), url, dataset.get('name'), full_metadata_url)
            csv.write(row)

def delete_datasets(spatial_datasets):
    datasets = []

    # Find the WMS datasets that conain `public_oreder_url` or `wms_url`
    for dataset in spatial_datasets:

        for resource in dataset.get('resources', []):
            if resource.get('public_order_url', None)  or resource.get('wms_url') or 'order?email=:emailAddress' in resource.get('url', ''):
                datasets.append(dataset)
                if dataset not in datasets:
                    with open('legacy-sdm-datasets/{}.json'.format(dataset.get('id')), "w") as f:
                        f.write(json.dumps(dataset, indent=2))
                    datasets.append(dataset)

    with open('wms_datasets_to_be_deleted.csv', 'w') as csv:
        header = "title,url,full_metadata_url\n"
        csv.write(header)
        for dataset in datasets:
            full_metadata_url = get_full_metadata_url(dataset.get('extras'))
            row = "{0},{1}/dataset/{2},{3}\n".format(dataset.get('title').replace(',',''), url, dataset.get('name'), full_metadata_url)
            csv.write(row)

    print("Datasets to delete {0}".format(len(datasets)))
    with open('wms_datasets_deleted.csv', 'w') as csv:
        header = "title,url,full_metadata_url, format\n"
        csv.write(header)
        for dataset in datasets:
            dataset_url = "{0}dataset/{1}".format(url, dataset.get('name'))
            full_metadata_url = get_full_metadata_url(dataset.get('extras'))
            # for resource in dataset.get('resources', []):
            #     try:
            #         logic.get_action('datastore_delete')(get_context(), dict(id=resource.get('id'), force=True))
            #         print('Successfully deleted datastore for {}'.format(resource.get('resource_id')))
            #     except NotFound as ex:
            #         pass
            #         # log and ignore
            #         # print('datastore_delete: {}'.format(ex))

            #     try:
            #         logic.get_action('resource_view_delete')(get_context(), dict(id=resource.get('id'), force=True))
            #         print('Successful deleted resource_view for {}'.format(resource.get('resource_id')))
            #     except NotFound as ex:
            #         pass
            #         # log and ignore
            #         # print('resource_view_delete: {}'.format(ex))

            try:
                logic.get_action('package_delete')(get_context(), dict(id=dataset.get('id')))
                logic.get_action('dataset_purge')(get_context(), dict(id=dataset.get('id')))
                print('Successfully deleted {}'.format(dataset.get('name')))
                res_format = dataset.get('resources')[0].get('format')
                row = "{0},{1},{2}, {3}\n".format(dataset.get('title').replace(',',''), dataset_url, full_metadata_url, res_format)
                csv.write(row)
            except Exception as ex:
                # log and ignore
                datasets_failed.append(dataset)
                print('Failed to delete {0}: {1}'.format(dataset.get('name'), ex))
                # print(dataset)

    with open('wms_datasets_failed_to_delete.csv', 'w') as csv:
        header = "title,url,full_metadata_url\n"
        csv.write(header)
        for dataset in datasets_failed:
            full_metadata_url = get_full_metadata_url(dataset.get('extras'))
            row = "{0},{1},{2}\n".format(dataset.get('title').replace(',',''), dataset_url, full_metadata_url)
            csv.write(row)

    with open('wms_datasets_errors.csv', 'w') as csv:
        header = "title,url,full_metadata_url\n"
        csv.write(header)
        for dataset in datasets_errors:
            full_metadata_url = get_full_metadata_url(dataset.get('extras'))
            row = "{0},{1},{2}\n".format(dataset.get('title').replace(',',''), dataset_url, full_metadata_url)
            csv.write(row)


if __name__ == u'__main__':
    parser = argparse.ArgumentParser(usage=__doc__)
    parser.add_argument(u'-c', u'--config', help=u'CKAN config file (.ini)')
    args = parser.parse_args()
    assert args.config, u'You must supply a --config'
    print(u'Loading config')
    try:
        from ckan.cli import load_config
        from ckan.config.middleware import make_app
        make_app(load_config(args.config))
    except ImportError:
        # for CKAN 2.6 and earlier
        def load_config(config):
            from ckan.lib.cli import CkanCommand
            cmd = CkanCommand(name=None)

            class Options(object):
                pass
            cmd.options = Options()
            cmd.options.config = config
            cmd._load_config()
            return
        load_config(args.config)
    print("Collect datasets")
    get_datasets()