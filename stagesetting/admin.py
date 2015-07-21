# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.core.urlresolvers import reverse
from .models import RuntimeSetting
from stagesetting.utils import registry
from .views import CreateSetting
from .views import UpdateSetting
from .views import DeleteSetting


class RuntimeSettingAdmin(ModelAdmin):
    list_per_page = 500
    list_max_show_all = 500
    list_display = ['key', 'created', 'modified', 'has_changed']
    list_display_links = ['key']
    actions = None

    def add_view(self, request, **kwargs):
        return CreateSetting.as_view(
            admin=True, template_name='admin/stagesetting/add_form.html',
            success_url_name='admin:stagesetting_runtimesetting_change')(request=request)

    def change_view(self, request, object_id, **kwargs):
        return UpdateSetting.as_view(
            admin=True, template_name='admin/stagesetting/change_form.html',
            success_url=reverse('admin:stagesetting_runtimesetting_changelist'))(request=request, pk=object_id)

    def delete_view(self, request, object_id, **kwargs):
        return DeleteSetting.as_view(
            admin=True, template_name='admin/delete_confirmation.html',
            success_url=reverse('admin:stagesetting_runtimesetting_changelist'))(request=request, pk=object_id)
admin.site.register(RuntimeSetting, RuntimeSettingAdmin)
