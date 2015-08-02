# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from collections import namedtuple, OrderedDict
from datetime import datetime, timedelta
import json
from threading import RLock
from uuid import UUID
from django.conf import settings
from django.db.models import QuerySet, Model
from django.utils.encoding import force_text
from django.utils.encoding import python_2_unicode_compatible
from django.utils.module_loading import import_string
from .validators import validate_setting_name, validate_default
from .validators import validate_formish
from django.core.serializers.json import DjangoJSONEncoder


class JSONEncoder(DjangoJSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            # We don't use `T` as the sep, because Django doesn't include it
            # in it's DATETIME_INPUT_FORMATS
            r = o.isoformat(sep=str(' '))
            # We don't strip microseconds, because loss of precision is dumb
            # and I don't actually *care* about ECMA-262 or whatever.

            # We remove the timezone stuff because it ain't in
            # the DATETIME_INPUT_FORMATS
            if r.endswith('+00:00'):
                r = r[:-6]
            return r
        elif isinstance(o, timedelta):
            return force_text(o.total_seconds())
        elif isinstance(o, UUID):
            return force_text(o)
        elif isinstance(o, QuerySet):  # MultipleModelChoice
            return tuple(force_text(x.pk) for x in o)
        elif isinstance(o, Model):  # ModelChoice
            return force_text(o.pk)
        else:
            return super(JSONEncoder, self).default(o)  # pragma: no cover


class RegistryError(KeyError):
    pass

class AlreadyRegistered(RegistryError):
    pass

class NotRegistered(RegistryError):
    pass


Unregistered = namedtuple('Unregistered', 'setting_name form_class default')


@python_2_unicode_compatible
class FormRegistry(object):
    __slots__ = ('_registry', '_defaults', '_name', '_lock')

    def __init__(self, name=None):
        self._registry = {}
        self._defaults = {}
        self._name = name or 'default'
        self._lock = RLock()

    def __str__(self):
        return ', '.join(self._registry.keys())

    def __repr__(self):
        return '<%(mod)s.%(cls)s "%(name)s" [%(settings)s]>' % {
            'mod': self.__module__, 'cls': self.__class__.__name__,
            'name': self._name, 'settings': force_text(self),
        }

    def __len__(self):
        return len(self._registry)

    def ready(self, sender, instance, model):
        project_setting = getattr(settings, 'STAGESETTINGS', {})

        for setting_name, config in project_setting.items():
            config_length = len(config)
            if not config_length:
                continue
            # assert 1 <= config_length <= 2, \
            #     "Value should be a 1 or 2 length iterable"
            importable = config[0]
            default = None
            if config_length == 2:
                default = config[1]
            form = import_string(importable)
            self.register(key=setting_name, form_class=form, default=default)

        db_for_rw = model.objects.using(self._name)
        wanted = set(self.keys())
        existing = set(db_for_rw.filter(key__in=wanted)
                       .values_list('key', flat=True))
        missing = wanted - existing
        models = [model(key=setting_name,
                        raw_value=self.get_default(key=setting_name))
                  for setting_name in missing]
        return db_for_rw.bulk_create(models)

    def register(self, key, form_class, default=None):
        validate_setting_name(key)
        validate_formish(form_class)
        if default is not None:
            validate_default(default)
        with self._lock:
            if key in self._registry:
                raise AlreadyRegistered('The setting "%s" is already registered' % key)
            self._registry[key] = form_class
            self._defaults[key] = default or {}
            return True
    add = register
    __setitem__ = register

    def unregister(self, key):
        validate_setting_name(key)
        with self._lock:
            if key not in self._registry:
                raise NotRegistered('The setting "%s" is not registered' % key)
            existing_form = self._registry.pop(key)
            existing_default = self._defaults.pop(key)
            return Unregistered(setting_name=key, form_class=existing_form,
                                default=existing_default)
    remove = unregister
    pop = unregister
    __delitem__ = unregister

    def __getitem__(self, item):
        return self._registry[item]

    def __nonzero__(self):
        return len(self) > 0
    __bool__ = __nonzero__

    def keys(self):
        return self._registry.keys()

    def values(self):
        return self._registry.values()

    def _get_default(self, key):
        validate_setting_name(key)
        return self._defaults[key]

    def get_default(self, key):
        return self.serialize(self._get_default(key=key))

    def serialize(self, data):
        return json.dumps(data, cls=JSONEncoder)

    def deserialize(self, data):
        return json.loads(data)

registry = FormRegistry(name='default')
