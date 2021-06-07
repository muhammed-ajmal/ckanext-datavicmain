from ckanapi import RemoteCKAN, NotFound
import json
import os

url = os.environ['LAGOON_ROUTE']
apikey = 'c8a89820-a159-4c84-947d-3cb55c5a6156'

try:
    with RemoteCKAN(url, apikey=apikey) as ckan:
        with open('metashare_datasets_created.csv', "w") as file:
            header = "title,url,full_metadata_url\n"
            file.write(header)
            start = 0
            rows = 1000
            datasets = []
            while start <= 6000:  # There should be less then 6000 so have this as backup to exit loop

                result = ckan.action.package_search(fq='groups:spatial-data', start=start, rows=rows)
                results = result.get('results', [])
                # If no results exist while loop
                if len(results) == 0:
                    print('No more results')
                    break
                for dataset in results:
                    if len(dataset.get('primary_purpose_of_collection', '')) > 0:
                        if dataset not in datasets:
                            row = "{0},{1}/dataset/{2},{3}\n".format(dataset.get('title').replace(',',''), url, dataset.get('name'), dataset.get('full_metadata_url'))
                            file.write(row)
                            datasets.append(dataset)

                start = start+rows
            # print(json.dumps(datasets))
            # print('\n'.join(datasets))
            print("Datasets created {0}".format(len(datasets)))

except Exception as ex:
    print(ex)
