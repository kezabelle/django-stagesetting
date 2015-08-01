# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
import logging
from .models import RuntimeSettingWrapper


logger = logging.getLogger(__name__)


class ApplyRuntimeSettings(object):
    __slots__ = ()

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not hasattr(request, 'stagesetting'):
            request.stagesetting = RuntimeSettingWrapper()
        else:
            logger.warning("Another middleware already set `request.stagesetting`")  # noqa
        return None
