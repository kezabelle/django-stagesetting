# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from django.utils.translation import ugettext_lazy as _
from django.apps import AppConfig


class TestAppConfig(AppConfig):
    name = 'test_app'
    verbose_name = _("Test app")

