# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from functools import partial
from django.core.checks import Warning
from django.core.checks import Error
from django.core.exceptions import ValidationError
from django.utils.six import string_types
try:
    from django.utils.module_loading import import_string
except ImportError:  # pragma: no cover
    from django.utils.module_loading import import_by_path as import_string
from stagesetting.validators import validate_setting_name
from stagesetting.validators import validate_default
from stagesetting.validators import validate_formish

W001 = partial(Warning,
    msg="You don't have any settings defined",
    hint="Set STAGESETTINGS in your project settings module",
    id='stagesetting.W001',
)

E001 = partial(Error,
    msg="Invalid name found in config",
    hint="Setting names should be UPPER_CASE_WITH_UNDERSCORES",
    id="stagesetting.E001",
)

E002 = partial(Error,
    msg="The values for settings keys should be lists or tuples",
    id="stagesetting.E002",
)

E003 = partial(Error,
    msg="The tuple or list should be 1 or 2 indexes long",
    id="stagesetting.E003",
)

E004 = partial(Error,
    msg="The first value for the setting is invalid",
    hint="Provide the 'dotted.path.to.a.Form' as a string",
    id="stagesetting.E004",
)

E005 = partial(Error,
    msg="The first value for the setting is invalid",
    hint="The default data for a setting should be a dictionary of data which "
         "would be valid in the Form",
    id="stagesetting.E005",
)

E006 = partial(Error,
    msg="the form could not be imported",
    hint="Change the 'dotted.path.to.a.Form' to a valid import path",
    id="stagesetting.E006",
)

E007 = partial(Error,
    msg="The import path given does not appear to be a valid Form",
    hint="Use a standard form subclass",
    id="stagesetting.E007",
)


# noinspection PyUnusedLocal
def check_setting(app_configs, **kwargs):
    from django.conf import settings
    errors = []
    if not hasattr(settings, 'STAGESETTINGS'):
        errors.append(W001(obj='settings'))
    else:
        for key, value in settings.STAGESETTINGS.items():
            try:
                validate_setting_name(key)
            except ValidationError as exc:
                errors.append(E001(obj=key))

            config_length = len(value)

            if not isinstance(value, (list, tuple)):
                try:
                    wtf_is_it = type(value).__name__
                except AttributeError:  # pragma: no cover
                    wtf_is_it = '???'
                errors.append(E002(obj=key, hint="Got `%s` instead" % wtf_is_it))
                return errors
            elif config_length not in (1, 2):
                errors.append(E003(obj=key))
                return errors

            if not isinstance(value[0], string_types):
                errors.append(E004(obj=key))
                return errors

            try:
                form = import_string(value[0])
            except (ImportError, AttributeError) as exc:
                errors.append(E006(obj=key))  # noqa
            else:
                try:
                    validate_formish(form)
                except ValidationError as exc:
                    errors.append(E007(obj=key))  # noqa

            if config_length == 2:
                try:
                    validate_default(value[1])
                except ValidationError as exc:
                    errors.append(E005(obj=key))
    return errors
