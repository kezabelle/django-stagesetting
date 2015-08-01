# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from django.utils.translation import ugettext_lazy as _
from django.apps import AppConfig
from .utils import registry


class StageSettingAppConfig(AppConfig):
    name = 'stagesetting'
    verbose_name = _("Run configuration")

    def ready(self):
        from .models import RuntimeSetting
        return registry.ready(sender=self.__class__, instance=self,
                              model=RuntimeSetting)

