# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
import logging
from django.core.checks import registry as django_check_registry
from django.db.utils import OperationalError
from django.utils.translation import ugettext_lazy as _
from django.apps import AppConfig


logger = logging.getLogger(__name__)


class StageSettingAppConfig(AppConfig):
    name = 'stagesetting'
    verbose_name = _("Run configuration")

    def ready(self):
        from .models import RuntimeSetting
        from .checks import check_setting
        from .utils import registry as stagesetting_registry
        django_check_registry.register(check_setting)
        # So I want to patch the defaults in by default, but apparently I
        # can't do so without migrating, nor in post_migrate.
        # I don't yet know in what ways this will break.
        try:
            stagesetting_registry.ready(sender=self.__class__, instance=self,
                                        model=RuntimeSetting)
        except OperationalError as exc:
            logger.warning("Could not do the database work in AppConfig.ready, "
                           "probably because nothing has migrated yet",
                           exc_info=1)
