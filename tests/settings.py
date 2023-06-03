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
USE_TZ = True
ROOT_URLCONF = "tests.urls"
TEMPLATES = []
