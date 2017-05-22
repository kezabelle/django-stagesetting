# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from django.core.management import BaseCommand, CommandError
from stagesetting.models import RuntimeSetting, RuntimeSettingWrapper


class Command(BaseCommand):
    help = ""

    def get_model(self):
        return RuntimeSetting

    def get_wrapper(self):
        return RuntimeSettingWrapper(model=self.get_model())

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='command')
        parser_list = subparsers.add_parser('list', cmd=self, help='list all settings')

        parser_get = subparsers.add_parser('get', cmd=self, help='get a specific setting')
        parser_get.add_argument('key', help='name of the setting to get', metavar='KEY')

    def write_setting_name(self, key):
        sep = '=' * len(key)
        self.stdout.write(self.style.HTTP_REDIRECT(key))
        self.stdout.write(self.style.HTTP_REDIRECT(sep))

    def write_setting_data(self, value):
        data = sorted(value.items())
        maxlength = max(len(x[0]) for x in data)
        tmpl = "{{k: <{}}}".format(maxlength)
        for form_key, form_value in data:
            key = tmpl.format(k=form_key)
            self.stdout.write("{k}: {v!r}".format(k=self.style.HTTP_INFO(key), v=form_value))

    def write_setting_raw(self, value):
        msg = "Raw dictionary"
        sep = '=' * len(msg)
        self.stdout.write(self.style.MIGRATE_HEADING(msg))
        self.stdout.write(self.style.MIGRATE_HEADING(sep))
        self.stdout.write('{!r}'.format(value))

    def handle(self, command, key=None, value=None, *args, **options):
        wrapped = self.get_wrapper()

        if command == "list":
            for key, value in sorted(wrapped):
                self.write_setting_name(key)
                self.write_setting_data(value)
                self.stdout.write("\n")
        elif command == "get":
            if key not in wrapped:
                raise CommandError("Invalid setting name {!r}".format(key))
            self.write_setting_name(key)
            value = wrapped[key]
            self.write_setting_data(value)
            self.stdout.write("\n")
            self.write_setting_raw(value)
            self.stdout.write("\n")
        elif command == "set":
            pass

