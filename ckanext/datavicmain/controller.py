import logging
from paste.deploy.converters import asbool
from ckan.common import config
import ckan.authz as authz
import ckan.lib.authenticator as authenticator
from ckan.controllers.user import set_repoze_user
from ckan.controllers.user import UserController
import ckan.lib.helpers as h
import ckan.lib.navl.dictization_functions as dictization_functions
from ckan.common import _, request
import ckan.lib.mailer as mailer
from ckan.common import c, response
from ckan.controllers.package import PackageController
# import ckan.lib.package_saver as package_saver
# from ckan.lib.base import BaseController
import ckan.lib.base as base
import ckan.lib as lib
import ckan.logic as logic
import ckan.model as model
import ckan.plugins.toolkit as toolkit
import json
import helpers

render = base.render
NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
get_action = logic.get_action

abort = base.abort
check_access = logic.check_access
ValidationError = logic.ValidationError
UsernamePasswordError = logic.UsernamePasswordError
DataError = dictization_functions.DataError
unflatten = dictization_functions.unflatten
log = logging.getLogger(__name__)


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
        # c.related_count = c.pkg.related_count
        self._setup_template_variables(context, {'id': id},
                                       package_type=package_type)

        # package_saver.PackageSaver().render_package(c.pkg_dict, context)

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
        except NotAuthorized as e:
            log.debug(str(e))
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
                # If you only want to automatically login new users, check that user_dict['state'] == 'pending'
                context['reset_password'] = True
                new_password = self._get_form_password()
                user_dict['password'] = new_password
                user_dict['reset_key'] = c.reset_key
                user_dict['state'] = model.State.ACTIVE
                user = get_action('user_update')(context, user_dict)
                mailer.create_reset_key(user_obj)

                h.flash_success(_("Your password has been reset."))

                if not c.user:
                    # log the user in programatically
                    set_repoze_user(user_dict['name'])
                    h.redirect_to(controller='user', action='me')

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

    def user_dashboard(self):
        # If user has access to create packages, show the dashboard_datasets, otherwise fall back to show dataset search page
        return self.dashboard_datasets() if h.check_access('package_create') else h.redirect_to(controller='package', action='search')

    def edit(self, id=None, data=None, errors=None, error_summary=None):
        # Copied from ckan.controllers.user.edit
        context = {'save': 'save' in request.params,
                   'schema': self._edit_form_to_db_schema(),
                   'model': model, 'session': model.Session,
                   'user': c.user, 'auth_user_obj': c.userobj
                   }
        if id is None:
            if c.userobj:
                id = c.userobj.id
            else:
                abort(400, _('No user specified'))
        data_dict = {'id': id}

        try:
            check_access('user_update', context, data_dict)
        except NotAuthorized:
            abort(403, _('Unauthorized to edit a user.'))

        if context['save'] and not data and request.method == 'POST':
            return self._save_edit(id, context)

        try:
            old_data = get_action('user_show')(context, data_dict)

            schema = self._db_to_edit_form_schema()
            if schema:
                old_data, errors = \
                    dictization_functions.validate(old_data, schema, context)

            c.display_name = old_data.get('display_name')
            c.user_name = old_data.get('name')

            data = data or old_data

        except NotAuthorized:
            abort(403, _('Unauthorized to edit user %s') % '')
        except NotFound:
            abort(404, _('User not found'))

        user_obj = context.get('user_obj')

        if not (authz.is_sysadmin(c.user)
                or c.user == user_obj.name):
            abort(403, _('User %s not authorized to edit %s') %
                  (str(c.user), id))

        errors = errors or {}
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}

        self._setup_template_variables({'model': model,
                                        'session': model.Session,
                                        'user': c.user},
                                       data_dict)

        c.is_myself = True
        c.show_email_notifications = asbool(
            config.get('ckan.activity_streams_email_notifications'))
        c.form = render(self.edit_user_form, extra_vars=vars)

        return render('user/edit.html')

    def _save_edit(self, id, context):
        # Copied from ckan.controllers.user._save_edit
        try:
            if id in (c.userobj.id, c.userobj.name):
                current_user = True
            else:
                current_user = False
            old_username = c.userobj.name

            data_dict = logic.clean_dict(unflatten(
                logic.tuplize_dict(logic.parse_params(request.params))))
            context['message'] = data_dict.get('log_message', '')
            data_dict['id'] = id

            email_changed = data_dict['email'] != c.userobj.email

            if (data_dict['password1'] and data_dict['password2']) \
                    or email_changed:
                identity = {'login': c.user,
                            'password': data_dict['old_password']}
                auth = authenticator.UsernamePasswordAuthenticator()

                if auth.authenticate(request.environ, identity) != c.user:
                    raise UsernamePasswordError

            # MOAN: Do I really have to do this here?
            if 'activity_streams_email_notifications' not in data_dict:
                data_dict['activity_streams_email_notifications'] = False

            user = get_action('user_update')(context, data_dict)
            h.flash_success(_('Profile updated'))

            if current_user and data_dict['name'] != old_username:
                # Changing currently logged in user's name.
                # Update repoze.who cookie to match
                set_repoze_user(data_dict['name'])
            # DataVic customisation
            # Redirect to different pages depending on user access
            if h.check_access('package_create'):
                h.redirect_to(controller='user', action='read', id=user['name'])
            else:
                h.redirect_to(controller='user', action='activity', id=user['name'])
        except NotAuthorized:
            abort(403, _('Unauthorized to edit user %s') % id)
        except NotFound, e:
            abort(404, _('User not found'))
        except DataError:
            abort(400, _(u'Integrity Error'))
        except ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.edit(id, data_dict, errors, error_summary)
        except UsernamePasswordError:
            errors = {'oldpassword': [_('Password entered was incorrect')]}
            error_summary = {_('Old Password'): _('incorrect password')}
            return self.edit(id, data_dict, errors, error_summary)

    def approve(self, id):
        try:
            data_dict = {'id': id}

            # Only sysadmins can activate a pending user
            toolkit.check_access('sysadmin', {})

            old_data = toolkit.get_action('user_show')({}, data_dict)
            old_data['state'] = model.State.ACTIVE
            user = toolkit.get_action('user_update')({}, old_data)

            # Send new account approved email to user
            helpers.send_email(
                [user.get('email', '')],
                'new_account_approved',
                {
                    "user_name": user.get('name', ''),
                    'login_url': toolkit.url_for('login', qualified=True),
                    "site_title": config.get('ckan.site_title'),
                    "site_url": config.get('ckan.site_url')
                }
            )

            h.flash_success(_('User approved'))

            return h.redirect_to(controller='user', action='read', id=user['name'])
        except NotAuthorized:
            abort(403, _('Unauthorized to activate user.'))
        except NotFound, e:
            abort(404, _('User not found'))
        except DataError:
            abort(400, _(u'Integrity Error'))
        except ValidationError, e:
            h.flash_error(u'%r' % e.error_dict)

    def deny(self, id):
        try:
            data_dict = {'id': id}

            # Only sysadmins can activate a pending user
            toolkit.check_access('sysadmin', {})

            user = toolkit.get_action('user_show')({}, data_dict)
            # Delete denied user
            toolkit.get_action('user_delete')({}, data_dict)

            # Send account requested denied email
            helpers.send_email(
                [user.get('email', '')],
                'new_account_denied',
                {
                    "user_name": user.get('name', ''),
                    "site_title": config.get('ckan.site_title'),
                    "site_url": config.get('ckan.site_url')
                }
            )

            h.flash_success(_('User Denied'))

            return h.redirect_to(controller='user', action='read', id=user['name'])
        except NotAuthorized:
            abort(403, _('Unauthorized to reject user.'))
        except NotFound, e:
            abort(404, _('User not found'))
        except DataError:
            abort(400, _(u'Integrity Error'))
        except ValidationError, e:
            h.flash_error(u'%r' % e.error_dict)
