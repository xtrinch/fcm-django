from django.conf import settings

if "tastypie" in settings.INSTALLED_APPS:
    # Tastypie resources are importable from the api package level (backwards compatibility)
    from .tastypie import APNSDeviceAuthenticatedResource, FCMDeviceResource

    __all__ = [
        "APNSDeviceAuthenticatedResource",
        "FCMDeviceResource",
    ]
