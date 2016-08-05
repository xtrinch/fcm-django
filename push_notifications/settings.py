from django.conf import settings

PUSH_NOTIFICATIONS_SETTINGS = getattr(settings, "PUSH_NOTIFICATIONS_SETTINGS", {})

# FCM
PUSH_NOTIFICATIONS_SETTINGS.setdefault("FCM_SERVER", "https://fcm.googleapis.com/fcm/send")
PUSH_NOTIFICATIONS_SETTINGS.setdefault("FCM_SERVER_KEY", None)

# User model
PUSH_NOTIFICATIONS_SETTINGS.setdefault("USER_MODEL", settings.AUTH_USER_MODEL)
