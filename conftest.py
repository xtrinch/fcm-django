from django.conf import settings
from firebase_admin import initialize_app


def pytest_configure():
    settings.configure(
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "fcm_django",
        ],
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            },
        },
    )
    initialize_app()  # for tests requiring Firebase
