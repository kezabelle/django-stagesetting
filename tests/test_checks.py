# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from django.test import override_settings
from stagesetting.checks import check_setting
from stagesetting.checks import W001, E001, E003, E002, E004, E006, E007, E005


def test_setting_not_set():
    result = check_setting(app_configs=None)
    assert len(result) == 1
    assert result[0].id == W001().id


def test_invalid_setting_name():
    settings = {
        'ghost': [],
    }
    with override_settings(STAGESETTINGS=settings):
        result = check_setting(app_configs=None)
        assert len(result) == 2
        assert result[0].id == E001().id


def test_invalid_value_type():
    settings = {
        'INVALID_TYPE': {},
    }
    with override_settings(STAGESETTINGS=settings):
        result = check_setting(app_configs=None)
        assert len(result) == 1
        assert result[0].id == E002().id


def test_invalid_value_length():
    settings = {
        'VALUE_LENGTH': [1, 2, 3],
    }
    with override_settings(STAGESETTINGS=settings):
        result = check_setting(app_configs=None)
        assert len(result) == 1
        assert result[0].id == E003().id


def test_invalid_type_for_value_argument_one():
    settings = {
        'NOT_A_STRING': [1],
    }
    with override_settings(STAGESETTINGS=settings):
        result = check_setting(app_configs=None)
        assert len(result) == 1
        assert result[0].id == E004().id

def test_invalid_dotted_path_for_value_argument_one():
    settings = {
        'NOT_A_STRING': ['this.should.NeverExist'],
    }
    with override_settings(STAGESETTINGS=settings):
        result = check_setting(app_configs=None)
        assert len(result) == 1
        assert result[0].id == E006().id


def test_invalid_form_object_for_value_argument_one():
    settings = {
        'NOT_A_STRING': ['django.VERSION'],
    }
    with override_settings(STAGESETTINGS=settings):
        result = check_setting(app_configs=None)
        assert len(result) == 1
        assert result[0].id == E007().id



def test_invalid_datatype_for_value_argument_two_defauls():
    settings = {
        'NOT_A_STRING': ['django.VERSION', set()],
    }
    with override_settings(STAGESETTINGS=settings):
        result = check_setting(app_configs=None)
        assert len(result) == 2
        assert result[1].id == E005().id
