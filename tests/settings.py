import dj_database_url

SECRET_KEY = "ToP SeCrEt"

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "fcm_django",
]
DATABASES = {"default": dj_database_url.config()}
USE_TZ = True
ROOT_URLCONF = "tests.urls"
TEMPLATES = []
