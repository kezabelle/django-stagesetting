# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
import django
from django.conf import settings
import os


HERE = os.path.realpath(os.path.dirname(__file__))

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
)
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'OPTIONS': {
            'context_processors': TEMPLATE_CONTEXT_PROCESSORS,
            'loaders': TEMPLATE_LOADERS,
        },
    },
]

def pytest_configure():
    if not settings.configured:
        settings.configure(
            DATABASES={
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": ":memory:"
                    }
                },
            INSTALLED_APPS=(
                'django.contrib.sites',
                'django.contrib.sitemaps',
                'django.contrib.auth',
                'django.contrib.admin',
                'django.contrib.sessions',
                'django.contrib.contenttypes',
                'django.contrib.messages',
                'stagesetting',
            ),
            # these are the default in 1.8, so we should make sure we
            # work with those.
            MIDDLEWARE_CLASSES=(
                'django.contrib.sessions.middleware.SessionMiddleware',
                'django.middleware.common.CommonMiddleware',
                'django.middleware.csrf.CsrfViewMiddleware',
                'django.contrib.auth.middleware.AuthenticationMiddleware',
                # 'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
                'django.contrib.messages.middleware.MessageMiddleware',
                'django.middleware.clickjacking.XFrameOptionsMiddleware',
            ),
            BASE_DIR=HERE,
            SITE_ID=1,
            STATIC_URL='/__s__/',
            STATIC_ROOT=os.path.join(HERE, 'test_collectstatic'),
            MEDIA_ROOT=os.path.join(HERE, 'test_app'),
            MEDIA_URL='/__m__/',
            ROOT_URLCONF='test_urls',
            PASSWORD_HASHERS=(
                'django.contrib.auth.hashers.MD5PasswordHasher',
            ),
			TEMPLATE_CONTEXT_PROCESSORS=TEMPLATE_CONTEXT_PROCESSORS,
			TEMPLATE_LOADERS=TEMPLATE_LOADERS,
			TEMPLATES=TEMPLATES,
            SILENCED_SYSTEM_CHECKS = ['1_8.W001'],
        )
    if hasattr(django, 'setup'):
        django.setup()
