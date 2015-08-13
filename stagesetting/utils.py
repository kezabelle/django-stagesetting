# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from collections import namedtuple, OrderedDict
from datetime import datetime, timedelta, date, time
from decimal import Decimal
from itertools import chain, groupby
import json
import logging
from threading import RLock
from uuid import UUID
from django.conf import settings
from django.contrib.staticfiles.finders import get_finders
from django.core.files.storage import default_storage
from django.utils.translation import ugettext as _
from django.core.exceptions import ValidationError
from django.core.validators import validate_slug, validate_ipv46_address, \
    URLValidator, validate_email
from django.db.models import QuerySet, Model
from django import forms
from django.utils.encoding import force_text
from django.utils.encoding import python_2_unicode_compatible
from django.utils.module_loading import import_string
from django.utils.six import string_types, integer_types
from .validators import validate_setting_name, validate_default
from .validators import validate_formish
from django.core.serializers.json import DjangoJSONEncoder


logger = logging.getLogger(__name__)


class JSONEncoder(DjangoJSONEncoder):
    def default(self, o):
        if callable(o):
            o = o()
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
            default = None
            first_param_is_dictish = False
            # if the only parameter is a dictionary, make it a form.
            try:
                validate_default(config)
                form = generate_form(config)
                default = config
            except ValidationError:
                # if the first parameter is a dictionary, generate a form
                try:
                    validate_default(config[0])
                    form = generate_form(config[0])
                    default = config[0]
                    first_param_is_dictish = True
                # if it's not a dictionary, it's a path to a Form class
                except ValidationError:
                    form = import_string(config[0])
                    first_param_is_dictish = False
            # if a second parameter is given, it is always the defaults.
            try:
                default = config[1]
            except IndexError:
                logger.info("No default found in the second parameter "
                            "for %s" % setting_name)
            except KeyError:
                logger.info("%s config is a dictionary, assuming it represents "
                            "both the form and default values" % setting_name)
            if first_param_is_dictish and default is not None:
                duped = config[0].copy()
                # don't call .update(), instead only copy in the ones which
                # existed in the form ...
                for k, v in default.items():
                    if k in duped:
                        duped[k] = v
                default = duped
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


def list_files_in_static():
    finders = get_finders()
    finders_results = (finder.list(ignore_patterns=None) for finder in finders)
    found_files = chain.from_iterable(finders_results)

    def first_part_of_path(x):
        """
        Ensure that items without a directory part are grouped together before
        being passed to groupby
        """
        split_by_path_sep = x.split('/')
        leftmost = split_by_path_sep[0]
        if leftmost == x:
            return _('None')
        return leftmost

    filenames_only = sorted((filename for filename, storage in found_files),
                            key=first_part_of_path)

    def tuple_to_choices(groupname, flat_tuple):
        """
        Given a tuple of:
            ('path/subpath/filename',
             'path/another_path/filename2')
        Yield something like:
            (('path/subpath/filename', 'subpath/filename'),
             ('path/another_path/filename2', 'another_path/filename2'))
        where `path` got replaced in the display value based on the
        given `groupname`
        """
        return tuple((v, v.replace(groupname, '', 1).lstrip('/'))
                     for v in flat_tuple)

    groups = groupby(filenames_only, first_part_of_path)
    evaluated_groups = tuple((groupname, tuple(groupitems))
                             for groupname, groupitems in groups)
    fixed = ((groupname, tuple_to_choices(groupname, groupitems))
             for groupname, groupitems in evaluated_groups
             if not groupname.startswith('.') and groupitems)
    # import pdb; pdb.set_trace()
    return fixed


def list_files_in_default_storage():
    dirs, files = default_storage.listdir('')
    return sorted((f, f) for f in files)


def _select_field(v):
    if callable(v):
        v = v()
    if v is None:
        return forms.NullBooleanField(initial=v)
    elif isinstance(v, datetime):
        return forms.DateTimeField(initial=v)
    elif isinstance(v, date):
        return forms.DateField(initial=v)
    elif isinstance(v, time):
        return forms.TimeField(initial=v)
    elif isinstance(v, timedelta):
        return forms.DurationField(initial=v)
    elif isinstance(v, Decimal):
        return forms.DecimalField(initial=v)
    elif isinstance(v, float):
        return forms.FloatField(initial=v)
    elif isinstance(v, bool):
        return forms.BooleanField(initial=v, required=False)
    elif isinstance(v, integer_types):
        return forms.IntegerField(initial=v)
    elif isinstance(v, UUID):
        try:
            return forms.UUIDField(initial=v)
        except AttributeError:
            logger.error("You're on an older version of Django which doesn't "
                         "have UUIDField, so a charfield is being used "
                         "instead", exc_info=1)
            return forms.CharField(initial=str(v))
    elif isinstance(v, (list, tuple)):
        choices = tuple((k, k) for k in v)
        return forms.MultipleChoiceField(choices=choices)
    elif isinstance(v, OrderedDict):
        choices = tuple((k, subv) for k, subv in v.items())
        return forms.ChoiceField(choices=choices)
    elif isinstance(v, dict):
        choices = sorted((k, subv) for k, subv in v.items())
        return forms.ChoiceField(choices=choices)
    elif isinstance(v, (set, frozenset)):
        choices = sorted((k, k) for k in v)
        return forms.ChoiceField(choices=choices)
    elif isinstance(v, Model):
        kws = {'queryset': v.__class__.objects.all()}
        if hasattr(v, 'pk') and v.pk is not None:
            kws.update(initial=v.pk)
        return forms.ModelChoiceField(**kws)
    elif isinstance(v, QuerySet):
        return forms.ModelMultipleChoiceField(queryset=v)
    elif isinstance(v, string_types):
        try:
            validate_ipv46_address(v)
            return forms.GenericIPAddressField(initial=v)
        except ValidationError:
            pass
        try:
            URLValidator()(v)
            return forms.URLField(initial=v)
        except ValidationError:
            pass
        try:
            validate_email(v)
            return forms.EmailField(initial=v)
        except ValidationError:
            pass
        if ' ' not in v and '-' in v:
            try:
                validate_slug(v)
                return forms.SlugField(initial=v)
            except ValidationError:
                pass
        if v in (settings.STATIC_URL, settings.STATICFILES_STORAGE):
            return forms.ChoiceField(choices=list_files_in_static)
        if v in (settings.MEDIA_URL, settings.DEFAULT_FILE_STORAGE):
            return forms.ChoiceField(choices=list_files_in_default_storage)
        return forms.CharField(initial=v)


def generate_form(dictionary):
    form_fields = OrderedDict()
    for k, v in sorted(dictionary.items()):
        if callable(v):
            v = v()
        form_fields[k] = _select_field(v)
    if len(form_fields) != len(dictionary):
        raise ValidationError("Could not generate all fields for form")
    return type(str('DictionaryGeneratedForm'), (forms.Form,), form_fields)








