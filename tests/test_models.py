# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
import contextlib
import json
from django.contrib.auth import get_user_model
from django.forms import IntegerField, Form, ModelChoiceField, \
    ModelMultipleChoiceField
import pytest
from stagesetting.models import RuntimeSetting, RuntimeSettingWrapper
from stagesetting.utils import registry


@contextlib.contextmanager
def form(key):
    class ListPerPageForm(Form):
        count = IntegerField(initial=25, min_value=1, max_value=99)
    registry.register(key, ListPerPageForm, {'amdefault': None})
    yield ListPerPageForm
    registry.unregister(key)


@contextlib.contextmanager
def userform(key):
    class ModelChoicesForm(Form):
        single_user = ModelChoiceField(queryset=get_user_model().objects.all())
        many_users = ModelMultipleChoiceField(queryset=get_user_model().objects.all())
        another = IntegerField(min_value=1, max_value=5)
    registry.register(key, ModelChoicesForm)
    yield ModelChoicesForm
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
    test_value = {'testing': 1, 'count': 2}
    test2_value = {'testing': 1, 'count': 4}
    RuntimeSetting.objects.create(key="TEST", raw_value=json.dumps(test_value))
    RuntimeSetting.objects.create(key="TEST2", raw_value=json.dumps(test2_value))

    class ListPerPageForm(Form):
        count = IntegerField(initial=25, min_value=1, max_value=99)

    registry.register('TEST', ListPerPageForm, {'count': '3'})
    registry.register('TEST_DEFAULT', ListPerPageForm, {'count': '14'})

    wrapped = RuntimeSettingWrapper()
    assert wrapped['TEST'] == {'count': 2}
    assert wrapped['TEST_DEFAULT'] == {'count': '14'}

    # new values won't be discovered until the existing data is updated
    RuntimeSetting.objects.create(key="TEST_DEFAULT",
                                  raw_value=json.dumps(test2_value))
    assert wrapped['TEST_DEFAULT'] == {'count': '14'}
    wrapped2 = RuntimeSettingWrapper()
    assert wrapped2['TEST_DEFAULT'] == {'count': 4}
    assert bool(wrapped) is True
    assert 'TEST' in wrapped
    assert wrapped.TEST == {'count': 2}
    data = set(x for x in wrapped)
    assert data == {'TEST', 'TEST_DEFAULT'}


@pytest.mark.django_db
def test_can_serialize_modelchoices():
    user1 = get_user_model().objects.create(username='woo')
    user2 = get_user_model().objects.create(username='woo2')
    with userform('USERFORM') as form_class:
        form_ = form_class(data={'single_user': user1.pk,
                                 'many_users': [user1.pk, user2.pk],
                                 'another': 3})
        form_.is_valid()

        value = RuntimeSetting(key="USERFORM")
        value.value = form_.cleaned_data
        assert '"single_user": "1"' in value.raw_value
        assert '"many_users": ["1", "2"]' in value.raw_value
        assert value.value['single_user'] == user1
        assert set(value.value['many_users']) == set([user1, user2])
