# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from contextlib import contextmanager
import json
try:
    from unittest.mock import patch
except ImportError:  # Python 2, pragma: no cover
    from mock import patch
from uuid import UUID, uuid4
from datetime import timedelta, datetime, date, time
from decimal import Decimal
from collections import OrderedDict
from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms import fields, ModelChoiceField, ModelMultipleChoiceField
from django.utils.functional import empty
import re
import django
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from django.test.utils import override_settings, patch_logger
from django.utils.timezone import utc
try:
    from django_bleach.forms import BleachField
    CAN_BLEACH = True
except ImportError:  # could either not be installed, or too new a Django (1.9+)
    CAN_BLEACH = False
import pytest
from stagesetting.models import RuntimeSetting
from stagesetting.utils import (JSONEncoder, FormRegistry, generate_form,
                                list_files_in_static, get_htmlfield,
                                list_files_in_default_storage,
                                StaticFilesChoiceField,
                                PartialStaticFilesChoiceField,
                                PartialDefaultStorageFilesChoiceField,
                                DefaultStorageFilesChoiceField,
                                formstring_from_formclass, LRU_MAX)


@pytest.mark.django_db
def test_custom_json():
    user = get_user_model().objects.create()
    output = json.dumps({
        'uuid': UUID('98967ef2-a5a3-4c19-aefa-9bb8dc5fcbac'),
        'timedelta': timedelta(minutes=14),
        'datetime': datetime(2015, 8, 1, 16, 8, 51, 125068),
        'tzdatetime': datetime(2015, 8, 1, 16, 8, 51, 125068).replace(tzinfo=utc),
        'super': 1,
        'user': user,
        'user_qs': get_user_model().objects.all(),
    }, cls=JSONEncoder)
    assert '"timedelta": "840.0"' in output
    assert '"datetime": "2015-08-01 16:08:51.125068"' in output
    assert '"uuid": "98967ef2-a5a3-4c19-aefa-9bb8dc5fcbac"' in output
    assert '"tzdatetime": "2015-08-01 16:08:51.125068"' in output
    assert '"user_qs": ["1"]' in output
    assert '"user": "1"' in output


def formregistry_ready():
    fr = FormRegistry(name='default')
    newconfig = {
        'HELLO': ['test_app.forms.DatetimeForm', {'blip': 'blop'}],
        'HELLO2': ['test_app.forms.ListPerPageForm'],
    }
    with override_settings(STAGESETTINGS=newconfig):
        return fr.ready(sender=None, instance=None, model=RuntimeSetting)


@pytest.mark.django_db
def test_formregistry_ready_dict():
    fr = FormRegistry(name='default')
    newconfig = {
        'HELLO': ['test_app.forms.DatetimeForm', {'blip': 'blop'}],
        'HELLO2': {
            'int': 1,
            'email': 'a@b.com',
            'url': 'https://news.bbc.co.uk/',
        },
    }
    with override_settings(STAGESETTINGS=newconfig):
        with patch_logger('stagesetting.utils', 'info') as logger_calls:
            result = fr.ready(sender=None, instance=None, model=RuntimeSetting)
        # implicit = RuntimeSetting.objects.get(key='HELLO2')
        # assert fr.deserialize(implicit.raw_value) == {
        #     'email': 'a@b.com',
        #     'int': 1,
        #     'url': 'https://news.bbc.co.uk/'
        # }
        assert fr._get_default(key='HELLO2') == {
            "email": "a@b.com",
            "int": 1,
            "url": "https://news.bbc.co.uk/"
        }
    # assert len(result) == 2
    assert logger_calls == ['HELLO2 config is a dictionary, assuming it '
                            'represents both the form and default values']


@pytest.mark.django_db
def test_formregistry_ready_dict_with_different_defaults():
    fr = FormRegistry(name='default')
    newconfig = {
        'HELLO': ['test_app.forms.DatetimeForm', {'blip': 'blop'}],
        'HELLO2': [{
            'int': 1,
            'email': 'a@b.com',
            'url': 'https://news.bbc.co.uk/',
        }, {
            'int': 3,
            'email': 'a@b.com',
            'url': 'https://www.bbc.com/',
        }],
    }
    with override_settings(STAGESETTINGS=newconfig):
        result = fr.ready(sender=None, instance=None, model=RuntimeSetting)
        # implicit = RuntimeSetting.objects.get(key='HELLO2')
        # assert fr.deserialize(implicit.raw_value) == {
        #     'email': 'a@b.com',
        #     'int': 3,
        #     'url': 'https://www.bbc.com/'
        # }
        assert fr._get_default(key='HELLO2') == {
            "email": "a@b.com",
            "int": 3,
            "url": "https://www.bbc.com/"
        }
    # assert len(result) == 2


@pytest.mark.django_db
def test_formregistry_ready_dict_with_partial_defaults():
    fr = FormRegistry(name='default')
    newconfig = {
        'HELLO4': [{
            'int': 1,
            'email': 'a@b.com',
            'url': 'https://news.bbc.co.uk/',
        }, {
            'int': 12,
            'url': 'https://www.bbc.com/',
        }],
    }
    with override_settings(STAGESETTINGS=newconfig):
        result = fr.ready(sender=None, instance=None, model=RuntimeSetting)
        # implicit = RuntimeSetting.objects.get(key='HELLO4')
        # assert fr.deserialize(implicit.raw_value) == {
        #     'email': 'a@b.com',
        #     'int': 12,
        #     'url': 'https://www.bbc.com/'
        # }
        assert fr._get_default(key='HELLO4') == {
            "email": "a@b.com",
            "int": 12,
            "url": "https://www.bbc.com/"
        }
    # assert len(result) == 1


@pytest.mark.django_db
def test_formregistry_complex_dict_with_no_defaults():
    fr = FormRegistry(name='default')
    def user(): return get_user_model()(pk=2)
    def user_qs(): return get_user_model().objects.all()
    newconfig = {
        'COMPLEX_NO_DEFAULTS': {
            'model': user,
            'queryset': user_qs,
        },
    }
    with override_settings(STAGESETTINGS=newconfig):
        result = fr.ready(sender=None, instance=None, model=RuntimeSetting)
        # implicit = RuntimeSetting.objects.get(key='COMPLEX_NO_DEFAULTS')
        # assert fr.deserialize(implicit.raw_value) == {
        #     'model': '2',
        #     'queryset': []
        # }
        assert fr._get_default(key='COMPLEX_NO_DEFAULTS') == {
            'model': user,
            'queryset': user_qs,
        }
    # assert len(result) == 1


@pytest.mark.django_db
def test_formregistry_complex_dict_with_partial_defaults():
    fr = FormRegistry(name='default')
    def user(): return get_user_model()(pk=2)
    def user_qs(): return get_user_model().objects.all()
    newconfig = {
        'COMPLEX_NO_DEFAULTS': [{
            'model': user,
            'queryset': user_qs,
        }, {
            'model': 1,
        }]
    }
    with override_settings(STAGESETTINGS=newconfig):
        result = fr.ready(sender=None, instance=None, model=RuntimeSetting)
        # implicit = RuntimeSetting.objects.get(key='COMPLEX_NO_DEFAULTS')
        # assert fr.deserialize(implicit.raw_value) == {
        #     'model': 1,
        #     'queryset': []
        # }
        assert fr._get_default(key='COMPLEX_NO_DEFAULTS') == {
            'model': 1,
            'queryset': user_qs,
        }
    # assert len(result) == 1


@pytest.mark.django_db
def test_formregistry_complex_dict_with_different_partial_defaults():
    fr = FormRegistry(name='default')
    def user(): return get_user_model()(pk=2)
    def user_qs(): return get_user_model().objects.all()
    newconfig = {
        'COMPLEX_NO_DEFAULTS': [{
            'model': user,
            'queryset': user_qs,
        }, {
            'queryset': [11, 2],
        }]
    }
    with override_settings(STAGESETTINGS=newconfig):
        result = fr.ready(sender=None, instance=None, model=RuntimeSetting)
        # implicit = RuntimeSetting.objects.get(key='COMPLEX_NO_DEFAULTS')
        # assert fr.deserialize(implicit.raw_value) == {
        #     'model': '2',
        #     'queryset': [11, 2],
        # }
        assert fr._get_default(key='COMPLEX_NO_DEFAULTS') == {
            'model': user,
            'queryset': [11, 2],
        }
    # assert len(result) == 1


@pytest.mark.django_db
def test_formregistry_complex_dict_with_completely_different_defaults():
    fr = FormRegistry(name='default')
    def user(): return get_user_model()(pk=2)
    def user_qs(): return get_user_model().objects.all()
    newconfig = {
        'COMPLEX_NO_DEFAULTS': [{
            'model': user,
            'queryset': user_qs,
        }, {
            'model': 'ohgod',
            'wat': 'not-even-a-thing',  # this won't turn up ever, hopefully.
            'queryset': [11, 2],
        }]
    }
    with override_settings(STAGESETTINGS=newconfig):
        result = fr.ready(sender=None, instance=None, model=RuntimeSetting)
        # implicit = RuntimeSetting.objects.get(key='COMPLEX_NO_DEFAULTS')
        # assert fr.deserialize(implicit.raw_value) == {
        #     'model': 'ohgod',
        #     'queryset': [11, 2],
        # }
        assert fr._get_default(key='COMPLEX_NO_DEFAULTS') == {
            'model': 'ohgod',
            'queryset': [11, 2],
        }
    # assert len(result) == 1


class FormRegistryTestCase(TransactionTestCase):
    def test_ready(self):
        with self.assertNumQueries(0):
            result = formregistry_ready()
        self.assertIsNone(result)


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
        'set': {'a', 'b'},
        'regex': re.compile('test'),
        'ordereddict_choices': OrderedDict([
            ('a', '1'),
            ('2', 'two'),
        ]),
        'dict_choices': {
            'a': '1',
            '2': 'two',
        },
        'html': '<b>html!</b>',
        'static_url': settings.STATIC_URL,
        'static_storage': settings.STATICFILES_STORAGE,
        'partial_static_url': r'%sadmin/(.+)\.css' % settings.STATIC_URL,
        'partial_static_url2': r'^%sadmin/(.+)\.css|\.js' % settings.STATIC_URL,
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
        'uuid': str(uuid),
        'list': ['a'],
        'set': 'b',
        'regex': 'test',
        'ordereddict_choices': 'a',
        'dict_choices': '2',
        'html': '<em>html!</em>',
        'static_url': 'admin/css/login.css',
        'static_storage': 'admin/css/login.css',
        'partial_static_url': 'admin/css/login.css',
        'partial_static_url2': 'admin/js/core.js',
    }
    form = form_class(data=validate_data)
    valid = form.is_valid()
    assert form.errors == {}
    qs = form.cleaned_data.pop('queryset')
    uuid_result = form.cleaned_data.pop('uuid')
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
        'list': ['a'],
        'time': time(4, 23),
        'set': 'b',
        'date': daaate,
        'regex': 'test',
        'dict_choices': '2',
        'ordereddict_choices': 'a',
        'html': '<em>html!</em>',
        'static_url': 'admin/css/login.css',
        'static_storage': 'admin/css/login.css',
        'partial_static_url': 'admin/css/login.css',
        'partial_static_url2': 'admin/js/core.js',
    }
    assert valid is True


@pytest.mark.xfail(django.VERSION[:2] < (1, 8), reason="requires Django 1.8 to "
                                                       "use the duration field")
def test_generate_form_duration_field():
    data = {
        'timedelta': timedelta(days=2),
    }
    form_class = generate_form(data)
    validate_data = {
        'timedelta': '1',
    }
    form = form_class(data=validate_data)
    valid = form.is_valid()
    assert form.errors == {}
    assert form.cleaned_data == {
        'timedelta': timedelta(0, 1),
    }
    assert valid is True


def test_generate_form_cannot_figure_out_appropriate_type():
    data = {
        'unknown': empty,
    }
    with pytest.raises(ValidationError):
        form_class = generate_form(data)


def test_list_files_in_static():
    found = tuple(list_files_in_static())
    found2 = tuple(list_files_in_static())
    # make sure they're the same.
    assert found == found2
    assert len(found) == 1
    assert found[0][0] == 'admin'
    assert ('admin/js/core.js', 'js/core.js') in found[0][1]
    assert ('admin/css/changelists.css', 'css/changelists.css') in found[0][1]


def test_list_files_in_static_partial():
    found = sorted(list_files_in_static(only_matching='\.js$'))
    found2 = sorted(list_files_in_static(only_matching='\.js$'))
    # make sure they're the same.
    assert found == found2
    assert len(found) == 1
    assert found[0][0] == 'admin'
    assert ('admin/js/core.js', 'js/core.js') in found[0][1]


@contextmanager
def isolate_lru_cache(lru_cache_object):
    """Clear the cache of an LRU cache object on entering and exiting."""
    lru_cache_object.cache_clear()
    try:
        yield
    finally:
        lru_cache_object.cache_clear()


def test_list_files_in_static_cached():
    # import pdb; pdb.set_trace()
    with isolate_lru_cache(list_files_in_static):
        with patch('stagesetting.utils._get_files_in_static_storage') as is_called:
            for x in range(0, 6):
                list_files_in_static()
            is_called.assert_called_once_with(only_matching=None)


def test_list_files_in_default_storage():
    found = tuple(list_files_in_default_storage())
    found2 = tuple(list_files_in_default_storage())
    # make sure they're the same.
    assert found == found2
    assert found[0][0] == 'None'
    # Using negative indexes because py3k leaves __pycache__ folders behind
    # which break the numbering on Py2.
    assert found[-2][0] == 'static'
    assert found[-1][0] == 'templates'
    assert found[-2][1] == (('static/file_found_1.txt', 'file_found_1.txt'),
                           ('static/subdir/file_found_2.txt', 'subdir/file_found_2.txt'))
    assert found[-1][1] == (('templates/base.html', 'base.html'),
                            ('templates/example_usage.html', 'example_usage.html'))


def test_list_files_in_default_storage_partial():
    found = tuple(list_files_in_default_storage(only_matching='\.txt$'))
    found2 = tuple(list_files_in_default_storage(only_matching='\.txt$'))
    # make sure they're the same.
    assert found == found2
    assert len(found) == 1
    assert found[0][0] == 'static'
    assert found[0][1] == (('static/file_found_1.txt', 'file_found_1.txt'),
                           ('static/subdir/file_found_2.txt', 'subdir/file_found_2.txt'))


def test_list_files_in_default_storage_cached():
    # import pdb; pdb.set_trace()
    with isolate_lru_cache(list_files_in_default_storage):
        with patch('stagesetting.utils._get_files_in_default_storage') as is_called:
            for x in range(0, 6):
                list_files_in_default_storage()
            is_called.assert_called_once_with()


@pytest.mark.skipif(CAN_BLEACH is False, reason="Import error loading BleachField")
def test_get_htmlfield():
    lol = get_htmlfield(initial='woo')
    assert isinstance(lol, fields.CharField) is True
    assert isinstance(lol, BleachField) is True
    assert lol.initial == 'woo'


def test_static_files_choice_field():
    field = StaticFilesChoiceField()
    found = tuple(field.choices)
    assert found[0][0] == 'admin'
    assert ('admin/js/core.js', 'js/core.js') in found[0][1]
    assert ('admin/css/changelists.css', 'css/changelists.css') in found[0][1]


def test_partial_static_files_choice_field():
    field = PartialStaticFilesChoiceField(only_matching='\.js$')
    found = tuple(field.choices)
    assert found[0][0] == 'admin'
    assert ('admin/js/core.js', 'js/core.js')in found[0][1]


def test_default_storage_files_choice_field():
    field = DefaultStorageFilesChoiceField()
    found = tuple(field.choices)
    assert found[-2][0] == 'static'
    assert found[-1][0] == 'templates'
    assert found[-2][1] == (('static/file_found_1.txt', 'file_found_1.txt'),
                           ('static/subdir/file_found_2.txt', 'subdir/file_found_2.txt'))
    assert found[-1][1] == (('templates/base.html', 'base.html'),
                            ('templates/example_usage.html', 'example_usage.html'))


def test_partial_default_storage_files_choice_field():
    field = PartialDefaultStorageFilesChoiceField(only_matching='\.txt$')
    found = tuple(field.choices)
    # Using negative indexes because py3k leaves __pycache__ folders behind
    # which break the numbering on Py2.
    assert found[0][0] == 'static'
    assert found[0][1] == (('static/file_found_1.txt', 'file_found_1.txt'),
                           ('static/subdir/file_found_2.txt', 'subdir/file_found_2.txt'))


def test_generate_form_none_becomes_nullbooleanfield():
    form = generate_form({'field': None})()
    assert isinstance(form.fields['field'], fields.NullBooleanField)


def test_generate_form_datetime_becomes_datetimefield():
    form = generate_form({'field': datetime.now()})()
    assert isinstance(form.fields['field'], fields.DateTimeField) is True


def test_generate_form_date_becomes_datefield():
    form = generate_form({'field': datetime.now().date()})()
    assert isinstance(form.fields['field'], fields.DateField) is True


def test_generate_form_time_becomes_timefield():
    form = generate_form({'field': time(4, 23)})()
    assert isinstance(form.fields['field'], fields.TimeField) is True


def test_generate_form_decimal_becomes_decimalfield():
    form = generate_form({'field': Decimal('1.0')})()
    assert isinstance(form.fields['field'], fields.DecimalField) is True


def test_generate_form_float_becomes_floatfield():
    form = generate_form({'field': 1.5})()
    assert isinstance(form.fields['field'], fields.FloatField) is True


def test_generate_form_bool_becomes_booleanfield():
    form = generate_form({'field': True})()
    assert isinstance(form.fields['field'], fields.BooleanField) is True


def test_generate_form_int_becomes_integerfield():
    form = generate_form({'field': 1})()
    assert isinstance(form.fields['field'], fields.IntegerField) is True


def test_generate_form_list_becomes_multiplechoicefield():
    form = generate_form({'field': ['a', 'b']})()
    assert isinstance(form.fields['field'], fields.MultipleChoiceField) is True


def test_generate_form_tuple_becomes_multiplechoicefield():
    form = generate_form({'field': ('a', 'b')})()
    assert isinstance(form.fields['field'], fields.MultipleChoiceField) is True


def test_generate_form_ordereddict_becomes_choicefield():
    form = generate_form({'field': OrderedDict([
        ['1', '2'],
        ['2', '4'],
    ])})()
    assert isinstance(form.fields['field'], fields.ChoiceField) is True


def test_generate_form_dict_becomes_choicefield():
    form = generate_form({'field': {
        'a': 'b',
        'c': 'd',
    }})()
    assert isinstance(form.fields['field'], fields.ChoiceField) is True


def test_generate_form_set_becomes_choicefield():
    form = generate_form({'field': {'a', 'b', 'c'}})()
    assert isinstance(form.fields['field'], fields.ChoiceField) is True


def test_generate_form_model_becomes_modelchoicefield():
    form = generate_form({'field': get_user_model()(pk=1)})()
    assert isinstance(form.fields['field'], ModelChoiceField) is True


def test_generate_form_queryset_becomes_modelmultiplechoicefield():
    form = generate_form({'field': get_user_model().objects.all()})()
    assert isinstance(form.fields['field'], ModelMultipleChoiceField) is True


def test_generate_form_regex_becomes_regexfield():
    form = generate_form({'field': re.compile('')})()
    assert isinstance(form.fields['field'], fields.RegexField) is True


def test_generate_form_ipish_string_becomes_genericipfield():
    form = generate_form({'field': '127.0.0.1'})()
    assert isinstance(form.fields['field'], fields.GenericIPAddressField) is True


def test_generate_form_urlish_string_becomes_urlfield():
    form = generate_form({'field': 'https://news.bbc.co.uk/'})()
    assert isinstance(form.fields['field'], fields.URLField) is True


def test_generate_form_emailish_string_becomes_emailfield():
    form = generate_form({'field': 'a@b.com'})()
    assert isinstance(form.fields['field'], fields.EmailField) is True


def test_generate_form_staticurl_becomes_staticfileschoicefield():
    form = generate_form({'field': settings.STATIC_URL})()
    assert isinstance(form.fields['field'], StaticFilesChoiceField) is True


def test_generate_form_staticstorage_becomes_staticfileschoicefield():
    form = generate_form({'field': settings.STATICFILES_STORAGE})()
    assert isinstance(form.fields['field'], StaticFilesChoiceField) is True



def test_generate_form_staticurl_startswith_becomes_staticfileschoicefield():
    form = generate_form({'field': '%s/test' % settings.STATIC_URL})()
    assert isinstance(form.fields['field'], PartialStaticFilesChoiceField) is True


def test_generate_form_mediaurl_becomes_staticfileschoicefield():
    form = generate_form({'field': settings.MEDIA_URL})()
    assert isinstance(form.fields['field'], DefaultStorageFilesChoiceField) is True


def test_generate_form_mediastorage_becomes_staticfileschoicefield():
    form = generate_form({'field': settings.DEFAULT_FILE_STORAGE})()
    assert isinstance(form.fields['field'], DefaultStorageFilesChoiceField) is True


def test_generate_form_mediaurl_startswith_becomes_staticfileschoicefield():
    form = generate_form({'field': '%s/test' % settings.MEDIA_URL})()
    assert isinstance(form.fields['field'], PartialDefaultStorageFilesChoiceField) is True


def test_generate_form_slugish_string_becomes_slugfield():
    form = generate_form({'field': 'a-b'})()
    assert isinstance(form.fields['field'], fields.SlugField) is True


def test_generate_form_decimalish_string_becomes_decimalfield():
    form = generate_form({'field': '1.0'})()
    assert isinstance(form.fields['field'], fields.DecimalField) is True


def test_generate_form_datetimeish_string_becomes_datetimefield():
    form = generate_form({'field': '01/01/2016 01:01:01'})()
    assert isinstance(form.fields['field'], fields.DateTimeField) is True

def test_generate_form_dateish_string_becomes_datefield():
    form = generate_form({'field': '01/01/2016'})()
    assert isinstance(form.fields['field'], fields.DateField) is True

def test_generate_form_timeish_string_becomes_timefield():
    form = generate_form({'field': '01:01:01'})()
    assert isinstance(form.fields['field'], fields.TimeField) is True


def test_generate_form_intish_string_becomes_integerfield():
    form = generate_form({'field': '1'})()
    assert isinstance(form.fields['field'], fields.IntegerField) is True


def test_generate_form_slugish_string_has_invalid_slug_chars_slugfield():
    form = generate_form({'field': 'a-b!!!'})()
    assert isinstance(form.fields['field'], fields.SlugField) is False
    assert isinstance(form.fields['field'], fields.CharField) is True


def test_generate_form_slugish_string_has_invalid_slug_chars_slugfield2():
    form = generate_form({'field': 'a-b '})()
    assert isinstance(form.fields['field'], fields.SlugField) is False
    assert isinstance(form.fields['field'], fields.CharField) is True


def test_generate_form_with_sorting():
    form = generate_form({'z':1, 'a': 2})
    assert tuple(form.base_fields.keys()) == ('a', 'z')


def test_generate_form_without_sorting():
    form = generate_form(OrderedDict([
        ('z',1),
        ('a', 2),
    ]))
    assert tuple(form.base_fields.keys()) == ('z', 'a')

@pytest.mark.skipif(CAN_BLEACH is False, reason="Import error loading BleachField")
def test_generate_form_to_string():
    form = generate_form(OrderedDict([
        ('z', '<b>lol</b>'),
        ('c', 'lol'),
        ('a', 2),
        ('e', Decimal('1.0')),
        ('f', datetime(2015, 10, 10, 10, 10, 10)),
    ]))
    assert "\n".join(formstring_from_formclass(form())) == """class ZCAEFForm(forms.Form):
    z = django_bleach.forms.BleachField(initial='<b>lol</b>', widget=widgets.Textarea)
    c = fields.CharField(initial='lol', widget=widgets.TextInput)
    a = fields.IntegerField(initial=2, widget=widgets.NumberInput)
    e = fields.DecimalField(initial=Decimal('1.0'), widget=widgets.NumberInput)
    f = fields.DateTimeField(initial=datetime.datetime(2015, 10, 10, 10, 10, 10), widget=widgets.DateTimeInput)"""

@pytest.mark.skipif(CAN_BLEACH is True, reason="BleachField imported OK, so it won't be a CharField")
def test_generate_form_to_string():
    form = generate_form(OrderedDict([
        ('z', '<b>lol</b>'),
        ('c', 'lol'),
        ('a', 2),
        ('e', Decimal('1.0')),
        ('f', datetime(2015, 10, 10, 10, 10, 10)),
    ]))
    assert "\n".join(formstring_from_formclass(form())) == """class ZCAEFForm(forms.Form):
    z = fields.CharField(initial='<b>lol</b>', widget=widgets.TextInput)
    c = fields.CharField(initial='lol', widget=widgets.TextInput)
    a = fields.IntegerField(initial=2, widget=widgets.NumberInput)
    e = fields.DecimalField(initial=Decimal('1.0'), widget=widgets.NumberInput)
    f = fields.DateTimeField(initial=datetime.datetime(2015, 10, 10, 10, 10, 10), widget=widgets.DateTimeInput)"""
