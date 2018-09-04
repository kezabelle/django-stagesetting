# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from django import VERSION as django_version
from django.template import Library
from stagesetting.models import RuntimeSettingWrapper, RuntimeSetting

register = Library()

if django_version[0:2] < (1, 9):
    tag = register.assignment_tag
else: # Django 1.9+ allows simple_tag to also be an "as tag"
    tag = register.simple_tag


@tag(takes_context=True)
def stagesetting(context):
    if 'STAGESETTING' in context:
        wrapper = context['STAGESETTING']
    elif 'request' in context and hasattr(context['request'], 'stagesetting'):
        wrapper = context['request'].stagesetting
    elif hasattr(context, 'request') and hasattr(context.request, 'stagesetting'):
        wrapper = context.request.stagesetting
    else:
        wrapper = RuntimeSettingWrapper(model=RuntimeSetting)
    return wrapper
