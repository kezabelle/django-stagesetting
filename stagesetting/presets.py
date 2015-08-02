# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from django.forms import IntegerField, BooleanField, Form


class Pagination(Form):
    per_page = IntegerField(min_value=1)
    allow_empty = BooleanField(initial=False)
