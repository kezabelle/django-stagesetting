# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.forms import Form, DateTimeField, IntegerField, ModelChoiceField, \
    ModelMultipleChoiceField
from django.forms import DateField


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


class ModelChoicesForm(Form):
    single_user = ModelChoiceField(queryset=get_user_model().objects.all())
    many_users = ModelMultipleChoiceField(queryset=get_user_model().objects.all())
    another = IntegerField(min_value=1, max_value=5)
