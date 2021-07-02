from itertools import repeat
from typing import Any, List, Optional, Sequence, TypedDict, Union

from django.db import models
from django.utils.translation import gettext_lazy as _
from firebase_admin import messaging
from firebase_admin.exceptions import FirebaseError, InvalidArgumentError

from fcm_django.settings import FCM_DJANGO_SETTINGS as SETTINGS

# Set by Firebase. Adjust when they adjust; developers can override too if we don't
# upgrade package in time via a monkeypatch.
MAX_MESSAGES_PER_BATCH = 500


class Device(models.Model):
    name = models.CharField(
        max_length=255, verbose_name=_("Name"), blank=True, null=True
    )
    active = models.BooleanField(
        verbose_name=_("Is active"),
        default=True,
        help_text=_("Inactive devices will not be sent notifications"),
    )
    user = models.ForeignKey(
        SETTINGS["USER_MODEL"], blank=True, null=True, on_delete=models.CASCADE
    )
    date_created = models.DateTimeField(
        verbose_name=_("Creation date"), auto_now_add=True, null=True
    )

    class Meta:
        abstract = True

    def __str__(self):
        return (
            self.name
            or str(getattr(self, "device_id", ""))
            or f"{self.__class__.__name__} for {self.user or 'unknown user'}"
        )


class FCMDeviceManager(models.Manager):
    def get_queryset(self):
        return FCMDeviceQuerySet(self.model)


# Error codes: https://firebase.google.com/docs/reference/fcm/rest/v1/ErrorCode
fcm_error_list = [
    messaging.UnregisteredError,
    messaging.SenderIdMismatchError,
    InvalidArgumentError,
]


def _validate_exception_for_deactivation(exc: Union[FirebaseError, Any]) -> bool:
    if not exc:
        return False
    exc_type = type(exc)
    return (
        exc_type == InvalidArgumentError
        and exc.cause == "Invalid registration"
        or exc_type in fcm_error_list
    )


class SendMessageResponseDict(TypedDict):
    response: messaging.BatchResponse
    registration_ids_sent: List[str]
    deactivated_registration_ids: List[str]


class FCMDeviceQuerySet(models.query.QuerySet):
    """
    Bulk sends using firebase.messaging.send_all. For every 500 messages, we send a
    single HTTP request to Firebase (the 500 is set by the firebase-sdk).
    """

    @staticmethod
    def _prepare_message(message: messaging.Message, token):
        message.token = token
        return message

    @staticmethod
    def get_default_send_message_response() -> SendMessageResponseDict:
        return SendMessageResponseDict(
            response=messaging.BatchResponse([]),
            registration_ids_sent=[],
            deactivated_registration_ids=[],
        )

    def send_message(
        self,
        message: messaging.Message,
        skip_registration_id_lookup: bool = False,
        additional_registration_ids: Sequence[str] = None,
        **more_send_message_kwargs,
    ) -> SendMessageResponseDict:
        """
        Send notification of single message for all active devices in
        queryset and deactivate if DELETE_INACTIVE_DEVICES setting is set to True.

        :param message: firebase.messaging.Message. If `message` includes a token/id, it
        will be overridden.
        :param skip_registration_id_lookup: skips the QuerySet lookup and solely uses
        the list of IDs from additional_registration_ids
        :param additional_registration_ids: specific registration_ids to add to the
        QuerySet lookup
        :param more_send_message_kwargs: Parameters for firebase.messaging.send_all()
        - dry_run: bool. Whether to actually send the notification to the device
        - app: firebase_admin.App. Specify a specific app to use
        If there are any new parameters, you can still specify them here.

        :returns firebase_admin.messaging.BatchResponse
        :returns a tuple of BatchResponse and a list of deactivated registration ids
        if return_registration_ids is specified
        """
        registration_ids = (
            list(additional_registration_ids) if additional_registration_ids else []
        )
        if not skip_registration_id_lookup:
            if not self.exists() and not additional_registration_ids:
                return self.get_default_send_message_response()
            registration_ids.extend(
                self.filter(active=True).values_list("registration_id", flat=True)
            )
        num_registrations = len(registration_ids)
        if num_registrations == 0:
            return self.get_default_send_message_response()
        responses: List[messaging.SendResponse] = []
        for i in range(0, len(registration_ids), MAX_MESSAGES_PER_BATCH):
            messages = [
                self._prepare_message(m, t)
                for m, t in zip(
                    repeat(message, MAX_MESSAGES_PER_BATCH),
                    registration_ids[i : i + MAX_MESSAGES_PER_BATCH],
                )
            ]
            responses.extend(
                messaging.send_all(messages, **more_send_message_kwargs).responses
            )
        return SendMessageResponseDict(
            response=messaging.BatchResponse(responses),
            registration_ids_sent=registration_ids,
            deactivated_registration_ids=self.deactivate_devices_with_error_results(
                registration_ids, responses
            ),
        )

    def deactivate_devices_with_error_results(
        self, registration_ids: List[str], results: List[messaging.SendResponse]
    ) -> List[str]:
        deactivated_ids = [
            token
            for item, token in zip(results, registration_ids)
            if _validate_exception_for_deactivation(item.exception)
        ]
        self.filter(registration_id__in=deactivated_ids).update(active=False)
        self._delete_inactive_devices_if_requested(deactivated_ids)
        return deactivated_ids

    def _delete_inactive_devices_if_requested(self, registration_ids: List[str]):
        if SETTINGS["DELETE_INACTIVE_DEVICES"]:
            self.filter(registration_id__in=registration_ids).delete()


class AbstractFCMDevice(Device):
    DEVICE_TYPES = (("ios", "ios"), ("android", "android"), ("web", "web"))

    device_id = models.CharField(
        verbose_name=_("Device ID"),
        blank=True,
        null=True,
        db_index=True,
        help_text=_("Unique device identifier"),
        max_length=150,
    )
    registration_id = models.TextField(verbose_name=_("Registration token"))
    type = models.CharField(choices=DEVICE_TYPES, max_length=10)
    objects: "FCMDeviceQuerySet" = FCMDeviceManager()

    class Meta:
        abstract = True
        verbose_name = _("FCM device")

    def send_message(
        self,
        message: messaging.Message,
        **more_send_message_kwargs,
    ) -> Optional[messaging.SendResponse]:
        """
        Send single message. The message's token should be blank (and will be
        overridden if not). Responds with message ID string.

        :param message: firebase.messaging.Message. If `message` includes a token/id, it
        will be overridden.
        :param more_send_message_kwargs: Parameters for firebase.messaging.send_all()
        - dry_run: bool. Whether to actually send the notification to the device
        - app: firebase_admin.App. Specify a specific app to use
        If there are any new parameters, you can still specify them here.

        :returns messaging.SendResponse or None if the device was reactivated
        due to an error
        """
        message.token = self.registration_id
        try:
            return messaging.SendResponse(
                {"name": messaging.send(message, **more_send_message_kwargs)}, None
            )
        except FirebaseError as e:
            self.deactivate_devices_with_error_result(self.registration_id, e)
            return None

    @classmethod
    def deactivate_devices_with_error_result(
        cls, registration_id, firebase_exc, name=None
    ) -> List[str]:
        return cls.objects.deactivate_devices_with_error_results(
            [registration_id], [messaging.SendResponse({"name": name}, firebase_exc)]
        )


class FCMDevice(AbstractFCMDevice):
    class Meta:
        verbose_name = _("FCM device")
        verbose_name_plural = _("FCM devices")
