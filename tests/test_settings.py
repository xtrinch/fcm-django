import importlib

from django.test import override_settings
from django.utils.functional import Promise


def test_app_verbose_name_defaults_when_explicitly_none(settings):
    settings.FCM_DJANGO_SETTINGS = {"APP_VERBOSE_NAME": None}

    import fcm_django.apps
    import fcm_django.settings

    importlib.reload(fcm_django.settings)
    importlib.reload(fcm_django.apps)

    assert isinstance(fcm_django.apps.FcmDjangoConfig.verbose_name, Promise)
    assert str(fcm_django.apps.FcmDjangoConfig.verbose_name) == "FCM Django"


def test_runtime_settings_follow_override_settings():
    from fcm_django.settings import FCM_DJANGO_SETTINGS

    assert FCM_DJANGO_SETTINGS["DEFAULT_FIREBASE_APP"] is None
    assert FCM_DJANGO_SETTINGS["DELETE_INACTIVE_DEVICES"] is False

    with override_settings(
        FCM_DJANGO_SETTINGS={
            "DEFAULT_FIREBASE_APP": "test-app",
            "DELETE_INACTIVE_DEVICES": True,
        }
    ):
        assert FCM_DJANGO_SETTINGS["DEFAULT_FIREBASE_APP"] == "test-app"
        assert FCM_DJANGO_SETTINGS["DELETE_INACTIVE_DEVICES"] is True
