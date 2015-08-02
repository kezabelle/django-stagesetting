# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
import logging
from django.core.exceptions import ImproperlyConfigured
from django.views.generic.list import MultipleObjectMixin


logger = logging.getLogger(__name__)


class MultipleObjectMixinReplacement(MultipleObjectMixin):

    def get_allow_empty(self):
        if not hasattr(self.request, 'stagesetting'):
            raise ImproperlyConfigured(
                "To use the replacement ListView you must add "
                "`stagesetting.middleware.ApplyRuntimeSettings` to your "
                "project's `MIDDLEWARE_CLASSES`")
        try:
            return self.request.stagesetting.PAGINATION['allow_empty']
        except KeyError as exc:
            raise ImproperlyConfigured(
                "To use the replacement ListView you must add `PAGINATION` "
                "as a key in your `STAGESETTINGS`")

    def get_paginate_by(self, queryset):
        if not hasattr(self.request, 'stagesetting'):
            raise ImproperlyConfigured(
                "To use the replacement ListView you must add "
                "`stagesetting.middleware.ApplyRuntimeSettings` to your "
                "project's `MIDDLEWARE_CLASSES`")
        try:
            return self.request.stagesetting.PAGINATION['per_page']
        except KeyError as exc:
            raise ImproperlyConfigured(
                "To use the replacement ListView you must add `PAGINATION` "
                "as a key in your `STAGESETTINGS`")
