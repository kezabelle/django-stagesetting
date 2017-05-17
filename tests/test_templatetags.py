# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from django.template import Template, Context, RequestContext
import pytest

from stagesetting.context_processors import runtime_settings
from stagesetting.middleware import ApplyRuntimeSettings


@pytest.fixture
def stagesetting_mw():
    return ApplyRuntimeSettings().process_view


def test_loading():
    assert Template("{% load stagesetting %}").render(Context()) == ''


@pytest.mark.django_db
def test_works():
    assert Template("{% load stagesetting %}{% stagesetting as LOL %}{{ LOL|length }}").render(Context()) == '2'


@pytest.mark.django_db
def test_reuses_existing_context_variable_if_set_via_context_processor(rf):
    request = rf.get('/')
    context = Context()
    context.update(runtime_settings(request=request))
    assert Template("{% load stagesetting %}{% stagesetting as LOL %}{{ LOL|length }}").render(context) == '2'


@pytest.mark.django_db
def test_reuses_existing_context_variable_if_set_via_middleware_and_request_in_context(rf, stagesetting_mw):
    request = rf.get('/')
    stagesetting_mw(request=request, view_func=None, view_args=None, view_kwargs=None)
    context = Context({'request': request})
    assert Template("{% load stagesetting %}{% stagesetting as LOL %}{{ LOL|length }}").render(context) == '2'


@pytest.mark.django_db
def test_reuses_existing_context_variable_if_set_via_middleware_is_requestcontext(rf, stagesetting_mw):
    request = rf.get('/')
    stagesetting_mw(request=request, view_func=None, view_args=None, view_kwargs=None)
    context = RequestContext(request, {})
    assert Template("{% load stagesetting %}{% stagesetting as LOL %}{{ LOL|length }}").render(context) == '2'
