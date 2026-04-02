from __future__ import annotations

from collections.abc import Sequence
from copy import copy
from typing import TYPE_CHECKING, Any, Optional, Union

import swapper
from asgiref.sync import sync_to_async

if TYPE_CHECKING:
    import firebase_admin
    from firebase_admin import messaging
    from firebase_admin.exceptions import FirebaseError
from django.db import models
from django.utils.translation import gettext_lazy as _

from fcm_django.firebase import (
    firebase_error_type,
    firebase_messaging,
    get_app,
    invalid_argument_error_type,
)
from fcm_django.settings import FCM_DJANGO_SETTINGS as SETTINGS
from fcm_django.signals import device_deactivated
from fcm_django.types import DeviceDeactivationData, FirebaseResponseDict

# Set by Firebase. Adjust when they adjust; developers can override too if we don't
# upgrade package in time via a monkeypatch.
MAX_MESSAGES_PER_BATCH = 500
MAX_DEVICES_PER_SUBSCRIBE_REQUEST = 1000

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
def _get_fcm_error_list():
    messaging = firebase_messaging()

    return [
        messaging.UnregisteredError,
        messaging.SenderIdMismatchError,
    ]


def _get_fcm_error_list_str():
    return [x.code for x in _get_fcm_error_list()]


def _validate_exception_for_deactivation(exc: Union[FirebaseError]) -> bool:
    InvalidArgumentError = invalid_argument_error_type()

    if not exc:
        return False
    exc_type = type(exc)
    if exc_type == str:
        return exc in _get_fcm_error_list_str()
    # INVALID_ARGUMENT is broader than token invalidation. Only deactivate for the
    # explicit invalid-registration cause; other causes such as invalid TTL or
    # malformed payload parameters should leave the device active.
    return (
        exc_type == InvalidArgumentError and exc.cause == "Invalid registration"
    ) or (exc_type in _get_fcm_error_list())


class _MissingFormatDict(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"


class FCMDeviceQuerySet(models.query.QuerySet):
    @staticmethod
    def _prepare_message(message: messaging.Message, token: str):
        message.token = token
        return copy(message)

    @staticmethod
    def get_default_send_message_response() -> FirebaseResponseDict:
        messaging = firebase_messaging()

        return FirebaseResponseDict(
            response=messaging.BatchResponse([]),
            registration_ids_sent=[],
            deactivated_registration_ids=[],
        )

    @staticmethod
    def _render_message_template(
        template: str, template_data: Optional[dict[str, Any]] = None
    ) -> str:
        if not template_data:
            return template
        return template.format_map(_MissingFormatDict(template_data))

    def _build_bulk_personalized_messages(
        self,
        registration_ids: list[str],
        title_template: str,
        body_template: str,
        message_data: Optional[dict[str, dict[str, Any]]] = None,
        data_fields: Optional[dict[str, Any]] = None,
    ) -> list["messaging.Message"]:
        from firebase_admin import messaging

        messages = []
        for token in registration_ids:
            template_data = message_data.get(token) if message_data else None
            message_kwargs: dict[str, Any] = {
                "notification": messaging.Notification(
                    title=self._render_message_template(title_template, template_data),
                    body=self._render_message_template(body_template, template_data),
                ),
                "token": token,
            }
            if data_fields:
                message_kwargs["data"] = {
                    str(key): str(value) for key, value in data_fields.items()
                }
            messages.append(messaging.Message(**message_kwargs))
        return messages

    @staticmethod
    def _get_deactivation_candidates(
        registration_ids: list[str],
        results: list[Union["messaging.SendResponse", "messaging.ErrorInfo"]],
    ) -> list[str]:
        if not results:
            return []
        from firebase_admin import messaging

        if isinstance(results[0], messaging.SendResponse):
            return [
                token
                for item, token in zip(results, registration_ids)
                if _validate_exception_for_deactivation(item.exception)
            ]
        return [
            registration_ids[item.index]
            for item in results
            if _validate_exception_for_deactivation(item.reason)
        ]

    def get_registration_ids(
        self,
        skip_registration_id_lookup: bool = False,
        additional_registration_ids: Sequence[str] = None,
    ) -> list[str]:
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

    async def aget_registration_ids(
        self,
        skip_registration_id_lookup: bool = False,
        additional_registration_ids: Sequence[str] = None,
    ) -> list[str]:
        registration_ids = (
            list(additional_registration_ids) if additional_registration_ids else []
        )
        if not skip_registration_id_lookup:
            async for registration_id in (
                self.filter(active=True)
                .values_list("registration_id", flat=True)
                .aiterator()
            ):
                registration_ids.append(registration_id)
        return registration_ids

    def send_message(
        self,
        message: messaging.Message,
        skip_registration_id_lookup: bool = False,
        additional_registration_ids: Sequence[str] = None,
        app: firebase_admin.App = None,
        **more_send_message_kwargs,
    ) -> FirebaseResponseDict:
        """
        Send notification of single message for all active devices in
        queryset and deactivate if DELETE_INACTIVE_DEVICES setting is set to True.
        Bulk sends using firebase.messaging.send_each. For every 500 messages, we send a
        single HTTP request to Firebase (the 500 is set by the firebase-sdk).

        :param message: firebase.messaging.Message. If `message` includes a token/id, it
        will be overridden.
        :param skip_registration_id_lookup: skips the QuerySet lookup and solely uses
        the list of IDs from additional_registration_ids
        :param additional_registration_ids: specific registration_ids to add to the
        :param app: firebase_admin.App. Specify a specific app to use
        QuerySet lookup
        :param more_send_message_kwargs: Parameters for firebase.messaging.send_each()
        - dry_run: bool. Whether to actually send the notification to the device
        If there are any new parameters, you can still specify them here.

        :raises FirebaseError
        :returns FirebaseResponseDict
        """
        app = get_app(app)
        registration_ids = self.get_registration_ids(
            skip_registration_id_lookup,
            additional_registration_ids,
        )
        app = SETTINGS["DEFAULT_FIREBASE_APP"] if app is None else app
        if not registration_ids:
            return self.get_default_send_message_response()
        messaging = firebase_messaging()
        responses: list[messaging.SendResponse] = []
        for i in range(0, len(registration_ids), MAX_MESSAGES_PER_BATCH):
            messages = [
                self._prepare_message(message, token)
                for token in registration_ids[i : i + MAX_MESSAGES_PER_BATCH]
            ]
            responses.extend(
                messaging.send_each(
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

    async def asend_message(
        self,
        message: "messaging.Message",
        skip_registration_id_lookup: bool = False,
        additional_registration_ids: Sequence[str] = None,
        app: Optional["firebase_admin.App"] = None,
        **more_send_message_kwargs,
    ) -> FirebaseResponseDict:
        registration_ids = await self.aget_registration_ids(
            skip_registration_id_lookup,
            additional_registration_ids,
        )
        app = SETTINGS["DEFAULT_FIREBASE_APP"] if app is None else app
        if not registration_ids:
            return self.get_default_send_message_response()
        from firebase_admin import messaging

        responses: list[messaging.SendResponse] = []
        for i in range(0, len(registration_ids), MAX_MESSAGES_PER_BATCH):
            messages = [
                self._prepare_message(message, token)
                for token in registration_ids[i : i + MAX_MESSAGES_PER_BATCH]
            ]
            batch_response = await messaging.send_each_async(
                messages, app=app, **more_send_message_kwargs
            )
            responses.extend(batch_response.responses)
        return FirebaseResponseDict(
            response=messaging.BatchResponse(responses),
            registration_ids_sent=registration_ids,
            deactivated_registration_ids=await self.adeactivate_devices_with_error_results(
                registration_ids, responses
            ),
        )

    def send_bulk_personalized_messages(
        self,
        title_template: str,
        body_template: str,
        message_data: Optional[dict[str, dict[str, Any]]] = None,
        data_fields: Optional[dict[str, Any]] = None,
        skip_registration_id_lookup: bool = False,
        additional_registration_ids: Sequence[str] = None,
        app: Optional[firebase_admin.App] = None,
        **more_send_message_kwargs,
    ) -> FirebaseResponseDict:
        """
        Send a personalized notification to each active device in the queryset.

        Templates are rendered with per-device data from ``message_data`` keyed by
        registration ID. Missing template variables are left unchanged.

        :param title_template: Notification title template.
        :param body_template: Notification body template.
        :param message_data: Mapping of registration IDs to template data.
        :param data_fields: Optional data payload added to every message.
        :param skip_registration_id_lookup: skips the QuerySet lookup and solely uses
        the list of IDs from additional_registration_ids
        :param additional_registration_ids: specific registration_ids to add to the
        QuerySet lookup
        :param app: firebase_admin.App. Specify a specific app to use
        :param more_send_message_kwargs: Parameters for firebase.messaging.send_each()
        - dry_run: bool. Whether to actually send the notification to the device

        :raises FirebaseError
        :returns FirebaseResponseDict
        """
        registration_ids = self.get_registration_ids(
            skip_registration_id_lookup,
            additional_registration_ids,
        )
        app = SETTINGS["DEFAULT_FIREBASE_APP"] if app is None else app
        app = get_app(app)
        if not registration_ids:
            return self.get_default_send_message_response()
        messaging = firebase_messaging()

        responses: list[messaging.SendResponse] = []
        for i in range(0, len(registration_ids), MAX_MESSAGES_PER_BATCH):
            batch_ids = registration_ids[i : i + MAX_MESSAGES_PER_BATCH]
            messages = self._build_bulk_personalized_messages(
                batch_ids, title_template, body_template, message_data, data_fields
            )
            responses.extend(
                messaging.send_each(
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

    async def asend_bulk_personalized_messages(
        self,
        title_template: str,
        body_template: str,
        message_data: Optional[dict[str, dict[str, Any]]] = None,
        data_fields: Optional[dict[str, Any]] = None,
        skip_registration_id_lookup: bool = False,
        additional_registration_ids: Sequence[str] = None,
        app: Optional["firebase_admin.App"] = None,
        **more_send_message_kwargs,
    ) -> FirebaseResponseDict:
        registration_ids = await self.aget_registration_ids(
            skip_registration_id_lookup,
            additional_registration_ids,
        )
        app = SETTINGS["DEFAULT_FIREBASE_APP"] if app is None else app
        if not registration_ids:
            return self.get_default_send_message_response()
        from firebase_admin import messaging

        responses: list[messaging.SendResponse] = []
        for i in range(0, len(registration_ids), MAX_MESSAGES_PER_BATCH):
            batch_ids = registration_ids[i : i + MAX_MESSAGES_PER_BATCH]
            messages = self._build_bulk_personalized_messages(
                batch_ids, title_template, body_template, message_data, data_fields
            )
            batch_response = await messaging.send_each_async(
                messages, app=app, **more_send_message_kwargs
            )
            responses.extend(batch_response.responses)

        return FirebaseResponseDict(
            response=messaging.BatchResponse(responses),
            registration_ids_sent=registration_ids,
            deactivated_registration_ids=await self.adeactivate_devices_with_error_results(
                registration_ids, responses
            ),
        )

    def deactivate(
        self,
        *,
        reason: str,
        source: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> list[str]:
        active_devices = self.filter(active=True)
        device_rows = [
            DeviceDeactivationData(*row)
            for row in active_devices.values_list("registration_id", "id", "user_id")
        ]
        if not device_rows:
            return []

        active_devices.update(active=False)
        self._emit_device_deactivated_signal(
            device_rows=device_rows,
            reason=reason,
            source=source,
            metadata=metadata,
        )
        return [device_row.registration_id for device_row in device_rows]

    async def adeactivate(
        self,
        *,
        reason: str,
        source: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> list[str]:
        active_devices = self.filter(active=True)
        device_rows = [
            DeviceDeactivationData(*row)
            for row in await sync_to_async(list)(
                active_devices.values_list("registration_id", "id", "user_id")
            )
        ]
        if not device_rows:
            return []

        await active_devices.aupdate(active=False)
        await sync_to_async(self._emit_device_deactivated_signal)(
            device_rows=device_rows,
            reason=reason,
            source=source,
            metadata=metadata,
        )
        return [device_row.registration_id for device_row in device_rows]

    def deactivate_devices_with_error_results(
        self,
        registration_ids: list[str],
        results: list[Union[messaging.SendResponse, messaging.ErrorInfo]],
    ) -> list[str]:
        deactivation_candidates = self._get_deactivation_candidates(
            registration_ids, results
        )
        failed_exceptions = self._get_failed_exception_codes(results)
        if not deactivation_candidates:
            return []
        deactivated_ids = self.filter(
            registration_id__in=deactivation_candidates
        ).deactivate(
            reason="firebase_error",
            source="send_message",
            metadata={"failed_exceptions": failed_exceptions},
        )
        self._delete_inactive_devices_if_requested(deactivated_ids)
        return deactivated_ids

    async def adeactivate_devices_with_error_results(
        self,
        registration_ids: list[str],
        results: list[Union["messaging.SendResponse", "messaging.ErrorInfo"]],
    ) -> list[str]:
        deactivation_candidates = self._get_deactivation_candidates(
            registration_ids, results
        )
        failed_exceptions = self._get_failed_exception_codes(results)
        if not deactivation_candidates:
            return []
        deactivated_ids = await self.filter(
            registration_id__in=deactivation_candidates
        ).adeactivate(
            reason="firebase_error",
            source="send_message",
            metadata={"failed_exceptions": failed_exceptions},
        )
        await self._adelete_inactive_devices_if_requested(deactivated_ids)
        return deactivated_ids

    def _delete_inactive_devices_if_requested(self, registration_ids: list[str]):
        if SETTINGS["DELETE_INACTIVE_DEVICES"]:
            self.filter(registration_id__in=registration_ids).delete()

    async def _adelete_inactive_devices_if_requested(self, registration_ids: list[str]):
        if SETTINGS["DELETE_INACTIVE_DEVICES"]:
            await self.filter(registration_id__in=registration_ids).adelete()

    @staticmethod
    def _get_failed_exception_codes(
        results: list[Union[messaging.SendResponse, messaging.ErrorInfo]],
    ) -> list[str]:
        messaging = firebase_messaging()

        failed_exceptions = []

        for item in results:
            if isinstance(item, messaging.SendResponse):
                if item.exception and _validate_exception_for_deactivation(
                    item.exception
                ):
                    failed_exceptions.append(item.exception.code)
            elif _validate_exception_for_deactivation(item.reason):
                failed_exceptions.append(item.reason)

        return failed_exceptions

    def _emit_device_deactivated_signal(
        self,
        *,
        device_rows: list[DeviceDeactivationData],
        reason: str,
        source: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        if not device_rows or not SETTINGS["EMIT_DEVICE_DEACTIVATED_SIGNAL"]:
            return

        device_deactivated.send(
            sender=self.model,
            registration_ids=[device_row.registration_id for device_row in device_rows],
            device_ids=[device_row.device_id for device_row in device_rows],
            user_ids=[
                device_row.user_id
                for device_row in device_rows
                if device_row.user_id is not None
            ],
            reason=reason,
            source=source,
            metadata=metadata or {},
        )

    @staticmethod
    def get_default_topic_response() -> FirebaseResponseDict:
        messaging = firebase_messaging()

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
        app: firebase_admin.App = None,
        **more_subscribe_kwargs,
    ) -> FirebaseResponseDict:
        """
        Subscribes or Unsubscribes filtered and/or given tokens/registration_ids
        to given topic. For every 1000 tokens/registration_ids, we send a
        single HTTP request to Firebase (the 1000 is set by the firebase-sdk).

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
        app = get_app(app)
        registration_ids = self.get_registration_ids(
            skip_registration_id_lookup,
            additional_registration_ids,
        )
        app = SETTINGS["DEFAULT_FIREBASE_APP"] if app is None else app
        if not registration_ids:
            return self.get_default_topic_response()
        messaging = firebase_messaging()

        responses: list[messaging.SendResponse] = []
        for i in range(0, len(registration_ids), MAX_DEVICES_PER_SUBSCRIBE_REQUEST):
            batch_ids = registration_ids[i : i + MAX_DEVICES_PER_SUBSCRIBE_REQUEST]
            responses.extend(
                messaging.subscribe_to_topic
                if should_subscribe
                else messaging.unsubscribe_from_topic
            )(batch_ids, topic, app=app, **more_subscribe_kwargs)
        return FirebaseResponseDict(
            response=messaging.BatchResponse(responses),
            registration_ids_sent=registration_ids,
            deactivated_registration_ids=self.deactivate_devices_with_error_results(
                registration_ids, responses
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
        unique=not SETTINGS["MYSQL_COMPATIBILITY"],
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
        app: firebase_admin.App = None,
        **more_send_message_kwargs,
    ) -> messaging.SendResponse:
        """
        Send single message. The message's token should be blank (and will be
        overridden if not). Responds with message ID string.

        :param message: firebase.messaging.Message. If `message` includes a token/id, it
        will be overridden.
        :param app: firebase_admin.App. Specify a specific app to use
        :param more_send_message_kwargs: Parameters for firebase.messaging.send_each()
        - dry_run: bool. Whether to actually send the notification to the device
        If there are any new parameters, you can still specify them here.

        :raises FirebaseError
        :returns messaging.SendResponse or FirebaseError if the device was
        deactivated due to an error.
        """
        messaging = firebase_messaging()
        app = get_app(app)

        if not self.active:
            return messaging.SendResponse(
                None,
                None,
            )
        app = SETTINGS["DEFAULT_FIREBASE_APP"] if app is None else app
        message.token = self.registration_id
        try:
            return messaging.SendResponse(
                {"name": messaging.send(message, app=app, **more_send_message_kwargs)},
                None,
            )
        except Exception as e:
            if isinstance(e, firebase_error_type()):
                self.deactivate_devices_with_error_result(self.registration_id, e)
            raise

    def handle_topic_subscription(
        self,
        should_subscribe: bool,
        topic: str,
        app: firebase_admin.App = None,
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
        messaging = firebase_messaging()
        app = get_app(app)
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
    ) -> list[str]:
        messaging = firebase_messaging()

        return cls.objects.deactivate_devices_with_error_results(
            [registration_id], [messaging.SendResponse({"name": name}, firebase_exc)]
        )

    @staticmethod
    def send_topic_message(
        message: messaging.Message,
        topic_name: str,
        app: firebase_admin.App = None,
        **more_send_message_kwargs,
    ) -> messaging.SendResponse:
        messaging = firebase_messaging()
        app = get_app(app)
        message.topic = topic_name

        return messaging.SendResponse(
            {"name": messaging.send(message, app=app, **more_send_message_kwargs)},
            None,
        )


class FCMDevice(AbstractFCMDevice):
    class Meta:
        verbose_name = _("FCM device")
        verbose_name_plural = _("FCM devices")

        if not SETTINGS["MYSQL_COMPATIBILITY"]:
            indexes = [
                models.Index(fields=["registration_id", "user"]),
            ]

        app_label = "fcm_django"
        swappable = swapper.swappable_setting("fcm_django", "fcmdevice")
