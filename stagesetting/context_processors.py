# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from .models import RuntimeSettingWrapper, RuntimeSetting


def runtime_settings_for_model(request, model):
    if hasattr(request, 'stagesetting'):
        settings = request.stagesetting
    else:
        settings = RuntimeSettingWrapper(model=model)
    return {
        'STAGESETTING': settings,
    }


def runtime_settings(request):
    return runtime_settings_for_model(request=request, model=RuntimeSetting)
