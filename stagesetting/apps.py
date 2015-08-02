# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from django.core.checks import registry as django_check_registry
from django.utils.translation import ugettext_lazy as _
from django.apps import AppConfig


class StageSettingAppConfig(AppConfig):
    name = 'stagesetting'
    verbose_name = _("Run configuration")

    def ready(self):
        from .models import RuntimeSetting
        from .checks import check_setting
        from .utils import registry as stagesetting_registry
        django_check_registry.register(check_setting)
        stagesetting_registry.ready(sender=self.__class__, instance=self,
                                    model=RuntimeSetting)

