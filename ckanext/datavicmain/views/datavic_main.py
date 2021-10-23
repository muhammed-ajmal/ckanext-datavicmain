import logging
import ckan.views.dataset as dataset
import ckan.model as model
import ckan.plugins.toolkit as toolkit

from flask import Blueprint

NotFound = toolkit.ObjectNotFound
NotAuthorized = toolkit.NotAuthorized
check_access = toolkit.check_access
get_action = toolkit.get_action
_ = toolkit._
g = toolkit.g
render = toolkit.render
abort = toolkit.abort
log = logging.getLogger(__name__)
datavicmain = Blueprint('datavicmain', __name__)


def historical(id):
    package_type = dataset._get_package_type(id.split('@')[0])  # check for new function if necessary

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

    extra_vars = {'pkg_dict': pkg_dict, 'pkg': pkg}

    try:
        return render('package/read_historical.html', extra_vars)
    # TemplateNotFound is not added to toolkit
    except NotFound as e:
        msg = _("Viewing {package_type} datasets in {format} format is "
                "not supported (template file {file} not found).".format(
                    package_type=package_type, format=format, file='package/read_historical.html'))
        abort(404, msg)

    assert False, "We should never get here"


def purge(id):
    try:
        # Only sysadmins can purge
        toolkit.check_access('sysadmin', {})
        toolkit.get_action('dataset_purge')({}, {'id': id})
        toolkit.h.flash_success('Successfully purged dataset ID: %s' % id)
    except Exception as e:
        print(str(e))
        toolkit.h.flash_error('Exception')

    return toolkit.h.redirect_to('/ckan-admin/trash')


def register_datavicmain_plugin_rules(blueprint):
    blueprint.add_url_rule('/dataset/<id>/historical', view_func=historical)
    blueprint.add_url_rule('/dataset/purge/<id>', view_func=purge)


register_datavicmain_plugin_rules(datavicmain)
