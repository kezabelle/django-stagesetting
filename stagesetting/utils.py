# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from collections import namedtuple
from datetime import datetime
import json
from threading import RLock
from django.utils.encoding import force_text
from django.utils.encoding import python_2_unicode_compatible
from .validators import validate_setting_name
from .validators import validate_formish
try:
    from rest_framework.utils.encoders import JSONEncoder as JSONSuperclass
except ImportError:
    from django.core.serializers.json import DjangoJSONEncoder as JSONSuperclass

class JSONEncoder(JSONSuperclass):
    def default(self, o):
        if isinstance(o, datetime):
            # We don't use `T` as the sep, because Django doesn't include it
            # in it's DATETIME_INPUT_FORMATS
            r = o.isoformat(sep=str(' '))
            if o.microsecond:
                r = r[:23] + r[26:]
            if r.endswith('+00:00'):
                r = r[:-6] + 'Z'
            return r
        return super(JSONEncoder, self).default(o)


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

    def register(self, key, form_class, default=None):
        validate_setting_name(key)
        validate_formish(form_class)
        with self._lock:
            if key in self._registry:
                raise AlreadyRegistered('The setting "%s" is already registered' % key)
            self._registry[key] = form_class
            self._defaults[key] = default or {}
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
