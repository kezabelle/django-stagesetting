# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from functools import partial
from django.core.checks import Warning
from django.core.checks import Error
from django.core.checks import Info
from django.core.exceptions import ValidationError
from django.utils.six import string_types
from stagesetting.utils import generate_form

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

I001 = partial(Info,
    id="stagesetting.I001",
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


def validate_as_dict(key, value):
    """
    Returns `True` if it's a dict we can generate a form for,
    `False` if it's not, or an Error instance comes out of the form.
    """
    try:
        validate_default(value)
        form = generate_form(value)
    except ValidationError:
        return None
    try:
        validate_formish(form)
        return form
    except ValidationError:
        return None  # E007(obj=key)


def validate_params_of_list(key, value):
    """
    Assumes the `value` is a list ...
    """
    errors = []
    config_length = len(value)
    # has multiple values
    if not isinstance(value, (list, tuple)):
        try:
            wtf_is_it = type(value).__name__
        except AttributeError:  # pragma: no cover
            wtf_is_it = '???'
        return [E002(obj=key, hint="Got `%s` instead" % wtf_is_it)]
    if isinstance(value, (list, tuple)) and config_length not in (1, 2):
        return [E003(obj=key)]

    # first try to make a form
    form = validate_as_dict(key, value=value[0])
    ignore_defaults_set_check = True
    if form is None:
        ignore_defaults_set_check = False
        if not isinstance(value[0], string_types):
            return [E004(obj=key)]
        # then try and import a form
        try:
            form = import_string(value[0])
        except (ImportError, AttributeError) as exc:
            return [E006(obj=key)]
        # make sure our value feels like a form
        try:
            validate_formish(form)
        except ValidationError:
            errors.append(E007(obj=key))
            # we won't have `base_fields`, so don't check it ...
            ignore_defaults_set_check = True

    # make sure the second param feels like a dictionary
    if config_length == 2:
        try:
            validate_default(value[1])
        except ValidationError as exc:
            errors.append(E005(obj=key))
        else:
            # if the first part is not a dict, and the second part is,
            # report on what is missing.
            if ignore_defaults_set_check is False:
                fields_in_form = frozenset(form.base_fields.keys())
                fields_in_defaults = frozenset(value[1].keys())
                missing = fields_in_form - fields_in_defaults
                if missing:
                    errors.append(I001(
                        obj=key, msg='The following keys are not in '
                                     'the defaults: %s' % ', '.join(missing)))
    return errors


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

            only_param_is_dict = validate_as_dict(key, value)
            if only_param_is_dict is None:
                list_errors = validate_params_of_list(key, value)
                errors.extend(list_errors)
    return errors
