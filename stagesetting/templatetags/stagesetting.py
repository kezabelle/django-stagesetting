# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from django.template import Library
from stagesetting.models import RuntimeSettingWrapper, RuntimeSetting

register = Library()


@register.assignment_tag(takes_context=True)
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
