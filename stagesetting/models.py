from __future__ import unicode_literals
from __future__ import absolute_import
import json
from threading import RLock
from django.core.cache.backends.base import MEMCACHE_MAX_KEY_LENGTH
from django.core.exceptions import ValidationError
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
        data = registry.deserialize(self.raw_value)
        return self.get_form_class()(data=data, initial=data, files=None)

    def get_value(self):
        form = self.get_form()
        form.full_clean()
        return form.cleaned_data

    def set_value(self, value):
        self.raw_value = registry.serialize(value)

    value = property(get_value, set_value)

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


@python_2_unicode_compatible
class RuntimeSettingWrapper(object):
    __slots__ = ('settings', '_lock')
    def __init__(self, settings=None):
        super(RuntimeSettingWrapper, self).__setattr__('settings', settings)
        super(RuntimeSettingWrapper, self).__setattr__('_lock', RLock())

    def __str__(self):
        msg_dict = {'cls': self.__class__.__name__}
        if self.settings is None:
            return 'Unevaluated %(cls)s' % msg_dict
        return 'Evaluated %(cls)s' % msg_dict

    def __repr__(self):
        msg_dict = {'cls': self.__class__.__name__}
        if self.settings is None:
            msg_dict.update(settings=self.settings)
            return '<%(cls)s [Unevaluated] settings=%(settings)r>' % msg_dict
        msg_dict.update(settings=self.settings.keys())
        return '<%(cls)s [Evaluated] settings=%(settings)r>' % msg_dict

    def __dir__(self):
        exposed = ['settings']
        if self.settings is None:
            return exposed
        return self.settings.keys() + exposed

    def _fetch_settings(self):
        if self.settings is not None:
            return False

        with self._lock:
            settings = {}
            # Set up defaults which are registered.
            for default_key, default_value in registry._defaults.items():
                settings[default_key] = default_value

            # Set up anything that's been configured into the database.
            keys = frozenset(registry._registry.keys())
            for setting in RuntimeSetting.objects.filter(key__in=keys).iterator():  # noqa
                try:
                    settings[setting.key] = setting.value
                except ValidationError:
                    continue

            super(RuntimeSettingWrapper, self).__setattr__('settings', settings)
        return True

    def __getitem__(self, item):
        self._fetch_settings()
        return self.settings[item]

    def __getattr__(self, item):
        self._fetch_settings()
        return self.settings[item]

    def __len__(self):
        self._fetch_settings()
        return len(self.settings)

    def __contains__(self, item):
        self._fetch_settings()
        return item in self.settings

    def __iter__(self):
        self._fetch_settings()
        return self.settings.__iter__()

    def __setattr__(self, key, value):
        raise NotImplementedError

    def __delattr__(self, key):
        raise NotImplementedError

    def __setitem__(self, item, value):
        raise NotImplementedError

    def __delitem__(self, item):
        raise NotImplementedError
