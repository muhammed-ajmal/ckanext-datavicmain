
from __future__ import print_function
from __future__ import absolute_import
import argparse
import sys
from collections import defaultdict
from six.moves import input
from six import text_type
from ckanapi import RemoteCKAN, NotFound
import json
import os
import ckan.logic as logic

from ckanapi.errors import CKANAPIError

url = os.environ['LAGOON_ROUTE']
apikey = 'c8a89820-a159-4c84-947d-3cb55c5a6156'

datasets_errors = []
_context = None

def get_context():
    from ckan import model
    import ckan.logic as logic
    global _context
    if not _context:
        user = logic.get_action(u'get_site_user')(
            {u'model': model, u'ignore_auth': True}, {})
        _context = {u'model': model, u'session': model.Session,
                    u'user': user[u'name']}
    return _context

def get_sdm_datasets(result):
    datasets = []
    for dataset in result:
        try:
            data_dict = logic.get_action('package_show')(get_context(), { "id": dataset })
            datasets.append(data_dict)
        except CKANAPIError as e:
            print(e)
            datasets_errors.append(dataset)
            continue

    return datasets


def collect_datasets():
    start = 0
    rows = 1000
    datasets = []
    datasets_failed = []
    # while start < 3000:  # There should be less then 2000 so have this as backup to exit loop

    #result = ckan.action.package_search(fq='groups:spatial-data', start=start, rows=rows)

    result = logic.get_action('package_list')(get_context(), {})
    results = get_sdm_datasets(result)
    

    print ("There are {0} spatial-data datasets".format(len(results)))
    for dataset in results:

        for resource in dataset.get('resources', []):
            if resource.get('public_order_url', None)  or resource.get('wms_url') or 'order?email=:emailAddress' in resource.get('url', ''):
                datasets.append(dataset)
                data_dict = dataset.get('id')
                if dataset not in datasets:
                    f = open('legacy-sdm-datasets/{}.json'.format(dataset.get('id')), "w")
                    f.write(json.dumps(dataset, indent=2))
                    f.close()
                    datasets.append(dataset)

    print("Datasets to delete {0}".format(len(datasets)))

    with open('sdm_datasets_deleted.csv', 'w') as csv:
        header = "title,url,full_metadata_url\n"
        csv.write(header)
        for dataset in datasets:
            for resource in dataset.get('resources', []):
                try:
                    logic.get_action('datastore_delete')(get_context(), dict(id=resource.get('id'), force=True))
                    print('Successfully deleted datastore for {}'.format(resource.get('resource_id')))
                except NotFound as ex:
                    pass
                    # log and ignore
                    # print('datastore_delete: {}'.format(ex))

                try:
                    logic.get_action('resource_view_delete')(get_context(), dict(id=resource.get('id'), force=True))
                    print('Successful deleted resource_view for {}'.format(resource.get('resource_id')))
                except NotFound as ex:
                    pass
                    # log and ignore
                    # print('resource_view_delete: {}'.format(ex))

            try:
                logic.get_action('package_delete')(get_context(), dict(id=dataset.get('id')))
                logic.get_action('dataset_purge')(get_context(), dict(id=dataset.get('id')))
                print('Successfully deleted {}'.format(dataset.get('name')))

                row = "{0},{1}/dataset/{2},{3}\n".format(dataset.get('title').replace(',',''), url, dataset.get('name'), dataset.get('full_metadata_url'))
                csv.write(row)
            except Exception as ex:
                # log and ignore
                datasets_failed.append(dataset)
                print('Failed to delete {0}: {1}'.format(dataset.get('name'), ex))
                # print(dataset)

    with open('sdm_datasets_failed_to_delete.csv', 'w') as csv:
        header = "title,url,full_metadata_url\n"
        csv.write(header)
        for dataset in datasets_failed:
            row = "{0},{1}/dataset/{2},{3}\n".format(dataset.get('title').replace(',',''), url, dataset.get('name'), dataset.get('full_metadata_url'))
            csv.write(row)

    with open('wms_datasets_errors.csv', 'w') as csv:
        header = "title,url,full_metadata_url\n"
        csv.write(header)
        for dataset in datasets_errors:
            row = "{0},{1}/dataset/{2},{3}\n".format(dataset.get('title').replace(',',''), url, dataset.get('name'), dataset.get('full_metadata_url'))
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
    collect_datasets()