fcm-django
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

Setup
-----
You can install the library directly from pypi using pip:

	$ pip install fcm-django


Edit your settings.py file:

	INSTALLED_APPS = (
		...
		"fcm_django"
	)

	FCM_DJANGO_SETTINGS = {
		"FCM_SERVER_KEY": "[your api key]"
	}

Native Django migrations are in use. ``manage.py migrate`` will install and migrate all models.

Sending messages
----------------

	from fcm_django.models import FCMDevice
	
	device = FCMDevice.objects.all().first()

	device.send_message("Title", "Message")

Sending messages in bulk
------------------------

	from fcm_django.models import FCMDevice
	
	devices = FCMDevice.objects.all()
	
	devices.send_message("Title", "Message")

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

http://www.django-rest-framework.org/tutorial/6-viewsets-and-routers#using-routers

	from fcm_django.api.rest_framework import FCMDeviceAuthorizedViewSet
	
	from rest_framework.routers import DefaultRouter

	router = DefaultRouter()
	
	router.register(r'devices', FCMDeviceAuthorizedViewSet)

	urlpatterns = patterns('',
		# URLs will show up at <api_root>/devices
		url(r'^', include(router.urls)),
		# ...
	)
	
- Using as_view_ (specify which views to include)

http://www.django-rest-framework.org/tutorial/6-viewsets-and-routers#binding-viewsets-to-urls-explicitly

	from fcm_django.api.rest_framework import FCMDeviceAuthorizedViewSet

	urlpatterns = patterns('',
		# Only allow creation of devices by authenticated users
		url(r'^devices?$', FCMDeviceAuthorizedViewSet.as_view({'post': 'create'}), name='create_fcm_device'),
		# ...
	)


Python 3 support
----------------
``fcm-django`` is fully compatible with Python 3.4 & 3.5


Acknowledgments
----------------
https://github.com/jleclanche/django-push-notifications

Need help, have any questions, suggestions?
----------------
Submit an issue/PR or email me at mojca.rojko@gmail.com
