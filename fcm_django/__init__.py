from django import VERSION as DJANGO_VERSION

__author__ = "xTrinch"
__email__ = "mojca.rojko@gmail.com"
__version__ = "1.0.0"


class NotificationError(Exception):
    pass


if DJANGO_VERSION < (3, 2):
    default_app_config = "fcm_django.apps.FcmDjangoConfig"
