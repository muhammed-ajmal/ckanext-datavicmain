# import logging

# from ckan.controllers.package import PackageController
# import ckan.plugins.toolkit as toolkit

# log = logging.getLogger(__name__)


# class PurgeController(PackageController):

#     def purge(self, id):
#         try:
#             # Only sysadmins can purge
#             toolkit.check_access('sysadmin', {})
#             toolkit.get_action('dataset_purge')({}, {'id': id})
#             toolkit.h.flash_success('Successfully purged dataset ID: %s' % id)
#         except Exception as e:
#             print(str(e))
#             toolkit.h.flash_error('Exception')

#         return toolkit.h.redirect_to('/ckan-admin/trash')
