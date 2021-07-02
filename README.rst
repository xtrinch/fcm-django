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
Note: the current demo project uses fcm-django < v1

Unsure how to use this project? Check out the demo at:
https://github.com/xtrinch/fcm-django-web-demo

Setup
-----
You can install the library directly from pypi using pip:

    $ pip install fcm-django


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
    Message(notification=Notification(title="title", body="text", image="url"))

Data message:

.. code-block:: python

    from firebase_admin.messaging import Message
    Message(
        data={
            "Nick" : "Mario",
            "body" : "great match!",
            "Room" : "PortugalVSDenmark"
       }
    )

As in the following example, you can send either a notification, a data message, or both.
You can also customize the Android, iOS, and Web configuration along with additional
FCM conditions. Visit ``firebase_admin.messaging.Message`` to learn more about those
configurations.

Sending messages
----------------

For a list of possible parameters see https://firebase.google.com/docs/cloud-messaging/http-server-ref#notification-payload-support

.. code-block:: python

    from firebase_admin.messaging import Message
    from fcm_django.models import FCMDevice

    device = FCMDevice.objects.all().first()
    # send_message parameters include: message, dry_run, app
    device.send_message(Message(data={...}))

Sending messages in bulk
------------------------

.. code-block:: python

    from firebase_admin.messaging import Message
    from fcm_django.models import FCMDevice

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
    # Unsubscribing
    FCMDevice.objects.all().handle_topic_subscription(False, topic="TOPIC NAME"))
    device = FCMDevice.objects.all().first()
    device.handle_topic_subscription(False, topic="TOPIC NAME"))

Sending messages to topic
-------------------------

.. code-block:: python

    from firebase_admin.messaging import Message
    from fcm_django.models import FCMDevice

    FCMDevice.objects.all().send_message(Message(data={...}, topic="TOPIC NAME"))
    device = FCMDevice.objects.all().first()
    device.send_message(Message(data={...}, topic="TOPIC NAME"))

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

    urlpatterns = patterns('',
        # Only allow creation of devices by authenticated users
        url(r'^devices?$', FCMDeviceAuthorizedViewSet.as_view({'post': 'create'}), name='create_fcm_device'),
        # ...
    )

Python 3 support
----------------
``fcm-django`` is fully compatible with Python 3.6+

Django version compatibility
----------------------------
Compatible with Django versions 2.2+. For lower django versions, use version ``fcm-django < 1``.

Acknowledgements
----------------
Library relies on pyFCM for sending notifications, for more info about all the possible fields, see:
https://github.com/olucurious/PyFCM

Need help, have any questions, suggestions?
-------------------------------------------
Submit an issue/PR on this project. Please do not send me emails, as then the community has no chance to see your questions / provide answers.

Contributing
------------

To setup the development environment, simply do `pip install -r requirements.txt`
