from typing import TYPE_CHECKING

from fcm_django.settings import FCM_DJANGO_SETTINGS as SETTINGS

if TYPE_CHECKING:
    import firebase_admin
    from firebase_admin import messaging


_cached_app = None


def firebase_messaging():
    from firebase_admin import messaging

    return messaging


def firebase_error_type():
    from firebase_admin.exceptions import FirebaseError

    return FirebaseError


def invalid_argument_error_type():
    from firebase_admin.exceptions import InvalidArgumentError

    return InvalidArgumentError


def get_app(app: "firebase_admin.App" = None):
    """Resolve the Firebase app, initializing it lazily if configured."""
    global _cached_app

    if app is not None:
        return app

    if SETTINGS.get("DEFAULT_FIREBASE_APP") is not None:
        return SETTINGS["DEFAULT_FIREBASE_APP"]

    if _cached_app is not None:
        return _cached_app

    from firebase_admin import get_app as firebase_get_app

    try:
        _cached_app = firebase_get_app()
        return _cached_app
    except ValueError:
        pass

    init_callable = SETTINGS.get("FIREBASE_APP_INITIALIZER")
    if not init_callable:
        return None

    result = init_callable()
    if result is not None:
        _cached_app = result
        return _cached_app

    try:
        _cached_app = firebase_get_app()
        return _cached_app
    except ValueError:
        raise ValueError(
            "FIREBASE_APP_INITIALIZER must return an App or call initialize_app()"
        )
