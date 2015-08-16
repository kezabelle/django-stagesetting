# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from django.conf.urls import url, include
from django.contrib import admin
from django.template.response import TemplateResponse
from rest_framework.routers import DefaultRouter
from stagesetting import urls as stagesetting_urls
from stagesetting.drf import SettingsViewSet


api = DefaultRouter(trailing_slash=True)
api.register(r'settings', SettingsViewSet)



def homepage(request):
    return TemplateResponse(request, template="example_usage.html", context={})


urlpatterns = [
   # url(r'docs/', include('rest_framework_swagger.urls')),
   url(r'api/', include(api.urls)),
   url(r'^$', homepage),
   url(r'^stagesetting/', include(stagesetting_urls)),
   url(r'^test_admin/', include(admin.site.urls)),
]
