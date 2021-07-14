from django import VERSION as DJANGO_VERSION

from fcm_django.__version__ import VERSION

__author__ = "xTrinch"
__email__ = "mojca.rojko@gmail.com"
__version__ = VERSION


class NotificationError(Exception):
    pass


if DJANGO_VERSION < (3, 2):
    default_app_config = "fcm_django.apps.FcmDjangoConfig"
