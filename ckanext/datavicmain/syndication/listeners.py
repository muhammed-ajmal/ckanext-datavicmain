import logging
from werkzeug.datastructures import FileStorage as FlaskFileStorage
import requests

import ckan.plugins.toolkit as tk
import ckan.model as model
from ckan.lib.uploader import get_resource_uploader
import ckanapi

import ckanext.syndicate.signals as signals
from ckanext.syndicate.utils import get_target

log = logging.getLogger(__name__)

@signals.after_syndication.connect
def after_syndication_listener(package_id, **kwargs):
    profile = kwargs["profile"]
    remote = kwargs["remote"]

    if "id" in remote:
        ckan = get_target(profile.ckan_url, profile.api_key)
        resources = remote.get('resources')

        pkg = model.Package.get(package_id)
        original_resources = pkg.resources

        for res in resources:
            if profile.ckan_url in res.get('url', ''):
                check_res = requests.head(res['url'])

                if not check_res.ok:
                    log.debug("File is not exists for {0} resource, copying it.".format(
                        res['id']
                    ))
                    org_res = [r for r in original_resources if r.id == res['id']]
                    if org_res:
                        uploader = get_resource_uploader(org_res[0].as_dict())
                        file_path = uploader.get_path(org_res[0].id)
                        try:
                            with open(file_path, 'rb') as file_data:
                                ckan.action.resource_update(
                                    id=res['id'],
                                    upload=FlaskFileStorage(file_data)
                                )
                        except Exception as e:
                            log.debug(e)

