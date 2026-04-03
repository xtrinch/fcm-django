fcm-django
=========================


.. image:: https://badge.fury.io/py/fcm-django.svg
    :target: https://badge.fury.io/py/fcm-django


Django app for Firebase Cloud Messaging. Used as an unified platform for sending push notifications to mobile devices & browsers (android / ios / chrome / firefox / ...).

Supports Firebase Cloud Messaging HTTP v1 API. If you're looking for the legacy API, use ``fcm-django<1``!

Async queryset send APIs require ``firebase-admin>=6.9`` because they use
``firebase_admin.messaging.send_each_async`` directly.

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

Upgrading from pre-1.0
----------------------
If you're still migrating from the old ``pyfcm``-based releases, see
`the v1.0 migration guide <docs/pages/migrating_to_v1.rst>`_.

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
         # emit the ``device_deactivated`` signal when this library deactivates devices
         # default: False
        "EMIT_DEVICE_DEACTIVATED_SIGNAL": True/False,
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
    device.send_message(Message(data={...}), dry_run=True)

Sending messages in bulk
------------------------

.. code-block:: python

    from firebase_admin.messaging import Message
    from fcm_django.models import FCMDevice

    # You can still use .filter() or any methods that return QuerySet (from the chain)
    devices = FCMDevice.objects.all()
    devices.send_message(Message(data={...}))
    devices.send_message(Message(data={...}), dry_run=True)
    # Or (send_message parameters include: message, dry_run, app)
    FCMDevice.objects.send_message(Message(...))

Use ``dry_run=True`` to validate the payload with Firebase without actually
delivering a notification. This is useful during development and integration
testing when you want to verify message construction without sending a real
push notification to devices.

Sending messages raises all the errors that ``firebase-admin`` raises, so make sure
they are caught and dealt with in your application code:

- ``FirebaseError`` – If an error occurs while sending the message to the FCM service.
- ``ValueError`` – If the input arguments are invalid.

For more info, see https://firebase.google.com/docs/reference/admin/python/firebase_admin.messaging#firebase_admin.messaging.BatchResponse

Inspecting batch send failures
------------------------------

``send_message()`` returns a ``FirebaseResponseDict`` wrapper around Firebase's
``BatchResponse``. For batch sends, Firebase may return per-device failures in the
response instead of raising an exception for the whole call.

Useful fields on the returned object include:

- ``response.success_count``
- ``response.failure_count``
- ``response.has_failures``
- ``response.all_failed``
- ``response.failed_registration_ids``
- ``response.failed_exceptions``
- ``response.summary``

Example:

.. code-block:: python

    response = FCMDevice.objects.send_message(Message(...))

    if response.has_failures:
        print(response.failure_count)
        print(response.failed_registration_ids)
        print(response.failed_exceptions)

This is especially useful for configuration-related failures such as APNS or
credential issues, where devices may fail without being deactivated.

Device deactivation signal
--------------------------

If you want an explicit hook when ``fcm-django`` deactivates devices, enable the
setting below:

.. code-block:: python

    FCM_DJANGO_SETTINGS = {
        "EMIT_DEVICE_DEACTIVATED_SIGNAL": True,
    }

Then subscribe to ``device_deactivated``:

.. code-block:: python

    from fcm_django.signals import device_deactivated

    def on_device_deactivated(
        sender,
        registration_ids,
        device_ids,
        user_ids,
        reason,
        source,
        metadata,
        **kwargs,
    ):
        print(registration_ids)
        print(device_ids)
        print(user_ids)
        print(reason)
        print(source)
        print(metadata)

    device_deactivated.connect(on_device_deactivated)

The signal is disabled by default and is emitted for library-managed device
deactivations. Its payload includes:

- ``registration_ids``: registration tokens that were deactivated
- ``device_ids``: matching device primary keys
- ``user_ids``: matching user primary keys, excluding devices without a user
- ``reason``: the deactivation reason
- ``source``: the library call site that triggered it
- ``metadata``: extra context such as ``failed_exceptions``

Current ``reason`` values include:

- ``firebase_error``
- ``one_device_per_user``
- ``duplicate_registration_id``
- ``manual_disable``

Current ``source`` values include:

- ``send_message``
- ``perform_create``
- ``perform_update``
- ``serializer_create``
- ``serializer_update``
- ``admin_action``

Sending personalized messages in bulk
-------------------------------------

Use ``send_bulk_personalized_messages`` when each device should receive a different
title or body while still being sent in Firebase batches.

.. code-block:: python

    from fcm_django.models import FCMDevice

    FCMDevice.objects.send_bulk_personalized_messages(
        title_template="Hello {name}",
        body_template="You have {count} new messages",
        message_data={
            "token-1": {"name": "Alice", "count": 3},
            "token-2": {"name": "Bob", "count": 7},
        },
        data_fields={"kind": "digest"},
    )

``message_data`` is keyed by registration ID. Missing template variables are left
unchanged in the rendered message.

Async queryset batch sending
----------------------------

If you are calling fcm-django from an async Django view or other async context,
use the queryset batch APIs with their async counterparts:

.. code-block:: python

    from firebase_admin.messaging import Message, Notification
    from fcm_django.models import FCMDevice

    await FCMDevice.objects.filter(user=request.user).asend_message(
        Message(notification=Notification(title="Hi", body="Async batch send")),
    )

    await FCMDevice.objects.asend_bulk_personalized_messages(
        title_template="Hello {name}",
        body_template="You have {count} updates",
        message_data={"token-1": {"name": "Alice", "count": 3}},
    )

These methods mirror ``send_message`` and ``send_bulk_personalized_messages`` on
``FCMDeviceQuerySet`` and are intended for batch queryset operations.

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
        # Detail routes must include the lookup field used by the viewset
        path(
            'devices/<str:registration_id>',
            FCMDeviceAuthorizedViewSet.as_view({'delete': 'destroy'}),
            name='delete_fcm_device',
        ),
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
If you need to customize the device model, see
`Using custom FCMDevice model <docs/pages/custom_fcmdevice_model.rst>`_.

Python 3 support
----------------
- ``fcm-django`` is fully compatible with Python 3.10+
- Python 3.9 support was dropped because Python 3.9 reached end-of-life.
- for Python 3.6, use ``fcm-django < 2.0.0`` , because `firebase-admin with version 6 drop support of Python 3.6 <https://firebase.google.com/support/release-notes/admin/python#version_600_-_06_october_2022>`_
- for Python 3.7 + 3.8, use ``fcm-django <= 2.2.1`` 

Django version compatibility
----------------------------
Compatible with Django versions 4.2+.
For Django version 2.2, use version ``fcm-django < 1.0.13``.
For lower django versions, use version ``fcm-django < 1.0.0``.

Need help, have any questions, suggestions?
-------------------------------------------
Submit an issue/PR on this project. Please do not send me emails, as then the community has no chance to see your questions / provide answers.

Contributing
------------

To setup the development environment:
  - create virtual environment with `python3 -m venv env`
  - activate virtual environment with `source env/bin/activate` or `.\env\Scripts\activate.ps1` for Windows' Powershell  
  - run ``pip install -r requirements_dev.txt``

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

Packaging for PyPi

- run `source env/bin/activate`
- run `rm -rf dist/`
- run `python3 -m build`
- run `twine upload dist/*`

Acknowledgements
----------------
Library relies on firebase-admin-sdk for sending notifications, for more info about all the possible fields, see:
https://github.com/firebase/firebase-admin-python

Migration from v0 to v1 was done by `Andrew-Chen-Wang <https://github.com/Andrew-Chen-Wang>`_
