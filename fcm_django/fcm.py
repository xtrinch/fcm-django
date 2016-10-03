from django.core.management import CommandError
from pyfcm import FCMNotification
from .settings import FCM_DJANGO_SETTINGS as SETTINGS

def fcm_send_message(registration_id,
                     title=None,
                     body=None,
                     icon=None,
                     data=None,
                     sound=None,
                     badge=None, **kwargs):
    api_key = SETTINGS.get("FCM_SERVER_KEY")
    push_service = FCMNotification(api_key=api_key)
    result = push_service.notify_single_device(registration_id=registration_id,
                                               message_title=title,
                                               message_body=body,
                                               message_icon=icon,
                                               data_message=data,
                                               sound=sound,
                                               badge=badge,
                                               **kwargs)

    # do not raise errors, pyfcm will raise exceptions if response status will
    # be anything but 200

    return result


def fcm_send_bulk_message(registration_ids,
                          title=None,
                          body=None,
                          icon=None,
                          data=None,
                          sound=None,
                          badge=None, **kwargs):
    api_key = SETTINGS.get("FCM_SERVER_KEY")
    push_service = FCMNotification(api_key=api_key)

    result = push_service.notify_multiple_devices(
        registration_ids=registration_ids,
        message_title=title,
        message_body=body,
        message_icon=icon,
        data_message=data,
        sound=sound,
        badge=badge,
        **kwargs
    )

    # do not raise errors, pyfcm will raise exceptions if response status will
    # be anything but 200

    return result

class FCMError(Exception):
    """
    PyFCM Error
    """

    pass