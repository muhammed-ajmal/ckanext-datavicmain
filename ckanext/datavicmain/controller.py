from ckan.common import c, response
from ckan.controllers.package import PackageController
#import ckan.lib.package_saver as package_saver
#from ckan.lib.base import BaseController
import ckan.lib.base as base
import ckan.lib as lib
import ckan.logic as logic
import ckan.model as model
import ckan.plugins.toolkit as toolkit
import json

render = base.render
NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
get_action = logic.get_action

abort = base.abort
check_access = logic.check_access
import ckan.lib.mailer as mailer
from ckan.common import _, request
import ckan.lib.navl.dictization_functions as dictization_functions
ValidationError = logic.ValidationError
DataError = dictization_functions.DataError
import ckan.lib.helpers as h
from ckan.controllers.user import UserController
from ckan.controllers.user import set_repoze_user


class DataVicMainController(PackageController):

    def historical(self, id):
        response.headers['Content-Type'] = "text/html; charset=utf-8"
        package_type = self._get_package_type(id.split('@')[0])

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True,
                   'auth_user_obj': c.userobj}
        data_dict = {'id': id}
        # check if package exists
        try:
            c.pkg_dict = get_action('package_show')(context, data_dict)
            c.pkg = context['package']
        except NotFound:
            abort(404, _('Dataset not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read package %s') % id)

        # used by disqus plugin
        c.current_package_id = c.pkg.id
        #c.related_count = c.pkg.related_count
        self._setup_template_variables(context, {'id': id},
                                       package_type=package_type)

        #package_saver.PackageSaver().render_package(c.pkg_dict, context)

        try:
            return render('package/read_historical.html')
        except lib.render.TemplateNotFound:
            msg = _("Viewing {package_type} datasets in {format} format is "
                    "not supported (template file {file} not found).".format(
                package_type=package_type, format=format, file='package/read_historical.html'))
            abort(404, msg)

        assert False, "We should never get here"

    def check_sysadmin(self):
        import ckan.authz as authz

        # Only sysadmin users can generate reports
        user = toolkit.c.userobj

        if not user or not authz.is_sysadmin(user.name):
            base.abort(403, _('You are not permitted to perform this action.'))


    def create_core_groups(self):
        self.check_sysadmin()

        context = {'user': toolkit.c.user, 'model': model, 'session': model.Session, 'ignore_auth': True, 'return_id_only': True}

        output = '<pre>'

        groups_to_fetch = [
            'business',
            'communication',
            'community',
            'education',
            'employment',
            'environment',
            'general',
            'finance',
            'health',
            'planning',
            'recreation',
            'science-technology',
            'society',
            'spatial-data',
            'transport'
        ]

        from ckanapi import RemoteCKAN
        ua = 'ckanapiexample/1.0 (+http://example.com/my/website)'
        demo = RemoteCKAN('https://www.data.vic.gov.au/data', user_agent=ua)
        for group in groups_to_fetch:
            group_dict = demo.action.group_show(
                id=group,
                include_datasets=False,
                include_groups=False,
                include_dataset_count=False,
                include_users=False,
                include_tags=False,
                include_extras=False,
                include_followers=False
            )

            output += "\nRemote CKAN group:\n"
            output += json.dumps(group_dict)

            # Check for existence of a local group with the same name
            try:
                local_group_dict = toolkit.get_action('group_show')(context, {'id': group_dict['name']})
                output += "\nA local group called %s DOES exist" % group_dict['name']
            except NotFound:
                output += "\nA local group called %s does not exist" % group_dict['name']
                toolkit.check_access('group_create', context)
                local_group_dict = toolkit.get_action('group_create')(context, group_dict)
                output += "\nCreated group:\n"
                output += json.dumps(local_group_dict)

            output += "\n==============================\n"

        return output


class DataVicUserController(UserController):
    def perform_reset(self, id):
        # FIXME 403 error for invalid key is a non helpful page
        context = {'model': model, 'session': model.Session,
                   'user': id,
                   'keep_email': True}

        try:
            check_access('user_reset', context)
        except NotAuthorized:
            abort(403, _('Unauthorized to reset password.'))

        try:
            data_dict = {'id': id}
            user_dict = get_action('user_show')(context, data_dict)

            user_obj = context['user_obj']
        except NotFound, e:
            abort(404, _('User not found'))

        c.reset_key = request.params.get('key')
        if not mailer.verify_reset_link(user_obj, c.reset_key):
            h.flash_error(_('Invalid reset key. Please try again.'))
            abort(403)

        if request.method == 'POST':
            try:
                is_new_user = user_dict['state'] == 'pending'
                context['reset_password'] = True
                new_password = self._get_form_password()
                user_dict['password'] = new_password
                user_dict['reset_key'] = c.reset_key
                user_dict['state'] = model.State.ACTIVE
                user = get_action('user_update')(context, user_dict)
                mailer.create_reset_key(user_obj)

                if is_new_user and not c.user:
                    # log the user in programatically
                    set_repoze_user(user_dict['name'])
                    h.redirect_to(controller='user', action='me')

                h.flash_success(_("Your password has been reset."))
                h.redirect_to('/')
            except NotAuthorized:
                h.flash_error(_('Unauthorized to edit user %s') % id)
            except NotFound, e:
                h.flash_error(_('User not found'))
            except DataError:
                h.flash_error(_(u'Integrity Error'))
            except ValidationError, e:
                h.flash_error(u'%r' % e.error_dict)
            except ValueError, ve:
                h.flash_error(unicode(ve))

        c.user_dict = user_dict
        return render('user/perform_reset.html')
