import os
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
    log.debug("Synchronizing uploaded files of %s", package_id)
    profile = kwargs["profile"]
    remote = kwargs["remote"]

    if "id" not in remote:
        log.debug("Cannot detect remote ID. Skip")
        return

    ckan = get_target(profile.ckan_url, profile.api_key)
    resources = remote.get('resources')

    pkg = model.Package.get(package_id)
    original_resources = pkg.resources

    for res in resources:
        log.debug("Checking resource %s", res["id"])
        if profile.ckan_url not in res.get('url', ''):
            log.debug("External resource. Skip")
            continue

        check_res = requests.head(res['url'])

        # TODO: consider checking modification date/size because content can be
        # different even if file exists
        if check_res.ok:
            log.debug("File already exists on remote portal. Skip")
            continue

        org_res = [r for r in original_resources if r.id == res['id']]
        if not org_res:
            log.debug(
                "Cannot locate resource with ID %s locally. Skip",
                res["id"]
            )
            continue

        log.debug(
            "File does not exist for %s resource, copying it.",
            res['id']
        )

        uploader = get_resource_uploader(org_res[0].as_dict())
        file_path = uploader.get_path(org_res[0].id)
        try:
            with open(file_path, 'rb') as file_data:
                ckan.action.resource_update(
                    id=res['id'],
                    upload=FlaskFileStorage(file_data, os.path.basename(org_res[0].url)),
                    url=org_res[0].url
                )
        except Exception:
            log.exception(
                "Cannot upload file from local resource %s to the remote %s",
                org_res[0].id,
                res["id"]
            )
