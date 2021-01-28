import logging
import json
from operator import itemgetter

from flask import Blueprint
from flask.views import MethodView

import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.logic as logic
import ckan.model as model
from ckan.common import _,  g

import ckan.views.dataset as dataset


NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
#TemplateNotFound = logic.TemplateNotFound
check_access = logic.check_access
get_action = logic.get_action
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
parse_params = logic.parse_params
flatten_to_string_key = logic.flatten_to_string_key

render = base.render
abort = base.abort

log = logging.getLogger(__name__)

datavicmain = Blueprint('datavicmain', __name__)


#TODO: Will require some rework to send the pkg_dict to templates
def historical(id):
    package_type = dataset._get_package_type(id.split('@')[0]) #check for new function if necessary

    context = {'model': model, 'session': model.Session,
                'user': g.user or g.author, 'for_view': True,
                'auth_user_obj': g.userobj}
    
    data_dict = {'id': id}
    # check if package exists
    try:
        pkg_dict = get_action('package_show')(context, data_dict)
        pkg = context['package']
    except NotFound:
        abort(404, _('Dataset not found'))
    except NotAuthorized:
        abort(401, _('Unauthorized to read package %s') % id)

    # used by disqus plugin
    g.current_package_id = pkg.id
    dataset._setup_template_variables(context, data_dict,
                                      package_type=package_type)

    # TODO: remove
    g.pkg_dict = pkg_dict
    g.pkg = pkg


    try:
        return render('package/read_historical.html')
    except base.TemplateNotFound:
        msg = _("Viewing {package_type} datasets in {format} format is "
                "not supported (template file {file} not found).".format(
                    package_type=package_type, format=format, file='package/read_historical.html'))
        abort(404, msg)

    assert False, "We should never get here"


def register_datavicmain_plugin_rules(blueprint):
    blueprint.add_url_rule('/dataset/<id>/historical', view_func=historical)

register_datavicmain_plugin_rules(datavicmain)