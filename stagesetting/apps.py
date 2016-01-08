# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
import logging
from django.core.checks import registry as django_check_registry
from django.utils.translation import ugettext_lazy as _
from django.apps import AppConfig


logger = logging.getLogger(__name__)


class StageSettingAppConfig(AppConfig):
    name = 'stagesetting'
    verbose_name = _("Run configuration")

    def get_stagesetting_model(self):
        from .models import RuntimeSetting
        return RuntimeSetting

    def get_stagesetting_model_modeladmin(self):
        from .admin import RuntimeSettingAdmin
        return RuntimeSettingAdmin

    def ready(self):
        from .checks import check_setting
        from .utils import registry as stagesetting_registry
        django_check_registry.register(check_setting)
        stagesetting_registry.ready(sender=self.__class__, instance=self,
                                        model=self.get_stagesetting_model())
        self.set_stagesetting_modeladmin()

    def set_stagesetting_modeladmin(self):
        from django.contrib import admin
        admin.site.register(self.get_stagesetting_model(),
                            self.get_stagesetting_model_modeladmin())
