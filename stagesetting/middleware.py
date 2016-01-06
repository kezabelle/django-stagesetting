# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
import logging
from .models import RuntimeSettingWrapper, RuntimeSetting


logger = logging.getLogger(__name__)


class ApplyRuntimeSettings(object):
    __slots__ = ()

    def get_model(self):
        return RuntimeSetting

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not hasattr(request, 'stagesetting'):
            request.stagesetting = RuntimeSettingWrapper(model=self.get_model())
        else:
            logger.warning("Another middleware already set `request.stagesetting`")  # noqa
        return None
