fcm-django
=========================


.. image:: https://badge.fury.io/py/fcm-django.svg
    :target: https://badge.fury.io/py/fcm-django


Django app for Firebase Cloud Messaging. Used as an unified platform for sending push notifications to mobile devices & browsers (android / ios / chrome / firefox / ...).

Supports Firebase Cloud Messaging HTTP v1 API. If you're looking for the legacy API, use ``fcm-django<1``!

FCMDevice model fields
 - *registration_id* (required - is FCM token)
 - *name* (optional)
 - *active* (default: true)
 - *user* (optional)
 - *device_id* (optional - can be used to uniquely identify devices)
 - *type* ('android', 'web', 'ios')

Functionality:
 - all necessary migrations
 - model admins for django admin
 - admin actions for testing single and bulk notification sending
 - automatic device pruning: devices to which notifications fail to send are marked as inactive
 - devices marked as inactive will not be sent notifications
 - Django rest framework viewsets

Demo javascript client project
------------------------------
Unsure how to use this project? Check out the demo at:
https://github.com/xtrinch/fcm-django-web-demo

Migration to v1.0
-----------------

We've replaced Python package ``pyfcm`` for Firebase's own package ``firebase-admin``.
Thus, we no longer use an API key. Instead, you'll need an environment variable
``GOOGLE_APPLICATION_CREDENTIALS`` which is a path pointing to your JSON-file stored
credentials. To learn more or view other options to input credentials, visit the
`Google Cloud docs <https://cloud.google.com/docs/authentication/getting-started>`_.

Finally, in your ``settings.py`` (or whatever imported file), add:

.. code-block:: python

    from firebase_admin import initialize_app
    FIREBASE_APP = initialize_app()
    # Or just
    initialize_app()

The API for sending messages is now under the ``firebase-admin`` package; hence,
we removed the methods ``send_data_message`` from the QuerySet and class instance
methods. Instead, everything is under a single method: ``send_message``

.. code-block:: python

    from firebase_admin.messaging import Message, Notification
    FCMDevice.objects.send_message(Message(data=dict()))
    # Note: You can also combine the data and notification kwarg
    FCMDevice.objects.send_message(
        Message(notification=Notification(title="title", body="body", image="image_url"))
    )
    device = FCMDevice.objects.first()
    device.send_message(Message(...))

Additionally, we've added Firebase's new Topic API, allowing for easier sending
of bulk messages.

.. code-block:: python

    from firebase_admin.messaging import Message, Notification
    topic = "A topic"
    FCMDevice.objects.handle_subscription(True, topic)
    FCMDevice.send_topic_message(Message(data={...}), "TOPIC NAME")

There are two additional parameters to both methods:
``skip_registration_id_lookup`` and ``additional_registration_ids``.
Visit `Sending Messages <https://github.com/xtrinch/fcm-django#sending-messages>`_ to learn more.

Note: ``registration_ids`` is actually incorrect terminology as it
should actually be called ``registration tokens``. However, to be
consistent with ``django-push-notifications``, we've refrained from
switching to stay backwards compatible in the docs and with the
sister package.

Setup
-----
You can install the library directly from pypi using pip:

.. code-block:: console

    pip install fcm-django


Edit your settings.py file:

.. code-block:: python

    from firebase_admin import initialize_app

    INSTALLED_APPS = (
        ...
        "fcm_django"
        ...
    )

    # Optional ONLY IF you have initialized a firebase app already:
    # Visit https://firebase.google.com/docs/admin/setup/#python
    # for more options for the following:
    # Store an environment variable called GOOGLE_APPLICATION_CREDENTIALS
    # which is a path that point to a json file with your credentials.
    # Additional arguments are available: credentials, options, name
    FIREBASE_APP = initialize_app()
    # To learn more, visit the docs here:
    # https://cloud.google.com/docs/authentication/getting-started>

    FCM_DJANGO_SETTINGS = {
         # an instance of firebase_admin.App to be used as default for all fcm-django requests
         # default: None (the default Firebase app)
        "DEFAULT_FIREBASE_APP": None,
         # default: _('FCM Django')
        "APP_VERBOSE_NAME": "[string for AppConfig's verbose_name]",
         # true if you want to have only one active device per registered user at a time
         # default: False
        "ONE_DEVICE_PER_USER": True/False,
         # devices to which notifications cannot be sent,
         # are deleted upon receiving error response from FCM
         # default: False
        "DELETE_INACTIVE_DEVICES": True/False,
    }

Native Django migrations are in use. ``manage.py migrate`` will install and migrate all models.

Messages
--------

You can read more about different types of messages here_.

.. _here: https://firebase.google.com/docs/cloud-messaging/concept-options

In short, there are two types: notifications and data messages.

Notification:

.. code-block:: python

    from firebase_admin.messaging import Message, Notification
    Message(
        notification=Notification(title="title", body="text", image="url"),
        topic="Optional topic parameter: Whatever you want",
    )

Data message:

.. code-block:: python

    from firebase_admin.messaging import Message
    Message(
        data={
            "Nick" : "Mario",
            "body" : "great match!",
            "Room" : "PortugalVSDenmark"
       },
       topic="Optional topic parameter: Whatever you want",
    )

As in the following example, you can send either a notification, a data message, or both.
You can also customize the Android, iOS, and Web configuration along with additional
FCM conditions. Visit ``firebase_admin.messaging.Message`` to learn more about those
configurations.

Sending messages
----------------

Additional parameters are ``additional_registration_ids`` and
``skip_registration_id_lookup``. View the "Additional Parameters"
section for more information.

.. code-block:: python

    from firebase_admin.messaging import Message
    from fcm_django.models import FCMDevice

    # You can still use .filter() or any methods that return QuerySet (from the chain)
    device = FCMDevice.objects.all().first()
    # send_message parameters include: message, dry_run, app
    device.send_message(Message(data={...}))

Sending messages in bulk
------------------------

.. code-block:: python

    from firebase_admin.messaging import Message
    from fcm_django.models import FCMDevice

    # You can still use .filter() or any methods that return QuerySet (from the chain)
    devices = FCMDevice.objects.all()
    devices.send_message(Message(data={...}))
    # Or (send_message parameters include: messages, dry_run, app)
    FCMDevice.objects.send_message(Message(...))

    Sending messages raises all the errors that ``firebase-admin`` raises, so make sure
they are caught and dealt with in your application code:

- ``FirebaseError`` – If an error occurs while sending the message to the FCM service.
- ``ValueError`` – If the input arguments are invalid.

For more info, see https://firebase.google.com/docs/reference/admin/python/firebase_admin.messaging#firebase_admin.messaging.BatchResponse

Subscribing or Unsubscribing Users to topic
-------------------------------------------

.. code-block:: python

    from fcm_django.models import FCMDevice

    # Subscribing
    FCMDevice.objects.all().handle_topic_subscription(True, topic="TOPIC NAME"))
    device = FCMDevice.objects.all().first()
    device.handle_topic_subscription(True, topic="TOPIC NAME"))

    # Finally you can send a message to that topic
    from firebase_admin.messaging import Message
    message = Message(..., topic="A topic")
    # You can still use .filter() or any methods that return QuerySet (from the chain)
    FCMDevice.objects.send_message(message)

    # Unsubscribing
    FCMDevice.objects.all().handle_topic_subscription(False, topic="TOPIC NAME"))
    device = FCMDevice.objects.all().first()
    device.handle_topic_subscription(False, topic="TOPIC NAME"))

Sending messages to topic
-------------------------

.. code-block:: python

    from fcm_django.models import FCMDevice

    FCMDevice.send_topic_message(Message(data={...}), "TOPIC NAME")

Additional Parameters
---------------------

You can add additional_registration_ids (Sequence) for manually
sending registration IDs. It will append these IDs to the queryset
lookup's returned registration IDs.

You can also add skip_registration_id_lookup (bool) to skip database
lookup that goes along with your query.

.. code-block:: python

    from firebase_admin.messaging import Message
    from fcm_django.models import FCMDevice
    FCMDevice.objects.send_message(Message(...), False, ["registration_ids"])

Using multiple FCM apps
-----------------------

By default the message will be sent using the default FCM ``firebase_admin.App`` (we initialized this in our settings),
or the one specified with the ``DEFAULT_FIREBASE_APP`` setting.

This default can be overridden by specifying an app when calling send_message. This can be used to send messages using different firebase projects.

.. code-block:: python

    from firebase_app import App
    from firebase_app.messaging import Notification
    from fcm_django.models import FCMDevice

    device = FCMDevice.objects.all().first()
    device.send_message(notification=Notification(...), app=App(...))

Setting a default Firebase app for FCM
--------------------------------------

If you want to use a specific Firebase app for all fcm-django requests, you can create an instance of
``firebase_admin.App`` and pass it to fcm-django with the ``DEFAULT_FIREBASE_APP`` setting.

The ``DEFAULT_FIREBASE_APP`` will be used for all send / subscribe / unsubscribe requests, include ``FCMDevice``'s
admin actions.

In your ``settings.py``:

.. code-block:: python

    from firebase_admin import initialize_app, credentials
    from google.auth import load_credentials_from_file
    from google.oauth2.service_account import Credentials

    # create a custom Credentials class to load a non-default google service account JSON
    class CustomFirebaseCredentials(credentials.ApplicationDefault):
        def __init__(self, account_file_path: str):
            super().__init__()
            self._account_file_path = account_file_path

        def _load_credential(self):
            if not self._g_credential:
                self._g_credential, self._project_id = load_credentials_from_file(self._account_file_path,
                                                                                  scopes=credentials._scopes)

    # init default firebase app
    # this loads the default google service account with GOOGLE_APPLICATION_CREDENTIALS env variable
    FIREBASE_APP = initialize_app()

    # init second firebase app for fcm-django
    # the environment variable contains a path to the custom google service account JSON
    custom_credentials = CustomFirebaseCredentials(os.getenv('CUSTOM_GOOGLE_APPLICATION_CREDENTIALS'))
    FIREBASE_MESSAGING_APP = initialize_app(custom_credentials, name='messaging')

    FCM_DJANGO_SETTINGS = {
        "DEFAULT_FIREBASE_APP": FIREBASE_MESSAGING_APP,
        # [...] your other settings
    }


Django REST Framework (DRF) support
-----------------------------------

Viewsets come in two different varieties:

- ``FCMDeviceViewSet``

    - Permissions as specified in settings (``AllowAny`` by default, which is not recommended)
    - A device may be registered without associating it with a user
    - Will not allow duplicate registration_id's

- ``FCMDeviceAuthorizedViewSet``

    - Permissions are ``IsAuthenticated`` and custom permission ``IsOwner``, which will only allow the ``request.user`` to get and update devices that belong to that user
    - Requires a user to be authenticated, so all devices will be associated with a user
    - Will update the device on duplicate registration id

Routes can be added one of two ways:

- `Routers`_ (include all views)

.. _Routers: http://www.django-rest-framework.org/tutorial/6-viewsets-and-routers#using-routers

.. code-block:: python

    from fcm_django.api.rest_framework import FCMDeviceAuthorizedViewSet

    from rest_framework.routers import DefaultRouter

    router = DefaultRouter()

    router.register('devices', FCMDeviceAuthorizedViewSet)

    urlpatterns = [
        # URLs will show up at <api_root>/devices
        # DRF browsable API which lists all available endpoints
        path('', include(router.urls)),
        # ...
    ]

- Using `as_view`_ (specify which views to include)

.. _as_view: http://www.django-rest-framework.org/tutorial/6-viewsets-and-routers#binding-viewsets-to-urls-explicitly

.. code-block:: python

    from fcm_django.api.rest_framework import FCMDeviceAuthorizedViewSet

    urlpatterns = [
        # Only allow creation of devices by authenticated users
        path('devices', FCMDeviceAuthorizedViewSet.as_view({'post': 'create'}), name='create_fcm_device'),
        # ...
    ]

Update of device with duplicate registration ID
-----------------------------------------------

Tokens are device specific, so if the user e.g. logs out of their account on your device, and another user
logins on the same device, you do not wish the old user to receive messages while logged out.

Via DRF, any creation of device with an already existing registration ID will be transformed into an update.
If done manually, you are responsible for deleting the old device entry.

Using custom FCMDevice model
----------------------------

If there's a need to store additional information or change type of fields in the FCMDevice model.
You could simple override this model. To do this, inherit your model from the AbstractFCMDevice class.

In your ``your_app/models.py``:

.. code-block:: python

    import uuid
    from django.db import models
    from fcm_django.models import AbstractFCMDevice


    class CustomDevice(AbstractFCMDevice):
        # fields could be overwritten
        id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
        # could be added new fields
        updated_at = models.DateTimeField(auto_now=True)

In your ``settings.py``:

.. code-block:: python

    FCM_DJANGO_FCMDEVICE_MODEL = "your_app.CustomDevice"


In the DB will be two tables one that was created by this package and other your own. New data will appears only in your own table.
If you don't want default table appears in the DB then you should remove ``fcm_django`` out of ``INSTALLED_APPS`` at  ``settings.py``:

.. code-block:: python

    INSTALLED_APPS = (
        ...
        # "fcm_django", - remove this line
        "your_app", # your app should appears
        ...
    )

After setup your own ``Model`` don't forget to create ``migrations`` for your app and call ``migrate`` command.

After removing ``"fcm_django"`` out of ``INSTALLED_APPS``. You will need to re-register the Device in order to see it in the admin panel.
This can be accomplished as follows at ``your_app/admin.py``:

.. code-block:: python

    from django.contrib import admin

    from fcm_django.admin import DeviceAdmin
    from your_app.models import CustomDevice


    admin.site.unregister(CustomDevice)
    admin.site.register(CustomDevice, DeviceAdmin)


If you choose to move forward with swapped models then:

1. On existed project you have to keep in mind there are required manual work to move data from one table to anther.
2. If there's any tables with FK to swapped model then you have to deal with them on your own.

Note: This functionality based on `Swapper <https://pypi.org/project/swapper/>`_ that based on functionality
that allow to use a `custom User model <https://docs.djangoproject.com/en/4.2/topics/auth/customizing/#substituting-a-custom-user-model>`_.
So this functionality have the same limitations.
The most is important limitation it is that is difficult to start out with a default (non-swapped) model
and then later to switch to a swapped implementation without doing some migration hacking.

MySQL compatibility
-------------------
MySQL has a limit for indices and therefore the `registration_id` field cannot be made unique in MySQL.
We detect the database backend and remove the unique constraint for MySQL in the migration files. However,
to ensure that the constraint is removed from the actual model you have to add the following to your settings
to be able to run your django tests with MySQL and without running all migrations:

.. code-block:: python

    FCM_DJANGO_SETTINGS = {
        "MYSQL_COMPATIBILITY": True,
        # [...] your other settings
    }

As an alternative, you can use a custom model (see above) and either remove the unique constraint manually
or use a length limited CharField for the `registration_id` field. There are no guarantees on the max length of
FCM tokens, but in practice they are less than 200 characters long. Therefore, a CharField with a length of 600
should be sufficient and you can make it unique and index it even with MySQL:

.. code-block:: python

    from fcm_django.models import AbstractFCMDevice, FCMDevice as OriginalFCMDevice


    class CustomFCMDevice(AbstractFCMDevice):
        registration_id = models.CharField(
            verbose_name="Registration token",
            unique=True,
            max_length=600,  # https://stackoverflow.com/a/64902685 better to be safe than sorry
        )

        class Meta(OriginalFCMDevice.Meta):
            pass

Python 3 support
----------------
- ``fcm-django`` is fully compatible with Python 3.7+
- for Python 3.6, use ``fcm-django < 2.0.0`` , because `firebase-admin with version 6 drop support of Python 3.6 <https://firebase.google.com/support/release-notes/admin/python#version_600_-_06_october_2022>`_

Django version compatibility
----------------------------
Compatible with Django versions 3.0+.
For Django version 2.2, use version ``fcm-django < 1.0.13``.
For lower django versions, use version ``fcm-django < 1.0.0``.

Acknowledgements
----------------
Library relies on firebase-admin-sdk for sending notifications, for more info about all the possible fields, see:
https://github.com/firebase/firebase-admin-python

Migration from v0 to v1 was done by `Andrew-Chen-Wang <https://github.com/Andrew-Chen-Wang>`_

Need help, have any questions, suggestions?
-------------------------------------------
Submit an issue/PR on this project. Please do not send me emails, as then the community has no chance to see your questions / provide answers.

Contributing
------------

To setup the development environment, simply do ``pip install -r requirements_dev.txt``
To manually run the pre-commit hook, run `pre-commit run --all-files`.

Because there's possibility to use swapped models therefore tests contains two config files:

1. with default settings and non swapped models ``settings/default.py``
2. and with overwritten settings only that required by swapper - ``settings/swap.py``

To run tests locally you could use ``pytest``, and if you need to check migrations on different DB then you have to specify environment variable ``DATABASE_URL`` ie

.. code-block:: console

    export DATABASE_URL=postgres://postgres:postgres@127.0.0.1:5432/postgres
    export DJANGO_SETTINGS_MODULE=tests.settings.default
    # or export DJANGO_SETTINGS_MODULE=tests.settings.swap
    pytest
