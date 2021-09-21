from ckanapi import LocalCKAN,RemoteCKAN, NotFound, CKANAPIError
import csv


iar = 'https://directory.data.vic.gov.au/'
iarapikey = 'c8a89820-a159-4c84-947d-3cb55c5a6156'

local = 'http://datavic-ckan.docker.amazee.io/'
iarCKAN = RemoteCKAN(iar, apikey=iarapikey)

iar_datasets = []
local_datasets = []

with RemoteCKAN(iar, apikey=iarapikey) as iarCKAN:
    result = iarCKAN.action.package_search(fq='res_format:WMS')
    print(result.get('count'))
    iar_datasets = result.get('results', [])

with RemoteCKAN(local, apikey=iarapikey) as localCKAN:
    result = localCKAN.action.package_search(fq='res_format:WMS')
    print(result.get('count'))
    local_datasets = result.get('results', [])


missing_datasets = []
# missing_datasets = [dataset for d, dataset in zip(iar_datasets, local_datasets) if dataset.get('full_metadata_url') != d.get('full_metadata_url')]

# for dataset in local_datasets:
    # if dataset.get('full_metadata_url') not in local_datasets:
        # missing_datasets.append(dataset)
    # missing_datasets = [d for d in iar_datasets if dataset.get('full_metadata_url') != d.get('full_metadata_url')]

data_dict = {}
for i, item in enumerate(iar_datasets):
    data_dict[item['full_metadata_url']] = item

for item in local_datasets:
    if not item['full_metadata_url'] in data_dict:
        missing_datasets.append(item)


with open('missing_datasets.csv', 'w') as csv:
    header = "title\n"
    csv.write(header)
    for dataset in missing_datasets:
        row = "{0}\n".format(dataset.get('name'))
        csv.write(row)

