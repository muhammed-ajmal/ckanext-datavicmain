import ckan.plugins.toolkit as toolkit
import logging
import ckan.lib.navl.dictization_functions as df

from ckanext.datavicmain import helpers

log = logging.getLogger(__name__)
unflatten = df.unflatten


def datavic_tag_string(key, data, errors, context):

    request = toolkit.request if repr(toolkit.request) != '<LocalProxy unbound>' and hasattr(toolkit.request, 'params') else None

    if request:
        end_point = toolkit.get_endpoint()
        if end_point and end_point[0] == 'dataset' and end_point[1] in ['new', 'edit']:
            toolkit.get_validator('not_empty')(key, data, errors, context)
            return

    toolkit.get_validator('ignore_missing')(key, data, errors, context)


def datavic_category_add_package_to_group(key, data, errors, context):
    data_dict = unflatten(data)
    helpers.add_package_to_group(data_dict, context)
    # DATAVIC-251 - Create activity for private datasets
    activity_type = str('new') if data_dict.get('id') else str('changed')
    helpers.set_private_activity(data_dict, context, activity_type)
