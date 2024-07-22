__author__ = "xTrinch"
__email__ = "mojca.rojko@gmail.com"
__version__ = "2.2.1"


class NotificationError(Exception):
    pass


try:
    from django import VERSION as DJANGO_VERSION

    if DJANGO_VERSION < (3, 2):
        default_app_config = "fcm_django.apps.FcmDjangoConfig"
except ImportError:
    pass
