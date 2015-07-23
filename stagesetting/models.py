import json
from django.core.cache.backends.base import MEMCACHE_MAX_KEY_LENGTH
from django.core.exceptions import ValidationError
from django.db import router
from django.db.models.manager import Manager
from django.db.models.query import QuerySet
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from django.db.models import Model, TextField
from django.db.models.fields import CharField
from django.db.models.fields import DateTimeField
from .utils import registry
from .validators import validate_setting_name


class RuntimeSettingQuerySet(QuerySet):
    def key_exists(self, key):
        try:
            validate_setting_name(key)
        except ValidationError as e:
            raise self.model.DoesNotExist("Invalid setting name")
        return self.filter(key=key).exists()


@python_2_unicode_compatible
class RuntimeSetting(Model):
    key = CharField(max_length=MEMCACHE_MAX_KEY_LENGTH, unique=True,
                    db_index=True, validators=[validate_setting_name],
                    verbose_name=_("Name"))
    raw_value = TextField()
    created = DateTimeField(auto_now_add=True)
    modified = DateTimeField(auto_now=True)

    objects = Manager.from_queryset(RuntimeSettingQuerySet)()

    def __str__(self):
        return self.key

    def get_form_class(self):
        return registry[self.key]

    def get_form(self):
        return self.get_form_class()(data=json.loads(self.raw_value), files=None)

    @property
    def value(self):
        form = self.get_form()
        form.full_clean()
        return form.cleaned_data

    @property
    def default_value(self):
        return registry._get_default(key=self.key)

    def has_changed(self):
        return self.value != self.default_value
    has_changed.short_description = _("Changed")
    has_changed.boolean = True

    def __repr__(self):
        return '<%(cls)s key="%(key)s", raw_value="%(value)s">' % {
            'mod': self.__module__, 'cls': self.__class__.__name__,
            'key': self.key, 'value': self.raw_value,
        }

    def delete(self, using=None):
        assert self._get_pk_val() is not None, (
            "%s object can't be deleted because its %s attribute is set to None." %
            (self._meta.object_name, self._meta.pk.attname)
        )
        default = registry.get_default(self.key)
        self.raw_value = default
        self.full_clean()
        self.save()
    delete.alters_data = True

    class Meta:
        ordering = ('key',)
        verbose_name = _("Setting")
        verbose_name_plural = _("Settings")


class RuntimeSettingWrapper(object):
    __slots__ = ('settings',)
    def __init__(self):
        self.settings = None

    def _fetch_settings(self):
        if self.settings is not None:
            return False
        for setting in RuntimeSetting.objects.all().iterator():
            try:
                value = setting.value
            except ImportError:
                value = setting.default_value
            self.settings[setting.key] = value
        for default_key, default_value in registry._defaults.items():
            if default_key not in self.settings:
                self.settings[default_key] = default_value
        return True

    def __getitem__(self, item):
        self._fetch_settings()
        return self.settings[item]

    def __getattr__(self, item):
        self._fetch_settings()
        return self.settings[item]

    def __len__(self):
        return len(self.settings)

    def __contains__(self, item):
        return item in self.settings

    def __iter__(self):
