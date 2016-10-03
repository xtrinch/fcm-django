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

    print(result)

    # raise error only if no successful notifications were sent and there was
    # a failed notification

    if result['success'] == 0:
        raise FCMError(result)


    # TODO: prune devices to which notifications failed to send

    return str(result)


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

    print(result)

    # raise error only if no successful notifications were sent and there was
    # a failed notification

    if result['success'] == 0 and result['failure'] == 1:
        raise FCMError(result)

    return str(result)

class FCMError(Exception):
    """
    PyFCM Error
    """

    pass