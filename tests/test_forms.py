# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
import contextlib
from django.forms import Form
from django.forms import IntegerField
from stagesetting.forms import AdminFieldForm
from stagesetting.forms import CreateSettingForm
from stagesetting.models import RuntimeSetting
from stagesetting.utils import generate_form
from stagesetting.utils import registry
import pytest


def test_adminform_wrapover():
    form = generate_form({'a': 'a', 'b': 1})
    cls_name = str('AdminFields%s' % form.__name__)
    parents = (AdminFieldForm, form)
    replaced_form = type(form)(cls_name, parents, {})
    assert replaced_form().fields['a'].widget.attrs['class'] == 'vLargeTextField'


@contextlib.contextmanager
def fake_keys(*args):
    class ListPerPageForm(Form):
        count = IntegerField(min_value=1, max_value=99)
    for key in args:
        registry.register(key, ListPerPageForm)
    try:
        yield
    finally:
        for key in args:
            registry.unregister(key)


@pytest.mark.django_db
def test_create_settings_form_choices():
    RuntimeSetting.objects.create(key='LOL')
    RuntimeSetting.objects.create(key='ANOTHER_TEST')
    with fake_keys('HELLO', 'ANOTHER_TEST', 'SHARK_NADO', 'TEE_WRECKS'):
        form = CreateSettingForm()
    assert list(form.fields['key'].widget.choices) == [
        ('', '---------'),
        ('HELLO', 'Hello'),
        ('SHARK_NADO', 'Shark Nado'),
        ('TEE_WRECKS', 'Tee Wrecks')
    ]
