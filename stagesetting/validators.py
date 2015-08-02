# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.translation import ugettext_lazy as _
from re import compile


setting_name_re_str = '^[A-Z][A-Z0-9_]+[A-Z0-9]$'

class SettingNameValidator(RegexValidator):
    message = _("Setting format should be CAPITAL_WITH_UNDERSCORES")
    regex = compile(setting_name_re_str)

validate_setting_name = SettingNameValidator()


def validate_formish(value):
    try:
        assert hasattr(value, 'is_valid')
        assert hasattr(value, 'clean')
    except AssertionError:
        raise ValidationError("%(form)r doesn't appear to be a Form class" % {
            'form': value})


def validate_default(value):
    try:
        assert hasattr(value, '__getitem__')
        assert hasattr(value, 'keys')
    except AssertionError:
        raise ValidationError("%r doesn't appear to be dictish" % value)
