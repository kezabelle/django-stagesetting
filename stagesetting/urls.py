# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from django.conf.urls import url
from .views import create_view
from .views import update_view
from .views import delete_view
from .views import list_view

stagesetting_create = url(regex=r'^add/$',
                     view=create_view,
                     name='stagesetting_create',
                     kwargs={})

stagesetting_update = url(regex=r'^(?P<pk>\d+)/update/$',
                     view=update_view,
                     name='stagesetting_update',
                     kwargs={})

stagesetting_delete = url(regex=r'^(?P<pk>\d+)/delete/$',
                     view=delete_view,
                     name='stagesetting_delete',
                     kwargs={})

stagesetting_list = url(regex=r'^$',
                    view=list_view,
                    name='stagesetting_list',
                    kwargs={})

urlpatterns = [
    stagesetting_create,
    stagesetting_update,
    stagesetting_delete,
    stagesetting_list,
]
