import ckan.model as model
import ckan.plugins.toolkit as toolkit
import logging
import ckan.lib.helpers as h
import datetime

log = logging.getLogger(__name__)

def add_package_to_group(pkg_dict, context):
    group_id = pkg_dict.get('category', None)
    if group_id:
        group = model.Group.get(group_id)
        groups = context.get('package').get_groups('group')
        if group not in groups:
            group.add_package_by_name(pkg_dict.get('name'))


def set_data_owner(owner_org):
    data_owner = ''
    if owner_org:
        organization = model.Group.get(owner_org)
        if organization:
            parents = organization.get_parent_group_hierarchy('organization')
            if parents:
                data_owner = parents[0].title
            else:
                data_owner = organization.title
    return data_owner.strip()

def is_dataset_harvested(package_id):
    if not package_id:
        return None
    return any(package_revision for package_revision in toolkit.get_action('package_revision_list')(data_dict={'id': package_id}) 
        if 'REST API: Create object' in package_revision.get('message') and h.date_str_to_datetime(package_revision.get('timestamp')) > datetime.datetime(2019, 4, 24))
