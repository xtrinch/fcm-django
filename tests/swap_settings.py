from .settings import *

INSTALLED_APPS += [
    'tests.swapped_models',
]

FCM_DJANGO_FCMDEVICE_MODEL = "swapped_models.CustomDevice"
