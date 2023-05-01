from copy import copy
from typing import List, NamedTuple, Optional, Sequence, Union

from django.db import models
from django.utils.translation import gettext_lazy as _
from firebase_admin import messaging
from firebase_admin.exceptions import FirebaseError, InvalidArgumentError

from fcm_django.settings import FCM_DJANGO_SETTINGS as SETTINGS

# Set by Firebase. Adjust when they adjust; developers can override too if we don't
# upgrade package in time via a monkeypatch.
MAX_MESSAGES_PER_BATCH = 500


class Device(models.Model):
    id = models.AutoField(
        verbose_name="ID",
        primary_key=True,
        auto_created=True,
    )
    name = models.CharField(
        max_length=255, verbose_name=_("Name"), blank=True, null=True
    )
    active = models.BooleanField(
        verbose_name=_("Is active"),
        default=True,
        help_text=_("Inactive devices will not be sent notifications"),
    )
    user = models.ForeignKey(
        SETTINGS["USER_MODEL"],
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_query_name=_("fcmdevice"),
    )
    date_created = models.DateTimeField(
        verbose_name=_("Creation date"), auto_now_add=True, null=True
    )

    class Meta:
        abstract = True

    def __str__(self):
        return (
            self.name
            or (getattr(self, "device_id") or "")
            or f"{self.__class__.__name__} for {self.user or 'unknown user'}"
        )


class _FCMDeviceManager(models.Manager):
    def get_queryset(self):
        return FCMDeviceQuerySet(self.model)


# Error codes: https://firebase.google.com/docs/reference/fcm/rest/v1/ErrorCode
fcm_error_list = [
    messaging.UnregisteredError,
    messaging.SenderIdMismatchError,
    InvalidArgumentError,
]

fcm_error_list_str = [x.code for x in fcm_error_list]


def _validate_exception_for_deactivation(exc: Union[FirebaseError]) -> bool:
    if not exc:
        return False
    exc_type = type(exc)
    if exc_type == str:
        return exc in fcm_error_list_str
    return (
        exc_type == InvalidArgumentError and exc.cause == "Invalid registration"
    ) or (exc_type in fcm_error_list)


class FirebaseResponseDict(NamedTuple):
    # All errors are stored rather than raised in BatchResponse.exceptions
    # or TopicManagementResponse.errors
    response: Union[messaging.BatchResponse, messaging.TopicManagementResponse]
    registration_ids_sent: List[str]
    deactivated_registration_ids: List[str]


class FCMDeviceQuerySet(models.query.QuerySet):
    @staticmethod
    def _prepare_message(message: messaging.Message, token: str):
        message.token = token
        return copy(message)

    @staticmethod
    def get_default_send_message_response() -> FirebaseResponseDict:
        return FirebaseResponseDict(
            response=messaging.BatchResponse([]),
            registration_ids_sent=[],
            deactivated_registration_ids=[],
        )

    def get_registration_ids(
        self,
        skip_registration_id_lookup: bool = False,
        additional_registration_ids: Sequence[str] = None,
    ) -> List[str]:
        """
        Uses the current filtering/QuerySet chain to get registration IDs

        :param skip_registration_id_lookup: skips the QuerySet lookup and solely uses
        the list of IDs from additional_registration_ids
        :param additional_registration_ids: specific registration_ids to add to the
        QuerySet lookup
        :returns a list of registration IDs
        """
        registration_ids = (
            list(additional_registration_ids) if additional_registration_ids else []
        )
        if not skip_registration_id_lookup:
            registration_ids.extend(
                self.filter(active=True).values_list("registration_id", flat=True)
            )
        return registration_ids

    def send_message(
        self,
        message: messaging.Message,
        skip_registration_id_lookup: bool = False,
        additional_registration_ids: Sequence[str] = None,
        app: "firebase_admin.App" = SETTINGS["DEFAULT_FIREBASE_APP"],
        **more_send_message_kwargs,
    ) -> FirebaseResponseDict:
        """
        Send notification of single message for all active devices in
        queryset and deactivate if DELETE_INACTIVE_DEVICES setting is set to True.
        Bulk sends using firebase.messaging.send_all. For every 500 messages, we send a
        single HTTP request to Firebase (the 500 is set by the firebase-sdk).

        :param message: firebase.messaging.Message. If `message` includes a token/id, it
        will be overridden.
        :param skip_registration_id_lookup: skips the QuerySet lookup and solely uses
        the list of IDs from additional_registration_ids
        :param additional_registration_ids: specific registration_ids to add to the
        :param app: firebase_admin.App. Specify a specific app to use
        QuerySet lookup
        :param more_send_message_kwargs: Parameters for firebase.messaging.send_all()
        - dry_run: bool. Whether to actually send the notification to the device
        If there are any new parameters, you can still specify them here.

        :raises FirebaseError
        :returns FirebaseResponseDict
        """
        registration_ids = self.get_registration_ids(
            skip_registration_id_lookup,
            additional_registration_ids,
        )
        if not registration_ids:
            return self.get_default_send_message_response()
        responses: List[messaging.SendResponse] = []
        for i in range(0, len(registration_ids), MAX_MESSAGES_PER_BATCH):
            messages = [
                self._prepare_message(message, token)
                for token in registration_ids[i : i + MAX_MESSAGES_PER_BATCH]
            ]
            responses.extend(
                messaging.send_all(
                    messages, app=app, **more_send_message_kwargs
                ).responses
            )
        return FirebaseResponseDict(
            response=messaging.BatchResponse(responses),
            registration_ids_sent=registration_ids,
            deactivated_registration_ids=self.deactivate_devices_with_error_results(
                registration_ids, responses
            ),
        )

    def deactivate_devices_with_error_results(
        self,
        registration_ids: List[str],
        results: List[Union[messaging.SendResponse, messaging.ErrorInfo]],
    ) -> List[str]:
        if not results:
            return []
        if isinstance(results[0], messaging.SendResponse):
            deactivated_ids = [
                token
                for item, token in zip(results, registration_ids)
                if _validate_exception_for_deactivation(item.exception)
            ]
        else:
            deactivated_ids = [
                registration_ids[x.index]
                for x in results
                if _validate_exception_for_deactivation(x.reason)
            ]
        self.filter(registration_id__in=deactivated_ids).update(active=False)
        self._delete_inactive_devices_if_requested(deactivated_ids)
        return deactivated_ids

    def _delete_inactive_devices_if_requested(self, registration_ids: List[str]):
        if SETTINGS["DELETE_INACTIVE_DEVICES"]:
            self.filter(registration_id__in=registration_ids).delete()

    @staticmethod
    def get_default_topic_response() -> FirebaseResponseDict:
        return FirebaseResponseDict(
            response=messaging.TopicManagementResponse({"results": []}),
            registration_ids_sent=[],
            deactivated_registration_ids=[],
        )

    def handle_topic_subscription(
        self,
        should_subscribe: bool,
        topic: str,
        skip_registration_id_lookup: bool = False,
        additional_registration_ids: Sequence[str] = None,
        app: "firebase_admin.App" = SETTINGS["DEFAULT_FIREBASE_APP"],
        **more_subscribe_kwargs,
    ) -> FirebaseResponseDict:
        """
        Subscribes or Unsubscribes filtered and/or given tokens/registration_ids
        to given topic.

        :param should_subscribe: whether to have these users subscribe (True) or
        unsubscribe to a topic (False).
        :param topic: Name of the topic to subscribe to. May contain the ``/topics/``
        prefix.
        :param skip_registration_id_lookup: skips the QuerySet lookup and solely uses
        the list of IDs from additional_registration_ids
        :param additional_registration_ids: specific registration_ids to add to the
        :param app: firebase_admin.App. Specify a specific app to use
        QuerySet lookup
        :param more_subscribe_kwargs: Parameters for
        ``firebase.messaging.subscribe_to_topic()``
        If there are any new parameters, you can still specify them here.

        :raises FirebaseError
        :returns FirebaseResponseDict
        """
        registration_ids = self.get_registration_ids(
            skip_registration_id_lookup,
            additional_registration_ids,
        )
        if not registration_ids:
            return self.get_default_topic_response()
        response = (
            messaging.subscribe_to_topic
            if should_subscribe
            else messaging.unsubscribe_from_topic
        )(registration_ids, topic, app=app, **more_subscribe_kwargs)
        return FirebaseResponseDict(
            response=response,
            registration_ids_sent=registration_ids,
            deactivated_registration_ids=self.deactivate_devices_with_error_results(
                registration_ids, response.errors
            ),
        )


FCMDeviceManager = _FCMDeviceManager.from_queryset(FCMDeviceQuerySet)


class DeviceType(models.TextChoices):
    IOS = "ios", "ios"
    ANDROID = "android", "android"
    WEB = "web", "web"


class AbstractFCMDevice(Device):
    device_id = models.CharField(
        verbose_name=_("Device ID"),
        blank=True,
        null=True,
        db_index=True,
        help_text=_("Unique device identifier"),
        max_length=255,
    )
    registration_id = models.TextField(
        verbose_name=_("Registration token"),
        unique=True,
    )
    type = models.CharField(choices=DeviceType.choices, max_length=10)
    objects: "FCMDeviceQuerySet" = FCMDeviceManager()

    class Meta:
        abstract = True
        verbose_name = _("FCM device")
        indexes = [
            models.Index(fields=["registration_id", "user"]),
        ]

    def send_message(
        self,
        message: messaging.Message,
        app: "firebase_admin.App" = SETTINGS["DEFAULT_FIREBASE_APP"],
        **more_send_message_kwargs,
    ) -> Union[Optional[messaging.SendResponse], FirebaseError]:
        """
        Send single message. The message's token should be blank (and will be
        overridden if not). Responds with message ID string.

        :param message: firebase.messaging.Message. If `message` includes a token/id, it
        will be overridden.
        :param app: firebase_admin.App. Specify a specific app to use
        :param more_send_message_kwargs: Parameters for firebase.messaging.send_all()
        - dry_run: bool. Whether to actually send the notification to the device
        If there are any new parameters, you can still specify them here.

        :raises FirebaseError
        :returns messaging.SendResponse or FirebaseError if the device was
        deactivated due to an error.
        """
        message.token = self.registration_id
        try:
            return messaging.SendResponse(
                {"name": messaging.send(message, app=app, **more_send_message_kwargs)},
                None,
            )
        except FirebaseError as e:
            self.deactivate_devices_with_error_result(self.registration_id, e)
            return e

    def handle_topic_subscription(
        self,
        should_subscribe: bool,
        topic: str,
        app: "firebase_admin.App" = SETTINGS["DEFAULT_FIREBASE_APP"],
        **more_subscribe_kwargs,
    ) -> FirebaseResponseDict:
        """
        Subscribes or Unsubscribes based on instance's registration_id

        :param should_subscribe: whether to have these users subscribe (True) or
        unsubscribe to a topic (False).
        :param topic: Name of the topic to subscribe to. May contain the ``/topics/``
        prefix.
        :param app: firebase_admin.App. Specify a specific app to use
        :param more_subscribe_kwargs: Parameters for
        ``firebase.messaging.subscribe_to_topic()``
        If there are any new parameters, you can still specify them here.

        :raises FirebaseError
        :returns FirebaseResponseDict
        """
        _r_ids = [self.registration_id]
        response = (
            messaging.subscribe_to_topic
            if should_subscribe
            else messaging.unsubscribe_from_topic
        )(_r_ids, topic, app=app, **more_subscribe_kwargs)
        return FirebaseResponseDict(
            response=response,
            registration_ids_sent=_r_ids,
            deactivated_registration_ids=type(
                self
            ).objects.deactivate_devices_with_error_results(_r_ids, response.errors),
        )

    @classmethod
    def deactivate_devices_with_error_result(
        cls, registration_id, firebase_exc, name=None
    ) -> List[str]:
        return cls.objects.deactivate_devices_with_error_results(
            [registration_id], [messaging.SendResponse({"name": name}, firebase_exc)]
        )

    @staticmethod
    def send_topic_message(
        message: messaging.Message,
        topic_name: str,
        app: "firebase_admin.App" = SETTINGS["DEFAULT_FIREBASE_APP"],
        **more_send_message_kwargs,
    ) -> Union[Optional[messaging.SendResponse], FirebaseError]:
        message.topic = topic_name

        try:
            return messaging.SendResponse(
                {"name": messaging.send(message, app=app, **more_send_message_kwargs)},
                None,
            )
        except FirebaseError as e:
            return e


class FCMDevice(AbstractFCMDevice):
    class Meta:
        verbose_name = _("FCM device")
        verbose_name_plural = _("FCM devices")
