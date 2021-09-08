import ckan.plugins.toolkit as toolkit

from ckan.lib.navl.dictization_functions import unflatten
from ckan.logic import clean_dict, tuplize_dict, parse_params


def get_frequency_options():
    return [
        {'value': 'ten_minutes', 'text': '10 minutes'},
        {'value': 'two_hours',  'text': '2 hours'},
        {'value': 'daily', 'text': 'Daily'}]


def clean_params(params):
    return clean_dict(unflatten(tuplize_dict(parse_params(params))))


def get_datastore_refresh_configs():
    user = toolkit.g.user
    context = {'user': user}
    return toolkit.get_action('refresh_dataset_datastore_list')(context, {})


def get_datasore_refresh_config_option(frequency):
    options = get_frequency_options()
    return [option['text'] for option in options if option['value'] == frequency]
