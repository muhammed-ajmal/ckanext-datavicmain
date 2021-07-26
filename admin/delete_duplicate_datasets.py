from ckanapi import RemoteCKAN, NotFound, CKANAPIError
import csv


# url = os.environ['LAGOON_ROUTE']
odp = 'https://develop.discover.data.vic.gov.au'
apikey = 'c8a89820-a159-4c84-947d-3cb55c5a6156'
username = 'salsa'
iar = 'https://develop.directory.data.vic.gov.au'

# local = 'http://datavic-ckan.docker.amazee.io/'
# iarCKAN = iarCKAN(username=username)

purged_datasets = []

error_datasets = []

WHITELIST_DATASETS = ['popular-baby-names']


def purge_dataset(dataset):
    with RemoteCKAN(odp, apikey=apikey) as ckan:
        print("Purged for datsaet {0}".format(dataset))
        for names in WHITELIST_DATASETS:
            if names not in dataset.get('name'):
                ckan.call_action.purge_dataset(id=dataset.get('name'))


def get_datasets_from_odp():
    rows = 1000
    start = 0
    datasets = []
    with RemoteCKAN(odp, apikey=apikey) as odpCKAN:
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
        with RemoteCKAN(iar, apikey=apikey) as iarCKAN:
            try:
                iar_dataset = iarCKAN.action.package_show(id=dataset_id)
                if iar_dataset.get('private'):
                    purge_dataset(dataset)
                    purged_datasets.append(dataset)
            except NotFound:
                purge_dataset(dataset)
                purged_datasets.append(dataset)
            except CKANAPIError as e:
                error_datasets.append(dataset)
                print("Error for dataset {0} with error {1}".format(dataset_name, e))
    with open('odp_datasets_to_purge_uat.csv', 'w') as csvfile:
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
