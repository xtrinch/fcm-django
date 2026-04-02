import importlib
import os
import subprocess

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
    assert FCM_DJANGO_SETTINGS["EMIT_DEVICE_DEACTIVATED_SIGNAL"] is False

    with override_settings(
        FCM_DJANGO_SETTINGS={
            "DEFAULT_FIREBASE_APP": "test-app",
            "DELETE_INACTIVE_DEVICES": True,
            "EMIT_DEVICE_DEACTIVATED_SIGNAL": True,
        }
    ):
        assert FCM_DJANGO_SETTINGS["DEFAULT_FIREBASE_APP"] == "test-app"
        assert FCM_DJANGO_SETTINGS["DELETE_INACTIVE_DEVICES"] is True
        assert FCM_DJANGO_SETTINGS["EMIT_DEVICE_DEACTIVATED_SIGNAL"] is True

    assert FCM_DJANGO_SETTINGS["DEFAULT_FIREBASE_APP"] is None
    assert FCM_DJANGO_SETTINGS["DELETE_INACTIVE_DEVICES"] is False
    assert FCM_DJANGO_SETTINGS["EMIT_DEVICE_DEACTIVATED_SIGNAL"] is False


def test_runtime_settings_do_not_share_nested_defaults():
    from fcm_django.settings import DEFAULT_SETTINGS, FCM_DJANGO_SETTINGS

    with override_settings(FCM_DJANGO_SETTINGS={}):
        errors = FCM_DJANGO_SETTINGS["ERRORS"]
        errors["temporary"] = "TemporaryError"

    assert "temporary" not in DEFAULT_SETTINGS["ERRORS"]

def test_importing_models_and_admin_does_not_eager_load_firebase_admin():
    env = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": "tests.settings.default",
    }
    script = """
import sys
import django

sys.modules.pop("firebase_admin", None)
sys.modules.pop("firebase_admin.messaging", None)

django.setup()

import fcm_django.models
import fcm_django.admin

assert "firebase_admin" not in sys.modules
assert "firebase_admin.messaging" not in sys.modules
"""
    subprocess.run(["python", "-c", script], env=env, check=True)
