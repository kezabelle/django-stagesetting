# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from django.conf.urls import url, include
from django.contrib import admin
from stagesetting import urls as stagesetting_urls

urlpatterns = [
   url(r'^', include(stagesetting_urls)),
   url(r'^test_admin/', include(admin.site.urls)),
]
