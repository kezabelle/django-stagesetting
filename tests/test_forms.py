# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from stagesetting.forms import AdminFieldForm
from stagesetting.utils import generate_form


def test_adminform_wrapover():
    form = generate_form({'a': 'a', 'b': 1})
    cls_name = str('AdminFields%s' % form.__name__)
    parents = (AdminFieldForm, form)
    replaced_form = type(form)(cls_name, parents, {})
    assert replaced_form().fields['a'].widget.attrs['class'] == 'vLargeTextField'
