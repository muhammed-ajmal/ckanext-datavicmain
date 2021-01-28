import logging
import json
from operator import itemgetter
import six

from flask import Blueprint
from flask.views import MethodView

import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.mailer as mailer
import ckan.lib.navl.dictization_functions as dictization_functions

import ckan.logic as logic
import ckan.model as model
from ckan.common import _, config, g, request
from ckan.lib.navl import dictization_functions
import ckan.plugins.toolkit as tk

from ckan.views.user import RequestResetView, PerformResetView

from ckanext.datavicmain.plugins import datavic_user_reset




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
DataError = dictization_functions.DataError
unflatten = dictization_functions.unflatten

render = base.render
abort = base.abort

log = logging.getLogger(__name__)

datavicuser = Blueprint('datavicuser', __name__)


class DataVicRequestResetView(RequestResetView):

    def get(self):
        self._prepare()
        return base.render(u'user/request_reset.html', {})

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
            user_list = logic.get_action(u'user_list')(context, {
                u'email': id
            })
            if user_list:
                # send reset emails for *all* user accounts with this email
                # (otherwise we'd have to silently fail - we can't tell the
                # user, as that would reveal the existence of accounts with
                # this email address)
                for user_dict in user_list:
                    logic.get_action(u'user_show')(
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


class DataVicPerformResetView(PerformResetView):

    def get(self):
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

    def post(self):
        try:
            # If you only want to automatically login new users, check that user_dict['state'] == 'pending'
            context['reset_password'] = True
            new_password = super()._get_form_password()
            user_dict['password'] = new_password
            user_dict['reset_key'] = g.reset_key
            user_dict['state'] = model.State.ACTIVE
            user = get_action('user_update')(context, user_dict)
            mailer.create_reset_key(user_obj)

            h.flash_success(_("Your password has been reset."))

            if not g.user:
                # log the user in programatically
                set_repoze_user(user_dict['name'])
                h.redirect_to(controller='user', action='me')

            h.redirect_to('/')
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




def user_dashboard():
    # If user has access to create packages, show the dashboard_datasets, otherwise fall back to show dataset search page
    return h.redirect_to('dataset.index') if h.check_access('package_create') else h.redirect_to('dataset.search')    

def register_datavicuser_plugin_rules(blueprint):
    blueprint.add_url_rule('/user/reset', view_func=DataVicRequestResetView.as_view(str('request_reset')))
    blueprint.add_url_rule(u'/reset', view_func= DataVicPerformResetView.as_view(str(u'perform_reset')))

register_datavicuser_plugin_rules(datavicuser)