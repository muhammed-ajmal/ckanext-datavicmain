from ckanapi import RemoteCKAN, NotFound, CKANAPIError
import csv


# url = os.environ['LAGOON_ROUTE']
odp = 'https://discover.data.vic.gov.au/'
# odp = 'https://nginx.pr-126.datavic-ckan-odp.sdp2.sdp.vic.gov.au/'
# iar = 'https://ckan.pr-148.datavic-ckan.sdp2.sdp.vic.gov.au/'
odpapikey = '0eabf140-439c-46a0-81bc-1c73320303b8'
iarapikey = 'c8a89820-a159-4c84-947d-3cb55c5a6156'
username = 'salsa'
iar = 'https://directory.data.vic.gov.au/'

# local = 'http://datavic-ckan.docker.amazee.io/'
iarCKAN = RemoteCKAN(iar, apikey=iarapikey)
odpCKAN = RemoteCKAN(odp, apikey=odpapikey)

purging_dataset = []

purged_datasets = []
error_datasets = []

WHITELIST_DATASETS = ['popular-baby-names']


def purge_dataset(datasets):
    with RemoteCKAN(odp, apikey=odpapikey) as ckan:
        for dataset in datasets:
            for names in WHITELIST_DATASETS:
                if names not in dataset.get('name'):
                    print("Purging dataset {0}".format(dataset.get('name')))
                    purged_datasets.append(dataset)
                    try:
                        ckan.action.dataset_purge(id=dataset.get('name'))
                    except CKANAPIError:
                        print("Error purging dataset {0}".format(dataset.get('name')))


def get_datasets_from_odp():
    rows = 1000
    start = 0
    datasets = []
    result = odpCKAN.action.package_search(fq='', start=start, rows=rows)

    while result["count"] > start:
        start += rows
        results = result.get('results', [])
        datasets.extend(results)
        result = odpCKAN.action.package_search(fq='', start=start, rows=rows)
    print("There are {0} datasets".format(len(datasets)))
    return datasets


def main():
    datasets = get_datasets_from_odp()
    for dataset in datasets:
        # get dataset id and name
        dataset_id = dataset.get('id')
        dataset_name = dataset.get('name')
        try:
            with RemoteCKAN(iar, apikey=iarapikey) as iarCKAN:
                # import pdb; pdb.set_trace()
                result = iarCKAN.action.package_search(q='id:{0}'.format(dataset_id))
                results = result.get('results', [])
                # print("Processing dataset {}".format(dataset_name))
                if len(results) == 0 or results[0].get('private'):
                    print("Add for purge {0}".format(dataset_name))
                    purging_dataset.append(dataset)
        except NotFound:
            purging_dataset.append(dataset)
            # purged_datasets.append(dataset)
        except CKANAPIError as e:
            error_datasets.append(dataset)
            print("Error for dataset {0} with error {1}".format(dataset_name, e.message))

    purge_dataset(purging_dataset)
    with open('odp_purged_datasets_prod.csv', 'w') as csvfile:
        write_to_csv(csvfile, purged_datasets)
    with open('error_datasets.csv', 'w') as csvfile:
        write_to_csv(csvfile, error_datasets)


def write_to_csv(csvfile, datasets):
    csvwriter = csv.writer(csvfile)
    header = ["No., ID,  Name, Status"]
    csvwriter.writerow(header)
    for i, dataset in enumerate(datasets, start=1):
        print("Write {0} dataset to csv file ".format(i))
        data = [i, dataset.get('id'), dataset.get('name'), dataset.get('private')]
        csvwriter.writerow(data)


if __name__ == "__main__":
    main()
