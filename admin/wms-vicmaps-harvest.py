# !/usr/bin/python
from datetime import datetime
import dateutil
import dateutil.parser
import ckanapi  # download from https://github.com/ckan/ckanapi and include in your scraper repo
import sys
import requests
import xml.etree.ElementTree as ele_tree
import json
import re

from ckan.lib.munge import munge_title_to_name
from unidecode import unidecode
from cStringIO import StringIO
from pprint import pprint


if len(sys.argv) < 2:
    sys.stderr.write('Usage: vicmaps-harvest.py IAR_CKAN_URL IAR_CKAN_API_KEY')
    sys.exit(1)

url = sys.argv[1]
api_key = sys.argv[2]
ckan = ckanapi.RemoteCKAN(url, api_key)

# Not in use
#odp_ckan = ckanapi.RemoteCKAN(sys.argv[3], sys.argv[4])

delete_only = False

# print ckan.action.status_show()
from string import Template

extent_template = Template('''
    {"type": "Polygon", "coordinates": [[[$xmin, $ymin], [$xmax, $ymin], [$xmax, $ymax], [$xmin, $ymax], [$xmin, $ymin]]]}
    ''')
group_cache = {}


def get_group(input_group_title):
    # new_title = input_group_title
    # if new_title == 'Environment':
    #     new_title = 'Environmental'
    # group_id = munge_title_to_name(new_title).lower()
    # DATAVIC-72: All SDM datasets are assigned to the "Spatial Data" group only
    new_title = 'Spatial Data'
    group_id = 'spatial-data'
    if group_id not in group_cache:
        try:
            group_cache[group_id] = ckan.action.group_show(id=group_id, include_datasets=False)
        except ckanapi.NotFound:
            group_cache[group_id] = ckan.action.group_create(name=group_id, title=new_title, include_datasets=False)
    return group_cache[group_id], new_title


organization_cache = {}


def get_org(organization_title):
    organization_id = munge_title_to_name(organization_title).lower()
    if organization_id not in organization_cache:
        try:
            organization_cache[organization_id] = ckan.action.organization_show(id=organization_id,
                                                                                include_datasets=False)
        except ckanapi.NotFound:
            organization_cache[organization_id] = ckan.action.organization_create(name=organization_id,
                                                                                  title=organization_title)
    return organization_cache[organization_id]


def convert_date(date_str):
    if date_str == 'Current' or date_str == 'Not Known' or date_str == 'current':
        return datetime.now().strftime("%Y-12-31")
    date_str = date_str[:2] + " " + date_str[2:]
    # print dateStr
    return dateutil.parser.parse(date_str).isoformat().split("T")[0]


def test_vicgislite_urls(url):
    return re.search('http://www.data.vic.gov.au/vicgislite/', url)


def convert_vicgislite_urls(url, dataset_name):
    return url.replace(
        'http://www.data.vic.gov.au/vicgislite/sdmAccess.jsp',
        'https://discover.data.vic.gov.au/dataset/' + dataset_name + '/order'
    )


'''## http://services.land.vic.gov.au/catalogue/cxfservices/CatalogWebServiceV3?wsdl
from pysimplesoap.client import SoapClient
client = SoapClient(wsdl="CatalogWebServiceV3.wsdl.xml", http_headers={'Authorization': 'Basic Z3Vlc3Q6Z3Vlc3Q=', 'User-Agent': 'Axis2'})
catalogues = client.getCatalogues(userName='guest')
catalogueList = catalogues['return'][0]['Catalogue']
for catalogueL in catalogueList:
    print catalogueList['layerList']'''

whitespace = re.compile('\s+')
url = 'http://services.land.vic.gov.au/catalogue/cxfservices/CatalogWebServiceV3'
payload = '<?xml version="1.0" encoding="UTF-8"?><soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"><soapenv:Body><ns1:getCatalogues xmlns:ns1="http://webservices.catalogue.dialog.com/"><userName>guest</userName></ns1:getCatalogues></soapenv:Body></soapenv:Envelope>'
# headers = {"Authorization": "Basic am1hZGV4OnBhc3N3b3Jk", #jmadex:password
headers = {"Authorization": "Basic Z3Vlc3Q6Z3Vlc3Q=",  # guest:password
           'SOAPAction': "http://webservices.catalogue.dialog.com/CatalogueWebService/getCatalogues",
           'User-Agent': 'Axis2'}
r = requests.post(url, data=payload, headers=headers)
tree = ele_tree.parse(StringIO(unidecode(r.text)))
with open('/tmp/vicmapsout.xml', 'w') as file:
    file.write(unidecode(r.text))
# tree = ET.parse('/tmp/vicmapsout.xml')
root = tree.getroot()
catalogues = root.findall('.//return')[0]
line_pat = re.compile(r'\. |: ')
used_slugs = []
datasets_created = []
datasets_updated = []
datasets_errors = []
datasets_skipped = []

# @Todo: remove this limit
limit = 0

for catalogue in catalogues:
    print(len(catalogues))
    groups = {"description": "", "name": "Spatial Data"}
    for layerGroup in catalogue.find('{http://model.catalogue.dialog.com}groupList'):
        groups[layerGroup.find('{http://model.catalogue.dialog.com}id').text] = \
            {"description": layerGroup.find('{http://model.catalogue.dialog.com}description').text,
             "name": layerGroup.find('{http://model.catalogue.dialog.com}name').text.replace("Environment",
                                                                                             "Environmental")}
    catalogs = catalogue.find('{http://model.catalogue.dialog.com}layerList')
    print("************************************************")
    print("************************************************")
    print(len(catalogs))
    print("************************************************")
    print("************************************************")
    for layerTag in catalogue.find('{http://model.catalogue.dialog.com}layerList'):

        # @Todo: remove this limit
        # if limit >= 10:
        #     print 'Limit reached - exiting loop'
        #     break
        # else:
        #     limit += 1
        layer = {}
        for layerAttribute in layerTag:
            attId = layerAttribute.tag.split("}")[1][0:]
            if attId == 'description' or attId == 'details':
                layer[attId] = json.loads(
                    re.sub(whitespace, ' ', layerAttribute.text.strip().replace('\n', ' ').strip()))
            else:
                layer[attId] = layerAttribute.text
        # print json.dumps(layer)
        # We only want to create/update datasets that have wmsURL https://digital-engagement.atlassian.net/browse/DATAVIC-308
        if not layer['details']['wmsUrl']:
            datasets_skipped.append(layer['title'])
            print("Dataset {0} does not have wms resource so skipping".format(layer['title'].strip()))
            continue

        pkg_dict = {'groups': [], 'resources': [], 'extract': ''}
        update = False
        new = True

        # @Todo: Remove this output
        # print '==============================================================='
        # print 'RAW LAYER DETAILS:'
        # print '==============================================================='
        # pprint(layer)
        # print '==============================================================='
        layer_title = layer['title'].strip()[:93] + ' - WMS'
        pkg_name = munge_title_to_name(layer_title)
        if pkg_name in used_slugs:
            continue
        used_slugs.append(pkg_name)
        if delete_only:
            continue

        try:
            pkg_dict = ckan.action.package_show(id=pkg_name)
            new = False
            print(pkg_name + " existing found")

            if pkg_dict.get('state', "") == 'deleted':
                print(pkg_dict['name'] + " is deleted. Undeleting...")
                pkg_dict['state'] = 'active'
                update = True
        except ckanapi.NotFound:
            pass
            # print(pkg_name + " not found, must be new")
        except ckanapi.CKANAPIError, e:
            print("CKAN api has failed with the following error: " + str(e) + " skipping...")
            continue

        def get_extra(key, package_dict):
            for extra in package_dict.get('extras', []):
                if extra['key'] == key:
                    return extra

        # DATAVIC-184: Add defaults for required fields
        if 'extras' not in pkg_dict:
            pkg_dict['extras'] = [
                {'key': 'update_frequency', 'value': 'unknown'},
                {'key': 'personal_information', 'value': 'no'},
                {'key': 'protective_marking', 'value': 'Public Domain'},
                {'key': 'access', 'value': 'yes'}
            ]

        # DATAVIC-184: Only set `date_created_data_asset` for new datasets
        if new:
            pkg_dict['extras'].append({'key': 'date_created_data_asset', 'value': datetime.utcnow().isoformat()})

        # DATAVIC-184: Add default tags
        pkg_dict['tags'] = [
            {'name': 'spatial'},
            {'name': 'mapping'},
            {'name': 'mapping service'},
            {'name': 'vicmap'},
        ]

        pkg_dict['geo_data'] = '1'

        pkg_dict['public'] = 'true'

        if pkg_dict.get("name", "") != pkg_name:
            # print "name changed"
            update = True
            pkg_dict['name'] = pkg_name

        if pkg_dict.get("title", "") != layer_title:
            # print "title changed"
            update = True
            pkg_dict['title'] = layer_title

        if pkg_dict.get("license_id", "") != 'cc-by':
            # print "license_id changed"
            update = True
            pkg_dict['license_id'] = 'cc-by'

        # DATAVIC-184: REMOVED - Data.Vic schema does not have an `external_id` field
        # if pkg_dict.get("external_id", "") != layer['id']:
        #     # update = True
        #     pkg_dict['external_id'] = layer['id']

        current_extract = get_extra('extract', pkg_dict)

        if len(layer['description']['abstractData']) > 255:
            extract = re.split(line_pat, layer['description']['abstractData'])[0]

            if current_extract and current_extract != extract:
                update = True
                # print "extract changed"
                pkg_dict['extras'].remove(current_extract)

            pkg_dict['extras'].append({'key': 'extract', 'value': extract})

            if pkg_dict.get("notes", "") != layer['description']['abstractData']:
                update = True
                # print "notes changed"
                pkg_dict['notes'] = layer['description']['abstractData']
        else:
            if layer['description'].get('purpose') and pkg_dict.get("notes", "") != layer['description'][
                'purpose'].strip():
                update = True
                # print "notes changed"
                pkg_dict['notes'] = layer['description']['purpose'].strip()

            if current_extract and current_extract != layer['description']['abstractData']:
                update = True
                # print "extract changed"
                pkg_dict['extras'].remove(current_extract)

            pkg_dict['extras'].append({'key': 'extract', 'value': layer['description']['abstractData']})

        # DATAVIC-184: REMOVED - Data.Vic schema does not have an `accuracy` field
        # if pkg_dict.get("accuracy", "") != layer['details']['attributeAccuracy'] + "\n" + layer['details'][
        #     'positionalAccuracy']:
        #     update = True
        #     print "accuracy changed"
        #     pkg_dict['accuracy'] = layer['details']['attributeAccuracy'] + "\n" + layer['details']['positionalAccuracy']

        # DATAVIC-184: REMOVED - Data.Vic schema does not have an `scale` field
        # if pkg_dict.get("scale", None) != layer['details']['scale']:
        #     update = True
        #     print "scale changed"
        #     pkg_dict['scale'] = layer['details']['scale']

        full_metadata_url = get_extra('full_metadata_url', pkg_dict)

        if full_metadata_url and full_metadata_url != layer['details']['metadataUrl']:
            update = True
            # print "full_metadata_url changed"
            pkg_dict['extras'].remove(full_metadata_url)
        pkg_dict['extras'].append({'key': 'full_metadata_url', 'value': layer['details']['metadataUrl']})

        # DATAVIC-184: REMOVED - Data.Vic schema does not have an `external_catalogue` field
        # if pkg_dict.get("external_catalogue", "") != layer['siteKey']:
        #     update = True
        #     print "external_catalogue changed"
        #     pkg_dict['external_catalogue'] = layer['siteKey']

        # DATAVIC-184: REMOVED - Data.Vic schema does not have an `citation` field
        # if pkg_dict.get("citation", "") != layer['details']['attribution']:
        #     update = True
        #     print "citation changed"
        #     pkg_dict['citation'] = layer['details']['attribution']

        if not pkg_dict.get("organization") or pkg_dict.get("organization", {}).get('title', '') != \
                layer['description']['custodian']:
            update = True
            # print "org changed"
            org_name = layer['description']['custodian'].strip()
            try:
                # print org_name + " search"
                org = get_org(org_name)
                pkg_dict['owner_org'] = org['id']
            except ckanapi.NotFound:
                print org_name + " not found"

        # DATAVIC-72: Add all SDM datasets to spatial-data group
        try:
            pkg_dict['groups'] = [{'id': get_group('Spatial Data')[0]['id']}]
        except ckanapi.NotFound:
            print "group not found, skipping..."
            continue
        # try:
        #     pkg_dict['groups'].append({'id': get_group('Spatial Data')[0]})
        # except ckanapi.NotFound:
        #     print "group not found, skipping..."
        #     continue
        # except ckanapi.CKANAPIError, e:
        #     print "CKAN api has failed with the following error: " + str(e) + " skipping..."
        #     continue
        # if layer['groupId']:
        #     for groupId in layer['groupId'].split(','):
        #         group_title = groups[groupId]['name']
        #         try:
        #             group, group_title = get_group(group_title)
        #             pkg_dict['groups'].append({'id': group['id']})
        #         except ckanapi.NotFound:
        #             print "group not found: " + group_title + "skipping..."
        #             continue
        #         except ckanapi.CKANAPIError, e:
        #             print "CKAN api has failed with the following error: " + str(e) + " skipping..."
        #             continue
        wms_dict = {'format': 'WMS'}
        new_res = True
        if len(pkg_dict['resources']) > 0:
            wms_dict = pkg_dict['resources'][0]
            new_res = False

        if wms_dict.get('name', '') != layer_title:
            update = True
            # print "wms name changed"
            wms_dict['name'] = layer_title
        if layer['details']['wmsUrl']:
            wms_url = layer['details']['wmsUrl'].replace('httpproxy', 'publicproxy/guest') + "?layers=" + layer['name']
            wms_preview_url = layer['details']['publicPreviewUrl'].replace('httpproxy', 'publicproxy/guest')

            # if wms_dict.get('wms_api_url', '') != wms_url:
            #     update = True
            #     # print "wms url 2 changed"
            #     wms_dict['format'] = 'wms'
            #     # wms_dict['wms_url'] = wms_preview_url
            #     wms_dict['wms_api_url'] = wms_url
            #     wms_dict['wms_layer'] = layer['name']
            #     wms_dict['visgis_preview'] = 'active'
            
            if wms_dict.get('url', '') != wms_preview_url:
                update = True
                # print "wms url changed"
                wms_dict['url'] = wms_preview_url
        # Removed for https://digital-engagement.atlassian.net/browse/DATAVIC-308
        # if wms_dict.get('public_order_url', '').strip() != layer['details']['wms_preview_url'].strip():
        #     update = True
        #     print "public_order_url changed"
        #     wms_dict['public_order_url'] = layer['details']['wms_preview_url'].strip()
        if wms_dict.get('attribution', '') != layer['details']['attribution']:
            update = True
            # print "wms attribution changed"
            wms_dict['attribution'] = layer['details']['attribution']
        if wms_dict.get('period_start', '') != convert_date(layer['details']['beginDate']):
            update = True
            # print "wms period_start changed"
            wms_dict['period_start'] = convert_date(layer['details']['beginDate'])
        if wms_dict.get('period_end', '') != convert_date(layer['details']['endDate']):
            update = True
            # print "wms period_end changed"
            wms_dict['period_end'] = convert_date(layer['details']['endDate'])
        # print wms_dict
        if new_res:
            pkg_dict['resources'].append(wms_dict)
        else:
            pkg_dict['resources'][0] = wms_dict

        # Change URLs from 'http://www.data.vic.gov.au' to 'https://sdm.iar.vic.gov.au'
        # Removed for https://digital-engagement.atlassian.net/browse/DATAVIC-308
        # if 'public_order_url' in pkg_dict['resources'][0] and test_vicgislite_urls(pkg_dict['resources'][0]['public_order_url']):
        #     pkg_dict['resources'][0]['public_order_url'] = convert_vicgislite_urls(pkg_dict['resources'][0]['public_order_url'], pkg_dict['name'])
        if 'url' in pkg_dict['resources'][0] and test_vicgislite_urls(pkg_dict['resources'][0]['url']):
            pkg_dict['resources'][0]['url'] = convert_vicgislite_urls(pkg_dict['resources'][0]['url'], pkg_dict['name'])

        if update:
            try:
                pkg_dict['geo_coverage'] = layer['details']['boundingbox']
                bbox = layer['details']['boundingbox'].split(',')
                xmin = float(bbox[0])
                xmax = float(bbox[2])
                ymin = float(bbox[1])
                ymax = float(bbox[3])

                # Some publishers define the same two corners for the bbox (ie a point),
                # that causes problems in the search if stored as polygon
                if xmin == xmax or ymin == ymax:
                    extent_string = Template('{"type": "Point", "coordinates": [$x, $y]}').substitute(
                        x=xmin, y=ymin
                    )
                else:
                    extent_string = extent_template.substitute(
                        xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax
                    )

                pkg_dict['spatial'] = extent_string.strip()
            except:
                pass

            try:
                if new:
                    pkg = ckan.call_action('package_create', pkg_dict)  # create a new dataset?
                    print pkg_dict['name'] + " created \n"
                    datasets_created.append(pkg_dict)
                else:
                #   pkg = ckan.call_action('package_update', pkg_dict)  # create a new dataset?
                    print pkg_dict['name'] + " updated \n"
                    datasets_updated.append(pkg_dict)
                #
                # # @Todo remove this output
                # pprint(pkg_dict)
            except ckanapi.errors.CKANAPIError, e:
                datasets_errors.append(pkg_dict)
                print str(e)
                continue

        else:
            print " no changes for " + layer_title + " \n"
            # print pkg_dict

# @Todo: Figure out what this does - it involves the ODP
# for c in [ckan, odp_ckan]:
#     spatial_packages = []
#     try:
#         spatial_group = c.call_action('group_show', {'id': 'spatial-data'})
#         for package in spatial_group['packages']:
#             if 'external_id' in package and package['external_id'] != "":
#                 spatial_packages.append(package['name'])
#     except ckanapi.errors.NotFound:
#         print 'Wrong id for Spatial Data'
#     except ckanapi.CKANAPIError, e:
#         print "CKAN api has failed with the following error: " + str(e) + " skipping..."
#         continue
#     spatial_packages = filter(lambda x: x not in used_slugs, spatial_packages)
#     for spack in spatial_packages:
#         c.call_action('package_delete', {'id': spack})
#         print spack, 'deleted'

# Output stats on number of datasets created and updated
print '= = = = = = = = = = = = = = = = = = = = = ='
print str(len(datasets_created)) + ' datasets created'
print str(len(datasets_updated)) + ' datasets updated'
print str(len(datasets_errors)) + ' datasets errors'
print str(len(datasets_skipped)) + ' datasets  skipped'
print '= = = = = = = = = = = = = = = = = = = = = ='
url = sys.argv[1]
with open('sdm_datasets_created.csv', 'w') as csv:
    header = "title,url,full_metadata_url\n"
    csv.write(header)
    for dataset in datasets_created:
        row = "{0},{1}/dataset/{2},{3}\n".format(dataset.get('title').replace(',',''), url, dataset.get('name'), dataset.get('full_metadata_url'))
        csv.write(row)

with open('sdm_datasets_updated.csv', 'w') as csv:
    header = "title,url,full_metadata_url\n"
    csv.write(header)
    for dataset in datasets_updated:
        row = "{0},{1}/dataset/{2},{3}\n".format(dataset.get('title').replace(',',''), url, dataset.get('name'), dataset.get('full_metadata_url'))
        csv.write(row)

with open('sdm_datasets_errors.csv', 'w') as csv:
    header = "title,url,full_metadata_url\n"
    csv.write(header)
    for dataset in datasets_errors:
        row = "{0},{1}/dataset/{2},{3}\n".format(dataset.get('title', '').replace(',',''), url, dataset.get('name'), dataset.get('full_metadata_url'))
        csv.write(row)

with open('sdm_datasets_skipped.csv', 'w') as csv:
    header = "title\n"
    csv.write(header)
    for dataset in datasets_skipped:
        row = "{0}\n".format(dataset)
        csv.write(row)
