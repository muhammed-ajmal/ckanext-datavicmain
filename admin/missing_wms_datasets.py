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


missing_datasets = [
    dataset
    for dataset in iar_datasets
    if dataset.get('name') not in local_datasets
]


with open('missing_datasets.csv', 'w') as csv:
    header = "title\n"
    csv.write(header)
    for dataset in missing_datasets:
        row = "{0}\n".format(dataset.get('name'))
        csv.write(row)

