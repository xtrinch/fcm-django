from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from django.conf import settings
from django.utils.translation import gettext_lazy as _

DEFAULT_SETTINGS = {
    "DEFAULT_FIREBASE_APP": None,
    "APP_VERBOSE_NAME": _("FCM Django"),
    "ONE_DEVICE_PER_USER": False,
    "DELETE_INACTIVE_DEVICES": False,
    "EMIT_DEVICE_DEACTIVATED_SIGNAL": False,
    "UPDATE_ON_DUPLICATE_REG_ID": True,
    "ERRORS": {
        "invalid_registration": "InvalidRegistration",
        "missing_registration": "MissingRegistration",
        "not_registered": "NotRegistered",
        "invalid_package_name": "InvalidPackageName",
    },
    "MYSQL_COMPATIBILITY": False,
}


class FCMSettings(Mapping[str, Any]):
    def __init__(self) -> None:
        self._resolved: dict[str, Any] | None = None
        self._settings_source: object | None = None

    def _resolve(self) -> dict[str, Any]:
        settings_source = settings._wrapped
        if self._resolved is None or self._settings_source is not settings_source:
            user_settings = getattr(settings, "FCM_DJANGO_SETTINGS", {}) or {}
            resolved = deepcopy(DEFAULT_SETTINGS)
            resolved["USER_MODEL"] = settings.AUTH_USER_MODEL
            resolved.update(user_settings)
            if resolved.get("APP_VERBOSE_NAME") is None:
                resolved["APP_VERBOSE_NAME"] = DEFAULT_SETTINGS["APP_VERBOSE_NAME"]
            self._resolved = resolved
            self._settings_source = settings_source
        return self._resolved

    def __getitem__(self, key: str) -> Any:
        return self._resolve()[key]

    def __iter__(self):
        return iter(self._resolve())

    def __len__(self) -> int:
        return len(self._resolve())

    def get(self, key: str, default: Any = None) -> Any:
        return self._resolve().get(key, default)


FCM_DJANGO_SETTINGS = FCMSettings()
