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

    from firebase_admin import firebase_init
    FIREBASE_APP = initialize_app()
    # Or just
    initialize_app()

The API for sending messages is now under the ``firebase-admin`` package; hence,
we removed the methods ``send_data_message`` from the QuerySet and class instance
methods. Instead, everything is under a single method: ``send_message``

.. code-block:: python

    from fcm_django.messaging import Message, Notification
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

    from fcm_django.messaging import Message, Notification
    topic = "A topic"
    FCMDevice.objects.handle_subscription(True, topic)
    message = Message(..., topic=topic)
    FCMDevice.objects.filter(is_cool=True).send_message(message)

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

.. code-block::

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
         # default: _('FCM Django')
        "APP_VERBOSE_NAME": "[string for AppConfig's verbose_name]",
         # true if you want to have only one active device per registered user at a time
         # default: False
        "ONE_DEVICE_PER_USER": True/False,
         # devices to which notifications cannot be sent,
         # are deleted upon receiving error response from FCM
         # default: False
        "DELETE_INACTIVE_DEVICES": True/False,
        # Transform create of an existing Device (based on registration id) into
		    # an update. See the section
        # "Update of device with duplicate registration ID" for more details.
        "UPDATE_ON_DUPLICATE_REG_ID": True/False,
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

    from firebase_admin.messaging import Message
    from fcm_django.models import FCMDevice

    # You can still use .filter() or any methods that return QuerySet (from the chain)
    FCMDevice.objects.all().send_message(Message(data={...}, topic="TOPIC NAME"))
    device = FCMDevice.objects.all().first()
    device.send_message(Message(data={...}, topic="TOPIC NAME"))

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

By default the message will be sent using the default FCM ``firebase_admin.App`` (we initialized this in our settings). This default can be overridden by specifying an app when calling send_message. This can be used to send messages using different firebase projects.

.. code-block:: python

    from firebase_app import App
    from firebase_app.messaging import Notification
    from fcm_django.models import FCMDevice

    device = FCMDevice.objects.all().first()
    device.send_message(notification=Notification(...), app=App(...))

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
    - Will allow duplicate registration_id's for different users, so you are responsible for cleanup (if that is generally perceived as undesired behaviour or if the package itself should be doing the cleanup, open an issue or email me)

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

The DRF viewset enforce the uniqueness of the registration ID. In same use case it
may cause an issue: If an already registered mobile device changes its user, then
it will fail to register because the registration ID already exist.

When option ``UPDATE_ON_DUPLICATE_REG_ID`` is set to True, then any creation of
device with an already existing registration ID will be transformed into an update.

The ``UPDATE_ON_DUPLICATE_REG_ID`` only works with DRF.

Python 3 support
----------------
``fcm-django`` is fully compatible with Python 3.6+

Django version compatibility
----------------------------
Compatible with Django versions 2.2+. For lower django versions, use version ``fcm-django < 1``.

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

To setup the development environment, simply do ``pip install -r requirements.txt``
To manually run the pre-commit hook, run `pre-commit run --all-files`.
