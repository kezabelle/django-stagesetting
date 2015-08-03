# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
import json
from uuid import UUID, uuid4
from datetime import timedelta, datetime, date, time
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from django.test.utils import override_settings
from django.utils.timezone import utc
import pytest
from stagesetting.models import RuntimeSetting
from stagesetting.utils import JSONEncoder, FormRegistry, generate_form


def test_custom_json():
    output = json.dumps({
        'uuid': UUID('98967ef2-a5a3-4c19-aefa-9bb8dc5fcbac'),
        'timedelta': timedelta(minutes=14),
        'datetime': datetime(2015, 8, 1, 16, 8, 51, 125068),
        'tzdatetime': datetime(2015, 8, 1, 16, 8, 51, 125068).replace(tzinfo=utc),
        'super': 1,
    }, cls=JSONEncoder)
    assert '"timedelta": "840.0"' in output
    assert '"datetime": "2015-08-01 16:08:51.125068"' in output
    assert '"uuid": "98967ef2-a5a3-4c19-aefa-9bb8dc5fcbac"' in output
    assert '"tzdatetime": "2015-08-01 16:08:51.125068"' in output


def formregistry_ready():
    fr = FormRegistry(name='default')
    newconfig = {
        'HELLO': ['test_app.forms.DatetimeForm', {'blip': 'blop'}],
        'HELLO2': ['test_app.forms.ListPerPageForm'],
    }
    with override_settings(STAGESETTINGS=newconfig):
        return fr.ready(sender=None, instance=None, model=RuntimeSetting)


@pytest.mark.django_db
def test_formregistry_ready():
    result = formregistry_ready()
    assert len(result) == 2


class FormRegistryTestCase(TransactionTestCase):
    def test_ready(self):
        with self.assertNumQueries(3):
            result = formregistry_ready()
        self.assertEqual(len(result), 2)


@pytest.mark.django_db
def test_generate_form():
    def user():
        return get_user_model()()

    def user_qs():
        return get_user_model().objects.all()

    user = get_user_model().objects.create()

    data = {
        'int': 1,
        'email': 'a@b.com',
        'url': 'https://news.bbc.co.uk/',
        'model': user,
        'queryset': user_qs,
        'datetime': datetime.today(),
        'date': date.today(),
        'time': time(4, 23),
        'boolean': False,
        'nullboolean': None,
        'ip': '127.0.0.1',
        'slug': 'test-test',
        'text': 'char field',
        'decimal': Decimal('3.25'),
        'float': 2.3,
        'uuid': uuid4(),
        'list': ['a', 'b'],
        'set': {'a', 'b'}
    }
    form_class = generate_form(data)
    uuid = uuid4()
    dt = datetime.today()
    daaate = dt.date()
    validate_data = {
        'int': 1,
        'email': 'a@b.com',
        'url': 'https://news.bbc.co.uk/',
        'model': str(user.pk),
        'queryset': [str(user.pk)],
        'datetime': dt.strftime('%Y-%m-%d %H:%M:%S'),
        'date': daaate.strftime('%Y-%m-%d'),
        'time': '4:23',
        'boolean': '',
        'nullboolean': '0',
        'ip': '127.0.0.1',
        'slug': 'test-test',
        'text': 'char field',
        'decimal': '3.25',
        'float': '2.3',
        'uuid': str(uuid.hex),
        'list': ['a'],
        'set': 'b'
    }
    form = form_class(data=validate_data)
    valid = form.is_valid()
    assert form.errors == {}
    qs = form.cleaned_data.pop('queryset')
    assert form.cleaned_data == {
        'url': 'https://news.bbc.co.uk/',
        'text': 'char field',
        'nullboolean': None,
        'datetime': dt.replace(microsecond=0),
        'decimal': Decimal('3.25'),
        'boolean': False,
        'ip': '127.0.0.1',
        'float': 2.3,
        'email': 'a@b.com',
        'slug': 'test-test',
        'model': user,
        'int': 1,
        'uuid': uuid,
        'list': ['a'],
        'time': time(4, 23),
        'set': 'b',
        'date': daaate
    }
    assert valid is True
