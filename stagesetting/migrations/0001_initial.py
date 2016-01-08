# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import stagesetting.validators


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='RuntimeSetting',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('key', models.CharField(db_index=True, unique=True, max_length=250, verbose_name='Name', validators=[stagesetting.validators.SettingNameValidator()])),
                ('raw_value', models.TextField()),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ('key',),
                'db_table': 'stagesetting_runtimesetting',
                'verbose_name': 'Setting',
                'verbose_name_plural': 'Settings',
            },
        ),
    ]
