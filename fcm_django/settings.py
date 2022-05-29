from django.conf import settings
from django.utils.translation import gettext_lazy as _

FCM_DJANGO_SETTINGS = getattr(settings, "FCM_DJANGO_SETTINGS", {})

# FCM
FCM_DJANGO_SETTINGS.setdefault("DEFAULT_FIREBASE_APP", None)
FCM_DJANGO_SETTINGS.setdefault("APP_VERBOSE_NAME", _("FCM Django"))
FCM_DJANGO_SETTINGS.setdefault("ONE_DEVICE_PER_USER", False)
FCM_DJANGO_SETTINGS.setdefault("DELETE_INACTIVE_DEVICES", False)
FCM_DJANGO_SETTINGS.setdefault("UPDATE_ON_DUPLICATE_REG_ID", False)

# User model
FCM_DJANGO_SETTINGS.setdefault("USER_MODEL", settings.AUTH_USER_MODEL)

FCM_DJANGO_SETTINGS.setdefault(
    "ERRORS",
    {
        "invalid_registration": "InvalidRegistration",
        "missing_registration": "MissingRegistration",
        "not_registered": "NotRegistered",
        "invalid_package_name": "InvalidPackageName",
    },
)
