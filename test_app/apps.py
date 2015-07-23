# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from django.core.exceptions import ValidationError
from django.forms import Form, IntegerField, DateTimeField, DateField, \
    SplitDateTimeField
from django.utils.translation import ugettext_lazy as _
from django.apps import AppConfig
from stagesetting.utils import registry


class DateForm(Form):
    start = DateField()
    end = DateField()

    def clean(self):
        cd = self.cleaned_data
        if 'start' in cd and 'end' in cd and cd['start'] > cd['end']:
            raise ValidationError("nope")
        return cd


class DatetimeForm(Form):
    start = DateTimeField()
    end = DateTimeField()

    def clean(self):
        cd = self.cleaned_data
        if 'start' in cd and 'end' in cd and cd['start'] > cd['end']:
            # removing from cleaned_data is a complete failboat, so screw that.
            self._errors["end"] = self.error_class(["End must be after start"])
        return cd


class ListPerPageForm(Form):
    count = IntegerField(initial=25, min_value=1, max_value=99)


class TestAppConfig(AppConfig):
    name = 'test_app'
    verbose_name = _("Test app")

    def ready(self):
        registry.register('LIST_PER_PAGE', ListPerPageForm)
        registry.register('DATES', DateForm)
        registry.register('DATETIMES', DatetimeForm)

