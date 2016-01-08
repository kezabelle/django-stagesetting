# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
import os
from django.utils.text import slugify
from django.utils.lru_cache import lru_cache
from functools import partial
from django.forms import TypedChoiceField
import re
from collections import namedtuple, OrderedDict
from datetime import datetime, timedelta, date, time
from decimal import Decimal, InvalidOperation
from itertools import chain, groupby
import json
import logging
from threading import RLock
from uuid import UUID
from django.conf import settings
from django.contrib.staticfiles.finders import get_finders
from django.core.files.storage import default_storage
from django.core.urlresolvers import NoReverseMatch, reverse
from django.utils.html import strip_tags
from django.utils.translation import ugettext as _
from django.core.exceptions import ValidationError
from django.core.validators import (validate_ipv46_address, URLValidator,
                                    validate_email)
from django.db.models import QuerySet, Model
from django import forms
from django.utils.encoding import force_text
from django.utils.encoding import python_2_unicode_compatible
from django.utils.module_loading import import_string
from django.utils.six import string_types, integer_types
from .validators import validate_setting_name, validate_default
from .validators import validate_formish
from django.core.serializers.json import DjangoJSONEncoder
try:
    forms.fields.CallableChoiceIterator
    CALLABLE_CHOICES = True
except AttributeError:  # pragma: no cover
    # Django 1.7 doesn't have a way of lazily evaluating a set of choices.
    CALLABLE_CHOICES = False


logger = logging.getLogger(__name__)
LRU_MAX = 5


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
        return None

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


def _get_files_in_static_storage(only_matching=None):
    finders = get_finders()
    finders_results = (finder.list(ignore_patterns=None) for finder in finders)
    found_files = chain.from_iterable(finders_results)
    filenames_only = (filename for filename, storage in found_files)
    if only_matching is not None:
        # Apply a regex search over the given filenames to choose only
        # matching elements.
        filenames_only = (fname for fname in filenames_only
                          if re.search(only_matching, fname))
    return filenames_only


def make_storage_choices(found_files):
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

    filenames_only = sorted(found_files, key=first_part_of_path)

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
    return fixed


@lru_cache(LRU_MAX)
def list_files_in_static(only_matching=None):
    return tuple(make_storage_choices(
        found_files=_get_files_in_static_storage(only_matching=only_matching)))


class StaticFilesChoiceField(TypedChoiceField):
    def __init__(self, *args, **kwargs):
        if 'choices' not in kwargs:  # pragma: no cover
            kwargs['choices'] = list_files_in_static
        if CALLABLE_CHOICES is False:
            kwargs['choices'] = kwargs['choices']()
        kwargs['coerce'] = force_text
        super(StaticFilesChoiceField, self).__init__(*args, **kwargs)


class PartialStaticFilesChoiceField(StaticFilesChoiceField):
    def __init__(self, only_matching, *args, **kwargs):
        if 'choices' not in kwargs:  # pragma: no cover
            kwargs['choices'] = partial(list_files_in_static,
                                        only_matching=only_matching)
        super(PartialStaticFilesChoiceField, self).__init__(*args, **kwargs)


def _get_files_in_default_storage(directory=''):
    dirs, files = default_storage.listdir(directory)
    for fn in files:
        location = os.path.join(directory, fn)
        yield location
    for subdir in dirs:
        if directory:
            subdir = os.path.join(directory, subdir)
        for fn in _get_files_in_default_storage(directory=subdir):
            yield fn


@lru_cache(LRU_MAX)
def list_files_in_default_storage(only_matching=None):
    filenames_only = _get_files_in_default_storage()
    if only_matching is not None:
        # Apply a regex search over the given filenames to choose only
        # matching elements.
        filenames_only = (fname for fname in filenames_only
                          if re.search(only_matching, fname))
    return tuple(make_storage_choices(found_files=filenames_only))


class DefaultStorageFilesChoiceField(TypedChoiceField):
    def __init__(self, *args, **kwargs):
        if 'choices' not in kwargs:  # pragma: no cover
            kwargs['choices'] = list_files_in_default_storage
        if CALLABLE_CHOICES is False:
            kwargs['choices'] = kwargs['choices']()
        kwargs['coerce'] = force_text
        super(DefaultStorageFilesChoiceField, self).__init__(*args, **kwargs)


class PartialDefaultStorageFilesChoiceField(DefaultStorageFilesChoiceField):
    def __init__(self, only_matching, *args, **kwargs):
        if 'choices' not in kwargs:  # pragma: no cover
            kwargs['choices'] = partial(list_files_in_default_storage,
                                        only_matching=only_matching)
        super(PartialDefaultStorageFilesChoiceField, self).__init__(*args, **kwargs)


def get_htmlfield(**kwargs):
    try:
        from django_bleach.forms import BleachField as HTMLField
    except ImportError:
        logger.warning("Using an HTML field without having `django-bleach` "
                       "installed; you should install it. Falling back to "
                       "using a CharField")
        HTMLField = forms.CharField

    def ckeditor_field(**kws):  # pragma: no cover
        try:
            reverse('ckeditor_upload')
        except NoReverseMatch:
            logging.info("Tried to use `django-ckeditor` without setting up "
                         "the URLconf requirements.", exc_info=1)
            return None
        # unlike most of the other fields,
        from ckeditor.widgets import CKEditorWidget
        kws.update(widget=CKEditorWidget)
        return HTMLField(**kws)

    def tinymce_field(**kws):  # pragma: no cover
        from tinymce.widgets import TinyMCE
        kws.update(widget=TinyMCE)
        return HTMLField(**kws)

    def django_markdown_field(**kws):  # pragma: no cover
        try:
            reverse('django_markdown_preview')
        except NoReverseMatch:
            logging.info("Tried to use `django_markdown` without setting up "
                         "the URLconf requirements", exc_info=1)
            return None
        from django_markdown.widgets import MarkdownWidget
        kws.update(widget=MarkdownWidget)
        return HTMLField(**kws)

    def pagedown_field(**kws):  # pragma: no cover
        from pagedown.widgets import PagedownWidget
        kws.update(widget=PagedownWidget)
        return HTMLField(**kws)

    def epiceditor_field(**kws):  # pragma: no cover
        from epiceditor.widgets import EpicEditorWidget
        kws.update(widget=EpicEditorWidget)
        return HTMLField(**kws)

    known = OrderedDict([
        ('ckeditor', ckeditor_field),
        ('tinymce', tinymce_field),
        ('django_markdown', django_markdown_field),
        ('pagedown', pagedown_field),
        ('epiceditor', epiceditor_field),
    ])
    for appname, field_function in known.items():
        if appname not in settings.INSTALLED_APPS:  # pragma: no cover
            continue
        field = field_function(**kwargs)
        if field is None:
            # Some of the widgets need urls configured. If they haven't been,
            # they're unusable so try the next one.
            continue
        return field
    # Bleach or CharField.
    return HTMLField(**kwargs)


uuid_re = re.compile(r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}|[a-fA-F0-9]{32}$')


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
            return forms.RegexField(regex=uuid_re, initial=str(v), max_length=36)
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
    elif isinstance(v, re._pattern_type):
        return forms.RegexField(regex=v)
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
        # cast integerlike strings as such.
        if v.isdigit():
            v = int(v)
            return forms.IntegerField(initial=v)
        try:
            v = Decimal(v)
            return forms.DecimalField(initial=v)
        except InvalidOperation:
            pass
        # allow 'ffffffff-ffff-ffff-ffff-ffffffffffff' to do the right thing.
        try:
            UUID(v)
        except ValueError:
            pass
        else:
            try:
                return forms.UUIDField(initial=v)
            except AttributeError:
                logger.error("You're on an older version of Django which doesn't "
                             "have UUIDField, so a charfield is being used "
                             "instead", exc_info=1)
                return forms.RegexField(regex=uuid_re, initial=str(v), max_length=36)

        def can_be_parsed_as_temporal(value, field):
            for format in field.input_formats:
                try:
                    field.strptime(value, format)
                    return True
                except (ValueError, TypeError):
                    continue
            return False

        if can_be_parsed_as_temporal(v, forms.TimeField()):
            return forms.TimeField(initial=v)

        if can_be_parsed_as_temporal(v, forms.DateField()):
            return forms.DateField(initial=v)

        if can_be_parsed_as_temporal(v, forms.DateTimeField()):
            return forms.DateTimeField(initial=v)

        if v in (settings.STATIC_URL, settings.STATICFILES_STORAGE):
            return StaticFilesChoiceField()

        if v in (settings.MEDIA_URL, settings.DEFAULT_FILE_STORAGE):
            return DefaultStorageFilesChoiceField()

        # filtered by a raw string representing a regex.
        starts_with_static_url = v.startswith(settings.STATIC_URL)
        if starts_with_static_url:
            v = v[len(settings.STATIC_URL):]
            return PartialStaticFilesChoiceField(only_matching=v)

        # filtered by a raw string representing a regex.
        starts_with_media_url = v.startswith(settings.MEDIA_URL)
        if starts_with_media_url:
            v = v[len(settings.MEDIA_URL):]
            return PartialDefaultStorageFilesChoiceField(only_matching=v)

        # filtered by a raw string representing a tethered regex.
        starts_with_tethered_static_url = v.startswith('^%s' % settings.STATIC_URL)  # noqa
        if starts_with_tethered_static_url:
            # removes ^/static/ or whatever and instead tethers to the
            # beginning of the next part.
            # so ^/static/admin/.+$ should become ^/admin/.+$
            v = '^%s' % v[len('^%s' % settings.STATIC_URL):]
            return PartialStaticFilesChoiceField(only_matching=v)

        # filtered by a raw string representing a tethered regex.
        starts_with_tethered_media_url = v.startswith('^%s' % settings.MEDIA_URL)  # noqa
        if starts_with_tethered_media_url:
            # removes ^/media/ or whatever and instead tethers to the
            # beginning of the next part.
            # so ^/media/admin/.+$ should become ^/admin/.+$
            v = '^%s' % v[len('^%s' % settings.MEDIA_URL):]
            return PartialDefaultStorageFilesChoiceField(only_matching=v)

        if ' ' not in v and '-' in v and slugify(v) == v:
            return forms.SlugField(initial=v)

        if strip_tags(v) != v:
            return get_htmlfield(initial=v)

        return forms.CharField(initial=v)


def generate_form(dictionary):
    form_fields = OrderedDict()
    if isinstance(dictionary, OrderedDict):
        fields_to_make = dictionary.items()
    else:
        fields_to_make = sorted(dictionary.items())
    for k, v in fields_to_make:
        if callable(v):
            v = v()
        newfield = _select_field(v)
        if newfield is not None:
            form_fields[k] = newfield
    if len(form_fields) != len(dictionary):
        raise ValidationError("Could not generate all fields for form")
    return type(str('DictionaryGeneratedForm'), (forms.Form,), form_fields)


def formstring_from_formclass(form):
    names = ''.join(x.title() for x in form.fields.keys())
    yield 'class {name}Form(forms.Form):'.format(name=names)
    for field_name, field in form.fields.items():
        field_module = field.__class__.__module__
        if field_module == 'django.forms.fields':
            field_module = 'fields'
        field_type = field.__class__.__name__
        widget_type = field.widget.__class__.__name__
        widget_module = field.widget.__class__.__module__
        if widget_module == 'django.forms.widgets':
            widget_module = 'widgets'
        if isinstance(field.initial, string_types):
            initial = "'%s'" % field.initial
        else:
            initial = repr(field.initial)
        yield ('    %(key)s = %(module)s.%(type)s(initial=%(initial)s, '
               'widget=%(widget_module)s.%(widget_type)s)' % {
            'key': field_name, 'module': field_module, 'type': field_type,
            'initial': initial, 'widget_type': widget_type,
            'widget_module': widget_module,
        })


def prettify_setting_name(value):
    """ Convert `SETTING_NAME` to `Setting Name`"""
    return value.replace('_', ' ').strip().title()
