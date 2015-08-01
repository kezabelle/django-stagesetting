# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
import contextlib
from django.forms import Form, IntegerField
from django.test import TransactionTestCase, RequestFactory
from django.test.utils import patch_logger
from stagesetting.models import RuntimeSettingWrapper
from stagesetting.context_processors import runtime_settings
from stagesetting.middleware import ApplyRuntimeSettings
from stagesetting.utils import registry


@contextlib.contextmanager
def form(key):
    class ListPerPageForm(Form):
        count = IntegerField(initial=25, min_value=1, max_value=99)
    registry.register(key, ListPerPageForm, {'amdefault': None})
    yield ListPerPageForm
    registry.unregister(key)


def test_runtime_settings_without_middleware(rf):
    request = rf.get('/')
    output = runtime_settings(request=request)
    assert 'STAGESETTING' in output
    assert isinstance(output['STAGESETTING'], RuntimeSettingWrapper)
    return output


def test_runtime_settings_with_middleware(rf):
    request = rf.get('/')
    ApplyRuntimeSettings().process_view(request=request, view_func=None,
                                        view_args=(), view_kwargs={})
    output = runtime_settings(request=request)
    assert 'STAGESETTING' in output
    assert isinstance(output['STAGESETTING'], RuntimeSettingWrapper)
    assert output['STAGESETTING'] is request.stagesetting
    return output


def test_runtime_settings_with_middleware_doesnt_apply_twice(rf):
    request = rf.get('/')
    mw = ApplyRuntimeSettings()
    mw.process_view(request=request, view_func=None, view_args=(), view_kwargs={})
    with patch_logger('stagesetting.middleware', 'warning') as logger_calls:
        mw.process_view(request=request, view_func=None, view_args=(),
                        view_kwargs={})
        message = ['Another middleware already set `request.stagesetting`']
        assert logger_calls == message


class QueryTestCase(TransactionTestCase):
    def test_runtime_settings_without_middleware(self):
        with form('LIST_PER_PAGE'):
            with self.assertNumQueries(0):
                rf = RequestFactory()
                output = test_runtime_settings_without_middleware(rf=rf)
            with self.assertNumQueries(1):
                output['STAGESETTING'].LIST_PER_PAGE
            with self.assertNumQueries(0):
                output['STAGESETTING'].LIST_PER_PAGE

    def test_runtime_settings_with_middleware(self):
        with form('LIST_PER_PAGE'):
            with self.assertNumQueries(0):
                rf = RequestFactory()
                output = test_runtime_settings_with_middleware(rf=rf)
            with self.assertNumQueries(1):
                output['STAGESETTING'].LIST_PER_PAGE
            with self.assertNumQueries(0):
                output['STAGESETTING'].LIST_PER_PAGE
