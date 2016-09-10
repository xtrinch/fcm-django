from django.core.management import CommandError
from pyfcm import FCMNotification
from .settings import FCM_DJANGO_SETTINGS as SETTINGS

def fcm_send_message(registration_id, title=None, body=None, icon=None, data=None, **kwargs):
    api_key = SETTINGS.get("FCM_SERVER_KEY")
    push_service = FCMNotification(api_key=api_key)
    result = push_service.notify_single_device(registration_id=registration_id,
                                               message_title=title,
                                               message_body=body,
                                               message_icon=icon,
                                               data_message=data,
                                               **kwargs)

    if result['success'] == 0:
        raise FCMError(result)

    return str(result)


def fcm_send_bulk_message(registration_ids, title=None, body=None, icon=None, data=None, **kwargs):
    api_key = SETTINGS.get("FCM_SERVER_KEY")
    push_service = FCMNotification(api_key=api_key)

    # Send to multiple devices by passing a list of ids.
    #registration_ids = ["<device registration_id 1>",
    #                    "<device registration_id 2>", ]

    result = push_service.notify_multiple_devices(
        registration_ids=registration_ids,
        message_title=title,
        message_body=body,
        message_icon=icon,
        data_message=data,
        **kwargs
    )

    if result['success'] == 0:
        raise FCMError(result)

    return str(result)

class FCMError(Exception):
    """
    PyFCM Error
    """

    pass