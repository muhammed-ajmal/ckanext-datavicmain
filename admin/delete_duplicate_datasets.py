from ckanapi import RemoteCKAN, NotFound, CKANAPIError
import csv


# url = os.environ['LAGOON_ROUTE']
url = 'https://develop.discover.data.vic.gov.au'
apikey = 'c8a89820-a159-4c84-947d-3cb55c5a6156'
username = 'salsa'
local = 'http://datavic-ckan.docker.amazee.io/'

# iarCKAN = iarCKAN(username=username)

purged_datasets = []


# def purge_dataset(dataset):
#     with RemoteCKAN(url, apikey=apikey) as ckan:
#         ckan.call_action.purge_dataset(dataset)


def get_datasets_from_odp():
    rows = 1000
    start = 0
    datasets = []
    with RemoteCKAN(url, apikey=apikey) as odpCKAN:
        result = odpCKAN.action.package_search(fq='', start=start, rows=rows)

        while result["count"] > start:
            start += rows
            results = result.get('results', [])
            datasets.extend(results)
            result = odpCKAN.action.package_search(fq='', start=start, rows=rows)
        print("There are {0} datasets".format(len(datasets)))
    return datasets


def safe_str(obj):
    try:
        return str(obj)
    except UnicodeEncodeError:
        return obj.encode('ascii', 'ignore').decode('ascii')
    return ""


def main():
    datasets = get_datasets_from_odp()
    for dataset in datasets:
        # get dataset id and name
        dataset_id = dataset.get('id')
        dataset_name = dataset.get('name')
        with RemoteCKAN(local, apikey=apikey) as iarCKAN:
            try:
                # import pdb; pdb.set_trace()
                iar_dataset = iarCKAN.action.package_show(id=dataset_id)
                if iar_dataset.get('private'):
                    # purge_dataset(dataset_name)
                    purged_datasets.append(dataset)
            except NotFound:
                # purge_dataset(dataset_name)
                # import pdb; pdb.set_trace()
                try:
                    iar_dataset = iarCKAN.action.package_show(name_or_id=dataset_name)
                except NotFound:
                    purged_datasets.append(dataset)
                except CKANAPIError as e:
                    print("Error for dataset {0} with error {1}".format(dataset_name, e))
            except CKANAPIError as e:
                print("Error for dataset {0} with error {1}".format(dataset_name, e))
    with open('odp_datasets_to_purge_uat.csv', 'w') as csvfile:
        csvwriter = csv.writer(csvfile)
        header = ["No., ID,  Name, Status"]
        csvwriter.writerow(header)
        for i, dataset in enumerate(purged_datasets, start=1):
            print("Write {0} dataset to csv file ".format(i))
            data = [i, dataset.get('id'), safe_str(dataset.get('name')), dataset.get('private')]
            csvwriter.writerow(data)


if __name__ == "__main__":
    main()