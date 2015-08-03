#! /usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from datetime import datetime, date, time
import os
import sys
from django.conf import settings

DEBUG = os.environ.get('DEBUG', 'on') == 'on'
SECRET_KEY = os.environ.get('SECRET_KEY', 'TESTTESTTESTTESTTESTTESTTESTTEST')
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,testserver').split(',')

BASE_DIR = os.path.abspath(os.path.dirname(os.path.abspath(__file__)))

def user():
    from django.contrib.auth import get_user_model
    return get_user_model()()

def user_qs():
    from django.contrib.auth import get_user_model
    return get_user_model().objects.all()

settings.configure(
    DEBUG=DEBUG,
    SECRET_KEY=SECRET_KEY,
    ALLOWED_HOSTS=ALLOWED_HOSTS,
    SITE_ID=1,
    ROOT_URLCONF='test_urls',  # or __name__ to use local ones ...
    MIDDLEWARE_CLASSES=(
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.middleware.clickjacking.XFrameOptionsMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'stagesetting.middleware.ApplyRuntimeSettings',
    ),
    DATABASES={
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    },
    TEMPLATE_CONTEXT_PROCESSORS=(
        'django.contrib.messages.context_processors.messages',
        'django.contrib.auth.context_processors.auth',
        'stagesetting.context_processors.runtime_settings',
    ),
    INSTALLED_APPS=(
        'django.contrib.contenttypes',
        'django.contrib.messages',
        'django.contrib.sites',
        'django.contrib.auth',
        'django.contrib.staticfiles',
        'django.contrib.admin',
        'stagesetting',
        'test_app',
        'debug_toolbar',
    ),
    STATIC_ROOT=os.path.join(BASE_DIR, 'test_collectstatic'),
    STATIC_URL='/__static__/',
    MESSAGE_STORAGE='django.contrib.messages.storage.cookie.CookieStorage',
    SESSION_ENGINE='django.contrib.sessions.backends.signed_cookies',
    SESSION_COOKIE_HTTPONLY=True,
    STAGESETTINGS={
        'LIST_PER_PAGE': ['test_app.forms.ListPerPageForm'],
        'DATES': ['test_app.forms.DateForm', {'start': date.today()}],
        'DATETIMES': ['test_app.forms.DatetimeForm'],
        'USERS': ['test_app.forms.ModelChoicesForm'],
        'GENERATED':  {
            'int': 1,
            'email': 'a@b.com',
            'url': 'https://news.bbc.co.uk/',
            'model': user,
            'queryset': user_qs,
            'datetime': datetime.today(),
            'date': date.today(),
            'time': time(4, 23),
            'boolean': False,
            'nullboolean': None,
            'ip': '127.0.0.1',
            'slug': 'test-test',
            'text': 'char field',
        }
    },
)

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()


if __name__ == "__main__":
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
