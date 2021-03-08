from builtins import str
from builtins import range
import time
import six

from collections import OrderedDict
from six.moves.urllib.parse import urlparse, parse_qs, urlencode, urlunparse

import ckan.logic as logic
from ckan.plugins.toolkit import url_for, NotAuthorized, ObjectNotFound

import ckan.tests.factories as factories
import ckan.tests.helpers as helpers

import pytest

from ckan import plugins as p


@pytest.mark.ckan_config('ckan.plugins','datavicmain_dataset')
@pytest.mark.usefixtures('clean_db', 'with_plugins', 'with_request_context')
class TestEndpoints(object):

    def test_user_aprove(self, app):

        admin_pass = "RandomPassword123"
        sysadmin = factories.Sysadmin(password=admin_pass)

        user = factories.User()
        #
        url = url_for('datavicuser.approve', id= user['id'])
        env = {"REMOTE_USER": six.ensure_str(sysadmin["name"])}

        response = app.get(url=url, extra_environ=env)

        assert 200 == response.status_code
        assert b'User approved' in response.data

    def test_user_deny(self, app):

        admin_pass = "RandomPassword123"
        sysadmin = factories.Sysadmin(password=admin_pass)

        user = factories.User()
        #
        url = url_for('datavicuser.deny', id= user['id'])
        env = {"REMOTE_USER": six.ensure_str(sysadmin["name"])}

        response = app.get(url=url, extra_environ=env)

        assert 200 == response.status_code
        assert b'User Denied' in response.data