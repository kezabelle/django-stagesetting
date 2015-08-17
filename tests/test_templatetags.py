# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from django.template import Template, Context
import pytest


def test_loading():
    assert Template("{% load stagesetting %}").render(Context()) == ''


@pytest.mark.django_db
def test_works():
    assert Template("{% load stagesetting %}{% stagesetting as LOL %}{{ LOL|length }}").render(Context()) == '2'
