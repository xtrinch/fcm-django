from firebase_admin import initialize_app

FIREBASE_APP = initialize_app()

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "fcm_django",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

USE_TZ = False
