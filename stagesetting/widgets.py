# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from django.contrib.admin.widgets import AdminIntegerFieldWidget


class AdminIntegerFieldReplacement(AdminIntegerFieldWidget):
    input_type = 'number'

