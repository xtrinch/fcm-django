import dj_database_url

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "fcm_django",
]
DATABASES = {"default": dj_database_url.config()}
USE_TZ = True
ROOT_URLCONF = "tests.urls"
TEMPLATES = []
