# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
import contextlib
import json
from django.contrib import admin
from django.core.urlresolvers import reverse
from django.forms import Form, IntegerField
import pytest
from stagesetting.forms import CreateSettingForm, AdminFieldForm
from stagesetting.models import RuntimeSetting
from stagesetting.utils import registry


@pytest.yield_fixture
def modeladmin():
    yield admin.site._registry[RuntimeSetting]


@pytest.yield_fixture
def add_url():
    url = reverse('admin:stagesetting_runtimesetting_add')
    yield url


@pytest.yield_fixture
def changelist_url():
    url = reverse('admin:stagesetting_runtimesetting_changelist')
    yield url


@pytest.yield_fixture
def change_url():
    x = RuntimeSetting.objects.create(key='GLORP',
                                      raw_value=json.dumps({'count': '13'}))
    url = reverse('admin:stagesetting_runtimesetting_change', args=(x.pk,))
    yield url

@pytest.yield_fixture
def delete_url():
    x = RuntimeSetting.objects.create(key='GLORP',
                                      raw_value=json.dumps({'count': '13'}))
    url = reverse('admin:stagesetting_runtimesetting_delete', args=(x.pk,))
    yield url


@contextlib.contextmanager
def form(key):
    class ThisForm(Form):
        count = IntegerField(initial=25, min_value=1, max_value=99)
    registry.register(key, ThisForm, {'amdefault': None})
    try:
        yield ThisForm
    finally:
        registry.unregister(key)


def test_history_link(modeladmin):
    result = modeladmin.history_link(obj=RuntimeSetting(pk=1))
    expected = ('<a href="/test_admin/stagesetting/runtimesetting/1/history/" '
                'class="historylink">History</a>')
    assert result == expected


@pytest.mark.django_db
def test_add_view_GET(admin_client, add_url):
    """
    :type admin_client: django.test.client.Client
    :type response: django.template.response.TemplateResponse
    """
    response = admin_client.get(add_url)
    assert response.status_code == 200
    assert response.context_data != {}
    assert response.context_data['add'] is True
    assert response.context_data['change'] is False
    assert response.context_data['save_as'] is False
    assert response.context_data['show_save_and_continue'] is False
    assert isinstance(response.context_data['form'], CreateSettingForm)


@pytest.mark.django_db
def test_add_view_POST(admin_client, add_url):
    """
    :type admin_client: django.test.client.Client
    :type response: django.template.response.TemplateResponse
    """
    with form('ADD_POST'):
        response = admin_client.post(add_url, {
            'key': 'ADD_POST',
        })
    assert response.status_code == 302
    x = RuntimeSetting.objects.get()
    url = reverse('admin:stagesetting_runtimesetting_change', args=(x.pk,))
    assert response.url.endswith(url)


@pytest.mark.django_db
def test_change_view_GET(admin_client, change_url):
    with form('GLORP'):
        response = admin_client.get(change_url)
    assert response.status_code == 200
    assert response.context_data != {}
    assert response.context_data['add'] is False
    assert response.context_data['change'] is True
    assert response.context_data['save_as'] is False
    assert response.context_data['show_save_and_continue'] is False
    assert isinstance(response.context_data['original'], RuntimeSetting)
    assert isinstance(response.context_data['form'], AdminFieldForm)


@pytest.mark.django_db
def test_change_view_POST(admin_client, change_url, changelist_url):
    with form('GLORP'):
        response = admin_client.post(change_url, {'count': '24'})
    assert response.status_code == 302
    assert response.url.endswith(changelist_url) is True


@pytest.mark.django_db
def test_delete_view_GET(admin_client, delete_url):
    response = admin_client.get(delete_url)
    assert response.status_code == 200
    assert response.context_data != {}
    assert isinstance(response.context_data['original'], RuntimeSetting)
    assert isinstance(response.context_data['object'], RuntimeSetting)
    assert isinstance(response.context_data['runtimesetting'], RuntimeSetting)


@pytest.mark.django_db
def test_delete_view_DELETE(admin_client, delete_url, changelist_url):
    with form('GLORP'):
        response = admin_client.delete(delete_url)
    assert response.status_code == 302
    assert response.url.endswith(changelist_url)
