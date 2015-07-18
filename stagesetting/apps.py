# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from django.utils.translation import ugettext_lazy as _
from django.apps import AppConfig


class StageSettingAppConfig(AppConfig):
    name = 'stagesetting'
    verbose_name = _("Run configuration")

