from ckanapi import LocalCKAN, RemoteCKAN, NotFound, CKANAPIError
import json
import os
import csv


#url = os.environ['LAGOON_ROUTE']
url = 'https://develop.discover.data.vic.gov.au'
apikey = 'c8a89820-a159-4c84-947d-3cb55c5a6156'
username = 'salsa'
local = 'http://datavic-ckan.docker.amazee.io/'

# localCKAN = LocalCKAN(username=username)

purged_datasets = []


# def purge_dataset(dataset):
#     with RemoteCKAN(url, apikey=apikey) as ckan:
#         ckan.call_action.purge_dataset(dataset)


def get_datasets_from_odp():
    rows = 1000
    start = 0
    datasets = []
    with RemoteCKAN(url, apikey=apikey) as ckan:
        result = ckan.action.package_search(fq='', start=start, rows=rows)

        while result["count"] > start:
            start = start + rows
            results = result.get('results', [])
            datasets.extend(results)
            result = ckan.action.package_search(fq='', start=start, rows=rows)
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
        #dataset_id = dataset.get('id')
        dataset_name = dataset.get('name')
        try:
            with RemoteCKAN(local, apikey=apikey) as localCKAN:
                local_dataset = localCKAN.action.package_show(id=dataset_name)
                if local_dataset.get('private'):
                    #purge_dataset(dataset_name)
                    purged_datasets.append(dataset)
        except NotFound:
            # purge_dataset(dataset_name)
            purged_datasets.append(dataset)
            # print("Dataset not found")
        except CKANAPIError:
            pass

    with open('odp_datasets_to_purge_uat.csv', 'w') as csvfile:
        csvwriter = csv.writer(csvfile)
        header = "title, status"
        csvwriter.writerow(header)
        i = 1
        for dataset in purged_datasets:
            print("Write {0} dataset to csv file ".format(i))
            data = [i, safe_str(dataset.get('title')), dataset.get('private')]
            csvwriter.writerow(data)
            i += 1


if __name__ == "__main__":
    main()