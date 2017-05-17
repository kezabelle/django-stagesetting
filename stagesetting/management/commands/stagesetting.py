# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from django.core.management import BaseCommand
from stagesetting.models import RuntimeSetting, RuntimeSettingWrapper


class Command(BaseCommand):
    help = ""

    def get_model(self):
        return RuntimeSetting

    def get_wrapper(self):
        return RuntimeSettingWrapper(model=self.get_model())

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='command')
        parser_list = subparsers.add_parser('list', cmd=self, help='list all')


    def handle(self, command, key=None, value=None, *args, **options):
        if command == "list":
            wrapped = self.get_wrapper()
            for key, value in sorted(wrapped):
                self.stdout.write(
                    self.style.HTTP_REDIRECT(key),
                )
                data = sorted(value.items())
                maxlength = max(len(x[0]) for x in data)
                tmpl = "{{k: <{}}}".format(maxlength)
                for form_key, form_value in data:
                    key = tmpl.format(k=form_key)
                    self.stdout.write("{k}: {v!r}".format(k=self.style.HTTP_INFO(key), v=form_value))
                self.stdout.write("\n")
