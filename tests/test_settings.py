import importlib

from django.utils.functional import Promise


def test_app_verbose_name_defaults_when_explicitly_none(settings):
    settings.FCM_DJANGO_SETTINGS = {"APP_VERBOSE_NAME": None}

    import fcm_django.apps
    import fcm_django.settings

    importlib.reload(fcm_django.settings)
    importlib.reload(fcm_django.apps)

    assert isinstance(fcm_django.apps.FcmDjangoConfig.verbose_name, Promise)
    assert str(fcm_django.apps.FcmDjangoConfig.verbose_name) == "FCM Django"
