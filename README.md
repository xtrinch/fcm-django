django-fcm
=========================

Django app for Firebase Cloud Messaging.

Functionality:
 - FCMDevice model (fields: name, active, user, device_id, registration_id, type)
 - all necessary migrations
 - model admins for django admin
 - admin actions for testing single and bulk notification sending
 - Django rest framework viewsets

Dependencies
------------
Currently only tested with Django 1.9.8 and DRF 3.2.4

TODO: Setup
-----
TODO: You can install the library directly from pypi using pip:

	$ pip install django-fcm


Edit your settings.py file:

	INSTALLED_APPS = (
		...
		"push_notifications"
	)

	PUSH_NOTIFICATIONS_SETTINGS = {
		"FCM_SERVER_KEY": "[your api key]"
	}

Native Django migrations are in use. ``manage.py migrate`` will install and migrate all models.

Sending messages
----------------

	from push_notifications.models import FCMDevice
	device.send_message("Title", "Message")

Sending messages in bulk
------------------------

	from push_notifications.models import FCMDevice
	device.send_messages("Title", "Message")

Django REST Framework (DRF) support
-----------------------------------
Viewsets come in two different varieties:

- ``FCMDeviceViewSet``

	- Permissions as specified in settings (``AllowAny`` by default, which is not recommended)
	- A device may be registered without associating it with a user

- ``FCMDeviceAuthorizedViewSet``

	- Permissions are ``IsAuthenticated`` and custom permission ``IsOwner``, which will only allow the ``request.user`` to get and update devices that belong to that user
	- Requires a user to be authenticated, so all devices will be associated with a user

Routes can be added one of two ways:

- Routers_ (include all views)
.. _Routers: http://www.django-rest-framework.org/tutorial/6-viewsets-and-routers#using-routers


	from push_notifications.api.rest_framework import FCMDeviceAuthorizedViewSet
	from rest_framework.routers import DefaultRouter

	router = DefaultRouter()
	router.register(r'devices', FCMDeviceAuthorizedViewSet)

	urlpatterns = patterns('',
		# URLs will show up at <api_root>/devices
		url(r'^', include(router.urls)),
		# ...
	)

- Using as_view_ (specify which views to include)
.. _as_view: http://www.django-rest-framework.org/tutorial/6-viewsets-and-routers#binding-viewsets-to-urls-explicitly


	from push_notifications.api.rest_framework import FCMDeviceAuthorizedViewSet

	urlpatterns = patterns('',
		# Only allow creation of devices by authenticated users
		url(r'^devices?$', FCMDeviceAuthorizedViewSet.as_view({'post': 'create'}), name='create_fcm_device'),
		# ...
	)


Python 3 support
----------------
``django-fcm`` is fully compatible with Python 3.4 & 3.5
