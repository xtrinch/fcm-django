from django.conf import settings

FCM_DJANGO_SETTINGS = getattr(settings, "FCM_DJANGO_SETTINGS", {})

# FCM
FCM_DJANGO_SETTINGS.setdefault("FCM_SERVER", "https://fcm.googleapis.com/fcm/send")
FCM_DJANGO_SETTINGS.setdefault("FCM_SERVER_KEY", None)
FCM_DJANGO_SETTINGS.setdefault("ONE_DEVICE_PER_USER", False)
FCM_DJANGO_SETTINGS.setdefault("DELETE_INACTIVE_DEVICES", False)

# User model
FCM_DJANGO_SETTINGS.setdefault("USER_MODEL", settings.AUTH_USER_MODEL)

FCM_DJANGO_SETTINGS.setdefault("ERRORS", {
    'invalid_registration': 'InvalidRegistration',
    'missing_registration': 'MissingRegistration',
    'not_registered': 'NotRegistered',
    'invalid_package_name': 'InvalidPackageName'
})