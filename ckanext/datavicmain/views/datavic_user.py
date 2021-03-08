import logging
import json
from operator import itemgetter
import six

from flask import Blueprint
from flask.views import MethodView

import ckan.lib.helpers as h
import ckan.lib.mailer as mailer
import ckan.plugins.toolkit as toolkit
import ckan.logic as logic
import ckan.model as model
from ckan.common import _, g, config, request
import ckan.lib.authenticator as authenticator


import ckan.views.user as user

from ckanext.datavicmain.plugins import datavic_user_reset

import ckanext.datavicmain.helpers as helpers
import ckan.lib.navl.dictization_functions as dictization_functions



NotFound = toolkit.ObjectNotFound
NotAuthorized = toolkit.NotAuthorized
ValidationError = toolkit.ValidationError
DataError = dictization_functions.DataError

check_access = toolkit.check_access
get_action = toolkit.get_action
asbool = toolkit.asbool

tuplize_dict = logic.tuplize_dict
parse_params = logic.parse_params
clean_dict = logic.clean_dict

_edit_form_to_db_schema = user._edit_form_to_db_schema
_extra_template_variables = user._extra_template_variables
edit_user_form = user.edit_user_form
set_repoze_user = user.set_repoze_user

render = toolkit.render
abort = toolkit.abort

log = logging.getLogger(__name__)

datavicuser = Blueprint('datavicuser', __name__)


class DataVicRequestResetView(user.RequestResetView):

    def _prepare(self, id):
        return super()._prepare(id)

    def get(self):
        self._prepare()
        return render(u'user/request_reset.html', {})

    def post(self):
        '''
        POST method datavic user
        '''
        id = request.params.get('user')
        if id in (None, u''):
            h.flash_error(_(u'Email is required'))
            return h.redirect_to(u'/user/reset')
        context = {'model': model,
                    'user': g.user,
                    u'ignore_auth': True}
        user_objs = []

        if u'@' not in id:
            try:
                user_dict = get_action('user_show')(context, {'id': id})
                user_objs.append(context['user_obj'])
            except NotFound:
                pass
        else:
            user_list = get_action(u'user_list')(context, {u'email': id})
            if user_list:
                # send reset emails for *all* user accounts with this email
                # (otherwise we'd have to silently fail - we can't tell the
                # user, as that would reveal the existence of accounts with
                # this email address)
                for user_dict in user_list:
                    get_action(u'user_show')(
                        context, {u'id': user_dict[u'id']})
                    user_objs.append(context[u'user_obj'])

        if not user_objs:
            log.info(u'User requested reset link for unknown user: {}'
                        .format(id))

        for user_obj in user_objs:
            log.info(u'Emailing reset link to user: {}'
                        .format(user_obj.name))
            try:
                # DATAVIC-221: Do not create/send reset link if user was self-registered and currently pending
                if user_obj.is_pending() and not user_obj.reset_key:
                    h.flash_error(_(u'Unable to send reset link - please contact the site administrator.'))
                    return h.redirect_to(u'/user/reset')
                else:
                    mailer.send_reset_link(user_obj)
            except mailer.MailerException as e:
                h.flash_error(
                    _(u'Error sending the email. Try again later '
                        'or contact an administrator for help')
                )
                log.exception(e)
                return h.redirect_to(u'/')
        # always tell the user it succeeded, because otherwise we reveal
        # which accounts exist or not
        h.flash_success(
            _(u'A reset link has been emailed to you '
                '(unless the account specified does not exist)'))
        return h.redirect_to(u'/')


class DataVicPerformResetView(user.PerformResetView):

    def _prepare(self, id):
        return super()._prepare(id)

    def get(self, id):
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
        except NotFound as e:
            abort(404, _('User not found'))

        g.reset_key = request.params.get('key')
        if not mailer.verify_reset_link(user_obj, g.reset_key):
            h.flash_error(_('Invalid reset key. Please try again.'))
            abort(403)
        return render('user/perform_reset.html')

    def post(self, id):
        context, user_dict = self._prepare(id)
        try:
            # If you only want to automatically login new users, check that user_dict['state'] == 'pending'
            context['reset_password'] = True
            new_password = super()._get_form_password()
            user_dict['password'] = new_password
            user_dict['reset_key'] = g.reset_key
            user_dict['state'] = model.State.ACTIVE
            user = get_action('user_update')(context, user_dict)
            user_obj = context['user_obj']
            mailer.create_reset_key(user_obj)

            h.flash_success(_("Your password has been reset."))

            if not g.user:
                # log the user in programatically
                set_repoze_user(user_dict['name'])
                h.redirect_to('user.me')

            # DataVic customisation
            # Redirect to different pages depending on user access
            if h.check_access('package_create'):
                h.redirect_to('user.read', id=user['name'])
            else:
                h.redirect_to('user.activity', id=user['name'])
        except NotAuthorized:
            h.flash_error(_('Unauthorized to edit user %s') % id)
        except NotFound as e:
            h.flash_error(_('User not found'))
        except DataError as e:
            h.flash_error(_(u'Integrity Error'))
        except ValidationError as  e:
            h.flash_error(u'%r' % e.error_dict)
        except ValueError as ve:
            h.flash_error(six.text_type(ve))


class DataVicUserEditView(user.EditView):

    def _prepare(self, id):
       return super(DataVicUserEditView, self)._prepare(id)

    # def get(self,  id=None, data=None, errors=None, error_summary=None):
    #     return super(DataVicUserEditView, self).get(id, data, errors, error_summary)

    def post(self, id=None):
        context, id = self._prepare(id)
        if not context[u'save']:
            return self.get(id)

        if id in (g.userobj.id, g.userobj.name):
            current_user = True
        else:
            current_user = False
        old_username = g.userobj.name

        try:
            data_dict = clean_dict(
                dictization_functions.unflatten(
                    tuplize_dict(parse_params(request.form))))
            data_dict.update(clean_dict(
                dictization_functions.unflatten(
                    tuplize_dict(parse_params(request.files))))
            )

        except dictization_functions.DataError:
            abort(400, _(u'Integrity Error'))
        data_dict.setdefault(u'activity_streams_email_notifications', False)

        context[u'message'] = data_dict.get(u'log_message', u'')
        data_dict[u'id'] = id
        email_changed = data_dict[u'email'] != g.userobj.email

        if (data_dict[u'password1']
                and data_dict[u'password2']) or email_changed:
            identity = {
                u'login': g.user,
                u'password': data_dict[u'old_password']
            }
            auth = authenticator.UsernamePasswordAuthenticator()

            if auth.authenticate(request.environ, identity) != g.user:
                errors = {
                    u'oldpassword': [_(u'Password entered was incorrect')]
                }
                error_summary = {_(u'Old Password'): _(u'incorrect password')}
                return self.get(id, data_dict, errors, error_summary)

        try:
            user = get_action(u'user_update')(context, data_dict)
        except NotAuthorized:
            abort(403, _(u'Unauthorized to edit user %s') % id)
        except NotFound:
            abort(404, _(u'User not found'))
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(id, data_dict, errors, error_summary)

        h.flash_success(_(u'Profile updated'))
        resp = h.redirect_to(u'user.read', id=user[u'name'])
        if current_user and data_dict[u'name'] != old_username:
            # Changing currently logged in user's name.
            # Update repoze.who cookie to match
            set_repoze_user(data_dict[u'name'], resp)
        return resp

    def get(self, id=None, data=None, errors=None, error_summary=None):
        context, id = self._prepare(id)
        data_dict = {u'id': id}
        try:
            old_data = logic.get_action(u'user_show')(context, data_dict)

            g.display_name = old_data.get(u'display_name')
            g.user_name = old_data.get(u'name')

            data = data or old_data

        except logic.NotAuthorized:
            abort(403, _(u'Unauthorized to edit user %s') % u'')
        except logic.NotFound:
            abort(404, _(u'User not found'))
        user_obj = context.get(u'user_obj')

        errors = errors or {}
        vars = {
            u'data': data,
            u'errors': errors,
            u'error_summary': error_summary
        }

        extra_vars = _extra_template_variables({
            u'model': model,
            u'session': model.Session,
            u'user': g.user
        }, data_dict)

        extra_vars[u'show_email_notifications'] = asbool(
            config.get(u'ckan.activity_streams_email_notifications'))
        vars.update(extra_vars)
        extra_vars[u'form'] = render(edit_user_form, extra_vars=vars)

        return render(u'user/edit.html', extra_vars)


def user_dashboard():
    # If user has access to create packages, show the dashboard_datasets, otherwise fall back to show dataset search page
    return h.redirect_to('dataset.index') if h.check_access('package_create') else h.redirect_to('dataset.search')   

def approve(id):
    try:
        data_dict = {'id': id}

        # Only sysadmins can activate a pending user
        check_access('sysadmin', {})

        old_data = get_action('user_show')({}, data_dict)
        old_data['state'] = model.State.ACTIVE
        user = get_action('user_update')({}, old_data)

        # Send new account approved email to user
        helpers.send_email(
            [user.get('email', '')],
            'new_account_approved',
            {
                "user_name": user.get('name', ''),
                'login_url': toolkit.url_for('user.login', qualified=True),
                "site_title": config.get('ckan.site_title'),
                "site_url": config.get('ckan.site_url')
            }
        )

        h.flash_success(_('User approved'))

        return h.redirect_to('user.read', id=user['name'])
    except NotAuthorized:
        abort(403, _('Unauthorized to activate user.'))
    except NotFound as e:
        abort(404, _('User not found'))
    except DataError:
        abort(400, _(u'Integrity Error'))
    except ValidationError as e:
        h.flash_error(u'%r' % e.error_dict)

def deny(id):
    try:
        data_dict = {'id': id}

        # Only sysadmins can activate a pending user
        check_access('sysadmin', {})

        user = get_action('user_show')({}, data_dict)
        # Delete denied user
        get_action('user_delete')({}, data_dict)

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

        return h.redirect_to('user.read', id=user['name'])
    except NotAuthorized:
        abort(403, _('Unauthorized to reject user.'))
    except NotFound as e:
        abort(404, _('User not found'))
    except DataError:
        abort(400, _(u'Integrity Error'))
    except ValidationError as e:
        h.flash_error(u'%r' % e.error_dict)


_edit_view = DataVicUserEditView.as_view(str('edit'))

def register_datavicuser_plugin_rules(blueprint):
    blueprint.add_url_rule(u'/user/reset', view_func=DataVicRequestResetView.as_view(str('request_reset')))
    blueprint.add_url_rule(u'/reset', view_func= DataVicPerformResetView.as_view(str('perform_reset')))
    blueprint.add_url_rule(u'/edit', view_func=_edit_view)
    blueprint.add_url_rule(u'/edit/<id>', view_func=_edit_view)
    blueprint.add_url_rule(u'/user/activate/<id>', view_func=approve)
    blueprint.add_url_rule(u'/user/deny/<id>', view_func=deny)

register_datavicuser_plugin_rules(datavicuser)
