# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
import json
from uuid import UUID
from datetime import timedelta, datetime
from django.test import TransactionTestCase
from django.test.utils import override_settings
from django.utils.timezone import utc
import pytest
from stagesetting.models import RuntimeSetting
from stagesetting.utils import JSONEncoder, FormRegistry


def test_custom_json():
    output = json.dumps({
        'uuid': UUID('98967ef2-a5a3-4c19-aefa-9bb8dc5fcbac'),
        'timedelta': timedelta(minutes=14),
        'datetime': datetime(2015, 8, 01, 16, 8, 51, 125068),
        'tzdatetime': datetime(2015, 8, 01, 16, 8, 51, 125068).replace(tzinfo=utc),
        'super': 1,
    }, cls=JSONEncoder)
    assert '"timedelta": "840.0"' in output
    assert '"datetime": "2015-08-01 16:08:51.125068"' in output
    assert '"uuid": "98967ef2-a5a3-4c19-aefa-9bb8dc5fcbac"' in output
    assert '"tzdatetime": "2015-08-01 16:08:51.125068"' in output


def formregistry_ready():
    fr = FormRegistry(name='default')
    newconfig = {
        'HELLO': ['test_app.apps.DatetimeForm', {'blip': 'blop'}],
        'HELLO2': ['test_app.apps.ListPerPageForm'],
    }
    with override_settings(STAGESETTINGS=newconfig):
        return fr.ready(sender=None, instance=None, model=RuntimeSetting)


@pytest.mark.django_db
def test_formregistry_ready():
    result = formregistry_ready()
    assert len(result) == 2


class FormRegistryTestCase(TransactionTestCase):
    def test_ready(self):
        with self.assertNumQueries(3):
            result = formregistry_ready()
        self.assertEqual(len(result), 2)
