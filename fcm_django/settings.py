from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from django.conf import settings
from django.utils.functional import LazyObject, empty
from django.utils.translation import gettext_lazy as _

DEFAULT_SETTINGS = {
    "DEFAULT_FIREBASE_APP": None,
    "FIREBASE_APP_INITIALIZER": None,
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


class FCMSettings(LazyObject, Mapping[str, Any]):
    def __init__(self) -> None:
        super().__init__()
        self.__dict__["_resolved"] = None
        self.__dict__["_settings_source"] = None

    def _resolve(self) -> dict[str, Any]:
        settings_source = settings._wrapped
        if self._resolved is None or self._settings_source is not settings_source:
            user_settings = getattr(settings, "FCM_DJANGO_SETTINGS", {}) or {}
            resolved = deepcopy(DEFAULT_SETTINGS)
            resolved["USER_MODEL"] = settings.AUTH_USER_MODEL
            resolved.update(user_settings)
            if resolved.get("APP_VERBOSE_NAME") is None:
                resolved["APP_VERBOSE_NAME"] = DEFAULT_SETTINGS["APP_VERBOSE_NAME"]
            self.__dict__["_resolved"] = resolved
            self.__dict__["_settings_source"] = settings_source
        return self._resolved

    def _setup(self) -> None:
        self._wrapped = self._resolve()

    def _ensure_current(self) -> dict[str, Any]:
        if self._wrapped is empty or self._settings_source is not settings._wrapped:
            self._wrapped = self._resolve()
        return self._wrapped

    def __getitem__(self, key: str) -> Any:
        return self._ensure_current()[key]

    def __iter__(self):
        return iter(self._ensure_current())

    def __len__(self) -> int:
        return len(self._ensure_current())

    def get(self, key: str, default: Any = None) -> Any:
        return self._ensure_current().get(key, default)


FCM_DJANGO_SETTINGS = FCMSettings()
