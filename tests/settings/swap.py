from .base import *

INSTALLED_APPS += [
    "tests.swapped_models",
]

FCM_DJANGO_FCMDEVICE_MODEL = "swapped_models.CustomDevice"

IS_SWAP = True  # Only to distinguish which model is used in the tests
