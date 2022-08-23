import ckan.plugins.toolkit as tk
import ckan.model as model


def update_syndication_flag(pkg_dict, is_ready_for_syndication):
    if is_ready_for_syndication and not tk.asbool(pkg_dict.get('syndicate', False)):
        pkg = model.Package.get(pkg_dict['id'])
        pkg.extras['syndicate'] = "true"
        tk.h.flash_success("Dataset '{0}' is being syndicated to ODP.".format(pkg_dict['title']))