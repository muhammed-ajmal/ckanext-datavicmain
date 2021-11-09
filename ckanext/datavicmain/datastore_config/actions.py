import ckan.plugins.toolkit as toolkit
import logging

from ckan.lib.dictization import table_dictize

from sqlalchemy.exc import IntegrityError
from ckanext.datavicmain.datastore_config.model import RefreshDatasetDatastore

_check_access = toolkit.check_access
log = logging.getLogger(__name__)
ValidationError = toolkit.ValidationError



def refresh_datastore_dataset_create(context, data_dict):
    if not data_dict:
        raise ValidationError()

    session = context['session']
    user = context['auth_user_obj']

    rdd = RefreshDatasetDatastore()

    rdd.dataset_id = data_dict.get('dataset_id')
    rdd.frequency = data_dict.get('frequency')
    rdd.created_user_id = user.id

    try:
        rdd.save()
    except IntegrityError:
        raise ValidationError('Dataset already set for execution')
    finally:
        session.rollback()

    session.add(rdd)
    session.commit()

    return table_dictize(rdd, context)


def refresh_dataset_datastore_list(context, data_dict=None):

    results = RefreshDatasetDatastore.get_all()
    
    res_dict = []
    for res in results:
        pkg = res._asdict()
        res_dict.append(pkg)

    return res_dict

def refresh_dataset_datastore_by_frequency(context, data_dict):

    results = RefreshDatasetDatastore.get_by_frequency(data_dict.get('frequency'))

    if not results:
        return []

    res_dict = []
    for res in results:
        pkg = res._asdict()
        res_dict.append(pkg)

    return res_dict



def refresh_dataset_datastore_delete(context, data_dict):

    rdd_id = data_dict['id']

    rdd = RefreshDatasetDatastore.get(rdd_id)

    if rdd:
        RefreshDatasetDatastore.delete(rdd_id)
    else:
        raise ValidationError("Not found")
