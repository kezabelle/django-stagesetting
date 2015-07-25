# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
import contextlib
import json
from django.forms import IntegerField, Form
import pytest
from stagesetting.models import RuntimeSetting
from stagesetting.utils import registry


@contextlib.contextmanager
def form(key):
    class ListPerPageForm(Form):
        count = IntegerField(initial=25, min_value=1, max_value=99)
    registry.register(key, ListPerPageForm, {'amdefault': None})
    yield ListPerPageForm
    registry.unregister(key)



def test_get_form_class():
    with form('TEST') as form_class:
        value = RuntimeSetting(key="TEST")
        assert value.get_form_class() == form_class
    with pytest.raises(KeyError):
        value.get_form_class()



def test_get_form():
    test_value = {'testing': 1, 'count': 2}
    with form('TEST') as form_class:
        value = RuntimeSetting(key="TEST", raw_value=json.dumps(test_value))
        form_instance = value.get_form()
        assert isinstance(form_instance, form_class)
        assert form_instance.is_bound is True
        assert form_instance.data == test_value


def test_value_deserializes_raw():
    test_value = {'testing': 1, 'count': 2}
    with form('TEST'):
        value = RuntimeSetting(key="TEST", raw_value=json.dumps(test_value))
        form_result = value.value
        assert 'count' in form_result
        assert form_result['count'] == 2
        # we dropped unknown data
        assert len(form_result) == 1


def test_default_value():
    test_value = {'testing': 1, 'count': 2}
    with form('TEST'):
        value = RuntimeSetting(key="TEST", raw_value=json.dumps(test_value))
        defalft_value = value.default_value
        assert defalft_value == {'amdefault': None}


def test_has_changed():
    test_value = {'testing': 1, 'count': 2}
    with form('TEST'):
        value = RuntimeSetting(key="TEST", raw_value=json.dumps(test_value))
        assert value.has_changed() is True


@pytest.mark.django_db
def test_delete_restores_default():
    test_value = {'testing': 1, 'count': 2}
    value = RuntimeSetting(key="TEST", raw_value=json.dumps(test_value))
    value.save()
    db_obj = value.__class__.objects.get(key='TEST')
    with form('TEST'):
        assert db_obj.value == {'count': 2}
        value.delete()
        db_obj2 = value.__class__.objects.get(key='TEST')
        assert db_obj2.raw_value == '{"amdefault": null}'
        assert db_obj2.value == {}


@pytest.mark.django_db
def test_runtimesettingswrapper():
    assert 1 == 2
