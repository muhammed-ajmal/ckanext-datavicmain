from ckanapi import RemoteCKAN, NotFound
import json
import os

url = os.environ['LAGOON_ROUTE']
apikey = 'c8a89820-a159-4c84-947d-3cb55c5a6156'

try:
    with RemoteCKAN(url, apikey=apikey) as ckan:
        start = 0
        rows = 1000
        datasets = []
        datasets_failed = []
        while start < 3000:  # There should be less then 2000 so have this as backup to exit loop

            result = ckan.action.package_search(fq='groups:spatial-data', start=start, rows=rows)
            results = result.get('results', [])
            # If no results exist while loop
            if len(results) == 0:
                print('No more results')
                break
            print ("There are {0} spatial-data datasets".format(len(results)))
            exit
            for dataset in results:
                # print(dataset)
                # if len(dataset.get('resources', [])) > 1:
                    # print('Dataset {0} has {1} resource\n'.format(dataset.get('name'), len(dataset.get('resources', []))))
                for resource in dataset.get('resources', []):
                    # print(resource)
                    if resource.get('public_order_url', None)  or resource.get('wms_url') or 'order?email=:emailAddress' in resource.get('url', ''):
                        # data_dict = {"id": dataset.get('id')}
                        datasets.append(dataset)
                        data_dict = dataset.get('id')
                        if dataset not in datasets:
                            f = open('legacy-sdm-datasets/{}.json'.format(dataset.get('id')), "w")
                            f.write(json.dumps(dataset, indent=2))
                            f.close()
                            datasets.append(dataset)
                        # try:
                        #     # result = ckan.action.package_delete(id=dataset.get('id'))
                        #     # print('Successfully deleted {}'.format(dataset.get('id')))
                        # except Exception as ex:
                        #     # log and ignore
                        #     datasets_failed.append(dataset)
                        #     print('dataset_purge: {}'.format(ex))
                        #     print(dataset)
                        # print('Dataset {dataset_name} has resource {res_name} with public_order_url {public_order_url}\n'.format(\
                        #     dataset_name=dataset.get('name'), res_name=resource.get('name'), public_order_url=resource.get('public_order_url')))
            start = start+rows
        # print(json.dumps(datasets))
        # print('\n'.join(datasets))
        print("Datasets to delete {0}".format(len(datasets)))

        with open('sdm_datasets_deleted.csv', 'w') as csv:
            header = "title,url,full_metadata_url\n"
            csv.write(header)
            for dataset in datasets:
                for resource in dataset.get('resources', []):
                    try:
                        ckan.action.datastore_delete(id=resource.get('id'), force=True)
                        print('Successfully deleted datastore for {}'.format(resource.get('resource_id')))
                    except NotFound as ex:
                        pass
                        # log and ignore
                        # print('datastore_delete: {}'.format(ex))

                    try:
                        ckan.action.resource_view_delete(id=resource.get('id'), force=True)
                        print('Successful deleted resource_view for {}'.format(resource.get('resource_id')))
                    except NotFound as ex:
                        pass
                        # log and ignore
                        # print('resource_view_delete: {}'.format(ex))

                try:
                    ckan.action.package_delete(id=dataset.get('id'))
                    ckan.action.dataset_purge(id=dataset.get('id'))
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

except Exception as ex:
    print(ex)
