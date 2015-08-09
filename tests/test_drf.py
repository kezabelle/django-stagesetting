# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from collections import OrderedDict
import contextlib
import json
from django.core.urlresolvers import reverse
from django.forms import Form, IntegerField
import pytest
from pytest_django.lazy_django import skip_if_no_django
from stagesetting.models import RuntimeSetting
from stagesetting.utils import registry


@contextlib.contextmanager
def form(key):
    class ListPerPageForm(Form):
        count = IntegerField(initial=25, min_value=1, max_value=99)
    registry.register(key, ListPerPageForm, {'amdefault': None})
    try:
        yield ListPerPageForm
    finally:
        registry.unregister(key)


@pytest.fixture()
def api_client():
    """A Django test client instance."""
    skip_if_no_django()
    from rest_framework.test import APIClient
    return APIClient()


@pytest.mark.django_db
def test_api_getlist(api_client):
    test_value = {'testing': 1, 'count': 2}
    setting = RuntimeSetting(key="TEST")
    with form('TEST'):
        setting.value = test_value
    setting.save()
    url = reverse('runtimesetting-list')
    with form('TEST'):
        response = api_client.get(url)
    assert response.data == [
        OrderedDict(
            [('key', 'TEST'), 
             ('value', {'count': 2})]
        )
    ]



@pytest.mark.django_db
def test_api_get_single(api_client):
    test_value = {'testing': 1, 'count': 4}
    setting = RuntimeSetting(key="TEST2")
    with form('TEST2'):
        setting.value = test_value
    setting.save()
    url = reverse('runtimesetting-detail', args=(setting.pk,))
    with form('TEST2'):
        response = api_client.get(url)
    assert response.data == {
        'value': {'count': 4},
        'key': 'TEST2'
    }


@pytest.mark.django_db
def test_api_post_does_create(api_client):
    test_value = {
        'key': 'TEST3',
        'value': {'testing': 1, 'count': 4},
    }
    url = reverse('runtimesetting-list')
    with form('TEST3'):
        response = api_client.post(url, data=test_value, format='json')
    assert response.data == {
        'value': {'count': 4},
        'key': 'TEST3'
    }
    obj = RuntimeSetting.objects.get(key='TEST3')
    with form('TEST3'):
        assert obj.value == {'count': 4}


@pytest.mark.django_db
def test_api_put_does_update(api_client):
    initial_value = {
        'key': 'TEST4',
        'value': {'testing': 1, 'count': 1},
    }
    setting = RuntimeSetting(key="TEST4")
    with form('TEST4'):
        setting.value = initial_value
    setting.save()
    test_value = {
        'key': 'TEST4',
        'value': {'testing': 1, 'count': 25},
    }
    url = reverse('runtimesetting-detail', args=(setting.pk,))
    with form('TEST4'):
        response = api_client.put(url, data=test_value, format='json')
    assert response.data == {
        'value': {'count': 25},
        'key': 'TEST4'
    }
    obj = RuntimeSetting.objects.get(key='TEST4')
    with form('TEST4'):
        assert obj.value == {'count': 25}


@pytest.mark.django_db
def test_api_patch_does_update(api_client):
    initial_value = {
        'key': 'TEST5',
        'value': {'testing': 1, 'count': 1},
    }
    setting = RuntimeSetting(key="TEST5")
    with form('TEST5'):
        setting.value = initial_value
    setting.save()
    test_value = {
        'key': 'TEST5',
        'value': {'testing': 1, 'count': 25},
    }
    url = reverse('runtimesetting-detail', args=(setting.pk,))
    with form('TEST5'):
        response = api_client.patch(url, data=test_value, format='json')
    assert response.data == {
        'value': {'count': 25},
        'key': 'TEST5'
    }
    obj = RuntimeSetting.objects.get(key='TEST5')
    with form('TEST5'):
        assert obj.value == {'count': 25}
