# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from django.contrib.sites.models import Site
from django.core.cache.backends.base import MEMCACHE_MAX_KEY_LENGTH
from django.core.exceptions import ValidationError
from django.db.models import BLANK_CHOICE_DASH
from django.forms import Form, Select
from django.forms.fields import CharField
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _
from .models import RuntimeSetting
from stagesetting.utils import registry


class CreateSettingForm(Form):
    key = CharField(min_length=1, max_length=MEMCACHE_MAX_KEY_LENGTH,
                    label=_("Name"))

    def __init__(self, *args, **kwargs):
        super(CreateSettingForm, self).__init__(*args, **kwargs)
        existing = frozenset(RuntimeSetting.objects.values_list('key', flat=True))
        possible = frozenset(registry.keys())
        creatable = possible - existing
        final = list((x, x) for x in creatable)
        self.fields['key'].widget = Select(choices=BLANK_CHOICE_DASH + final)


    def clean_key(self):
        key = self.cleaned_data['key']
        try:
            exists = RuntimeSetting.objects.key_exists(key=key)
        except RuntimeSetting.DoesNotExist as e:
            raise ValidationError(force_text(e))
        if exists:
            raise ValidationError("Setting already exists")
        return key

    def save(self):
        key = self.cleaned_data['key']
        value = registry.get_default(key=key)
        obj = RuntimeSetting(key=key, raw_value=value)
        obj.full_clean()
        obj.save()
        return obj
