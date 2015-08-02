django-stagesetting 0.2.0
=========================

An application for managing site configuration through normal `Django`_ forms,
and thus through the `admin site`_.

Yay, I've made another app to abuse `contrib.admin`_.

.. |travis_stable| image:: https://travis-ci.org/kezabelle/django-jackfrost.svg?branch=0.2.0
  :target: https://travis-ci.org/kezabelle/django-jackfrost

.. |travis_master| image:: https://travis-ci.org/kezabelle/django-stagesetting.svg?branch=master
  :target: https://travis-ci.org/kezabelle/django-stagesetting

==============  ======
Release         Status
==============  ======
stable (0.2.0)  |travis_stable|
master          |travis_master|
==============  ======

Installation
------------

Add the package to your ``INSTALLED_APPS`` in your settings::

    INSTALLED_APPS = (
        # ...
        'stagesetting',
        # ...
    )

Add a ``STAGESETTINGS`` dictionary to your project's settings::

    STAGESETTINGS = {
        'SETTING_NAME': ['path.to.Form.Class'],
        'ANOTHER_SETTING_NAME': ['path.to.Form.Class', {
            'initial': 'data',
            'is': 'optionl',
        }],
    }

The setting collection name is the dictionary key, so must be unique.
The dictionary value should be a list or tuple containing:

  - A string which represents the dotted python path to a `Form`_ class
  - Optionally, a second value (a dictionary mapping to the `Form`_ data) may be
    provided, which serves as the default value, and is used when creating items
    into the database for the first time.

A simple configuration form might look like::

    from django.core.exceptions import ValidationError
    from django.forms import Form, DateField

    class DateForm(Form):
        start = DateField()
        end = DateField()

        def clean(self):
            cd = self.cleaned_data
            if 'start' in cd and 'end' in cd and cd['start'] > cd['end']:
                raise ValidationError("Start date cannot be after end date")
            return cd

As you can see, it really is just a normal `Form`_. Internally, this form's
``cleaned_data`` will be converted into `JSON`_ before being saved to the
database.
It will get re-converted to proper Python values when pulled out
of the database, by going through the given `Form`_ class's validation again,
including converting to rich values like model instances.

Usage in code
-------------

The best way to access the settings in your views is to include
``stagesetting.middleware.ApplyRuntimeSettings`` in your ``MIDDLEWARE_CLASSES``
which will ensure there is a ``request.stagesettings`` variable which can be
used like so::

    def myview(request):
        how_many_form_data = request.stagesetting.LIST_PER_PAGE
        allow_empty_form_data = request.stagesetting['ALLOW_EMPTY']

each setting will be a dictionary of the `Form`_ values, either the default ones
or those changed in the database.

Usage in templates
------------------

If you've already got ``request`` in your template, obviously you can continue
to use ``request.stagesettings`` if the middleware is wired up.

If you don't have request, or you're not using the middleware,
``stagesetting.context_processors.runtime_settings`` provides a ``STAGESETTING``
template variable which contains the exact same data.

Usage outside of a request
--------------------------

If you don't have the middleware, or are in a part of the code which doesn't
have a ``request``, you can use the wrapper object directly::

    from stagesetting.models import RuntimeSettingWrapper
    def my_signal_handler(sender, instance, **kwargs):
        live_settings = RuntimeSettingWrapper()
        data = live_settings.LIST_PER_PAGE

Try to keep a single ``RuntimeSettingWrapper`` around for as long as possible,
rather than creating a new instance everywhere, as the object must fetch
the available settings from the database the first time it needs them. It
caches them for it's lifetime thereafter.


.. _Django: https://docs.djangoproject.com/en/stable/
.. _admin site: https://docs.djangoproject.com/en/stable/ref/contrib/admin/
.. _contrib.admin: https://docs.djangoproject.com/en/stable/ref/contrib/admin/
.. _Form: https://docs.djangoproject.com/en/stable/topics/forms/
.. _Forms: https://docs.djangoproject.com/en/stable/topics/forms/
.. _JSON: http://json.org/
.. _pip: https://pip.pypa.io/en/stable/
.. _pytest: http://pytest.org/latest/
