from ckanapi import LocalCKAN, RemoteCKAN, NotFound
import json
import os

url = os.environ['LAGOON_ROUTE']
apikey = 'c8a89820-a159-4c84-947d-3cb55c5a6156'

localCKAN = LocalCKAN()

purged_datasets = []

with RemoteCKAN(url, apikey=apikey) as ckan:
    result = ckan.action.package_search(fq='')
    results = result.get('results', [])
    # If no results exist while loop
    if len(results) == 0:
        print('No more results')
        break
    print("There are {0} datasets".format(len(results)))
    exit
    for dataset in results:
        # get dataset id and name
        dataset_id = dataset.get('id')
        dataset_name = dataset.get('name')
        try:
            local_dataset = localCKAN.action.package_show(dataset_id)
            if local_dataset.get('private'):
                print('ok')
        except NotFound, e:
            print("Dataset not found")

with open('sdm_datasets_failed_to_delete.csv', 'w') as csv:
    header = "title,url\n"
    csv.write(header)
    for dataset in purged_datasets:
        row = "{0},{1}/dataset/{2},{3}\n".format(dataset.get('title').replace(',',''), url, dataset.get('name'))
        csv.write(row)