# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from .models import RuntimeSettingWrapper


def runtime_settings(request):
    if hasattr(request, 'stagesetting'):
        settings = request.stagesetting
    else:
        settings = RuntimeSettingWrapper()
    return {
        'STAGESETTING': settings,
    }
