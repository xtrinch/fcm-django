from django.conf import settings

FCM_DJANGO_SETTINGS = getattr(settings, "FCM_DJANGO_SETTINGS", {})

# FCM
FCM_DJANGO_SETTINGS.setdefault("FCM_SERVER", "https://fcm.googleapis.com/fcm/send")
FCM_DJANGO_SETTINGS.setdefault("FCM_SERVER_KEY", None)

# User model
FCM_DJANGO_SETTINGS.setdefault("USER_MODEL", settings.AUTH_USER_MODEL)

FCM_DJANGO_SETTINGS.setdefault("ERRORS", {
    'invalid_registration': 'InvalidRegistration',
    'missing_registration': 'MissingRegistration',
    'not_registered': 'NotRegistered',
    'invalid_package_name': 'InvalidPackageName'
})