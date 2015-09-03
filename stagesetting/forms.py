# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from functools import partial
from django.forms import fields
from django.contrib.admin import widgets as admin_widgets
from django.core.cache.backends.base import MEMCACHE_MAX_KEY_LENGTH
from django.core.exceptions import ValidationError
from django.db.models import BLANK_CHOICE_DASH
from django.forms import Form, Select
from django.forms.fields import CharField
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _
from .models import RuntimeSetting
from stagesetting import widgets
from stagesetting.utils import registry
import warnings


class CreateSettingForm(Form):
    key = CharField(min_length=1, max_length=MEMCACHE_MAX_KEY_LENGTH,
                    label=_("Name"))

    def __init__(self, *args, **kwargs):
        super(CreateSettingForm, self).__init__(*args, **kwargs)
        existing = frozenset(RuntimeSetting.objects.keys())
        possible = frozenset(registry.keys())
        creatable = possible - existing
        def pretty_name(value):
            return value.replace('_', ' ').strip().title()
        final = list((x, pretty_name(x)) for x in sorted(creatable))
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



ADMINFORMFIELD_FOR_FORMFIELD_DEFAULTS = {
    fields.DateTimeField: {
    #     'form_class': fields.SplitDateTimeField,
        'widget': admin_widgets.AdminSplitDateTime
    },
    # fields.SplitDateTimeField: {'widget': admin_widgets.AdminSplitDateTime},
    fields.DateField: {'widget': admin_widgets.AdminDateWidget},
    fields.TimeField: {'widget': admin_widgets.AdminTimeWidget},
    fields.URLField: {'widget': admin_widgets.AdminURLFieldWidget},
    fields.IntegerField: {'widget': widgets.AdminIntegerFieldReplacement},
    fields.CharField: {'widget': admin_widgets.AdminTextInputWidget,
                       'widget_attrs': {'class': 'vLargeTextField'}},
    fields.ImageField: {'widget': admin_widgets.AdminFileWidget},
    fields.FileField: {'widget': admin_widgets.AdminFileWidget},
    fields.EmailField: {'widget': admin_widgets.AdminEmailInputWidget},
    # ModelMultipleChoiceField: {'widget': partial(widgets.FilteredSelectMultiple, verbose_name='hello', is_stacked=False)}
}


class AdminFieldForm(object):
    def __init__(self, *args, **kwargs):
        super(AdminFieldForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field.__class__ in ADMINFORMFIELD_FOR_FORMFIELD_DEFAULTS:
                custom = ADMINFORMFIELD_FOR_FORMFIELD_DEFAULTS[field.__class__]
                if field.widget.__class__ == field.__class__.widget:
                    old_attrs = field.widget.attrs.copy()
                    if 'widget_attrs' in custom:
                        old_attrs.update(custom['widget_attrs'])
                    field.widget = custom['widget'](attrs=old_attrs)
            if field.__class__ == fields.SplitDateTimeField:
                warnings.warn("Don't use SplitDateTimeField it's a multiwidget "
                              "and they're kind of a pain to split.", RuntimeWarning)
