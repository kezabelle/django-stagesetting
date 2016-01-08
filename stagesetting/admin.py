# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from django.contrib.admin import ModelAdmin
from django.contrib.admin.templatetags.admin_urls import admin_urlname
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from .forms import CreateSettingForm
from .views import CreateSetting
from .views import UpdateSetting
from .views import DeleteSetting


class RuntimeSettingAdmin(ModelAdmin):
    list_per_page = 500
    list_max_show_all = 500
    list_display = ['pretty_key', 'created', 'modified', 'has_changed', 'history_link']
    list_display_links = ['pretty_key']
    actions = None

    def history_link(self, obj):
        url = admin_urlname(obj._meta, 'history')
        url = reverse(url, args=(obj.pk,))  # noqa
        return '<a href="%(url)s" class="historylink">%(label)s</a>' % {
            'url': url, 'label': _("History")
        }
    history_link.short_description = _(" ")
    history_link.allow_tags = True

    def add_view(self, request, **kwargs):
        url = admin_urlname(self.model._meta, 'change')
        return CreateSetting.as_view(model=self.model, form_class=CreateSettingForm,
            admin=self, template_name='admin/stagesetting/add_form.html',
            success_url_name=url)(request=request)

    def change_view(self, request, object_id, **kwargs):
        url = admin_urlname(self.model._meta, 'changelist')
        return UpdateSetting.as_view(model=self.model,
            admin=self, template_name='admin/stagesetting/change_form.html',
            success_url=reverse(url))(request=request, pk=object_id)

    def delete_view(self, request, object_id, **kwargs):
        url = admin_urlname(self.model._meta, 'changelist')
        return DeleteSetting.as_view(queryset=self.model.objects.all(),
            admin=self, template_name='admin/delete_confirmation.html',
            success_url=reverse(url))(request=request, pk=object_id)
