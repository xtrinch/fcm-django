from typing import List, Tuple, Union

import swapper
from django.apps import apps
from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext_lazy
from firebase_admin.messaging import (
    ErrorInfo,
    Message,
    Notification,
    SendResponse,
    TopicManagementResponse,
)

from fcm_django.models import FirebaseResponseDict, fcm_error_list
from fcm_django.settings import FCM_DJANGO_SETTINGS as SETTINGS

User = apps.get_model(*SETTINGS["USER_MODEL"].split("."))

FCMDevice = swapper.load_model("fcm_django", "fcmdevice")


class DeviceAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "device_id",
        "name",
        "type",
        "user",
        "active",
        "date_created",
    )
    list_filter = (
        "active",
        "type",
    )
    actions = (
        "send_message",
        "send_bulk_message",
        "subscribe_to_topic",
        "bulk_subscribe_to_topic",
        "unsubscribe_to_topic",
        "bulk_unsubscribe_to_topic",
        "send_topic_message",
        "enable",
        "disable",
    )
    raw_id_fields = ("user",)
    list_select_related = ("user",)

    def get_search_fields(self, request):
        if hasattr(User, "USERNAME_FIELD"):
            return "name", "device_id", f"user__{User.USERNAME_FIELD}"
        else:
            return "name", "device_id"

    def _send_deactivated_message(
        self,
        request,
        response: Union[
            FirebaseResponseDict,
            List[FirebaseResponseDict],
            List[Tuple[SendResponse, str]],
        ],
        total_failure: int,
        is_topic: bool,
    ):
        if total_failure == 0:
            return
        if is_topic:
            message = ngettext_lazy(
                "A device failed to un/subscribe to topic. %(count)d device was "
                "marked as inactive.",
                "Some devices failed to un/subscribe to topic. %(count)d devices "
                "were marked as inactive.",
                total_failure,
            )
        else:
            message = ngettext_lazy(
                "A message failed to send. %(count)d device was marked as " "inactive.",
                "Some messages failed to send. %(count)d devices were marked as "
                "inactive.",
                total_failure,
            )
        self.message_user(
            request,
            message % {"count": total_failure},
            level=messages.WARNING,
        )

        def _get_to_str_obj(obj):
            if isinstance(obj, SendResponse):
                return obj.exception
            elif isinstance(obj, TopicManagementResponse):
                return obj.errors
            return obj

        def _print_responses(_response):
            __error_list = fcm_error_list + [ErrorInfo]
            # TODO Aggregate error response text. Each firebase error
            #  has multiple response texts too
            [
                self.message_user(
                    request,
                    (
                        _("%(response)s (Registration ID/Tokens: %(reg_id)s)")
                        % {"response": _get_to_str_obj(x), "reg_id": reg_id}
                    ),
                    level=messages.WARNING,
                )
                for x, reg_id in _response
                if type(_get_to_str_obj(x)) in __error_list
            ]

        if isinstance(response, list):
            # Our custom list of single responses
            _print_responses(response)
        elif isinstance(response, FirebaseResponseDict):
            # technically, type should be: FirebaseResponseDict not just dict
            _print_responses(
                zip(
                    response.response.responses,
                    response.deactivated_registration_ids,
                ),
            )
        else:
            raise NotImplementedError

    def send_messages(self, request, queryset, bulk=False):
        """
        Provides error handling for DeviceAdmin send_message and
        send_bulk_message methods.
        """
        total_failure = 0
        single_responses: List[Tuple[SendResponse, str]] = []

        for device in queryset:
            device: "FCMDevice"
            if bulk:
                response = queryset.send_message(
                    Message(
                        notification=Notification(
                            title="Test notification", body="Test bulk notification"
                        )
                    )
                )
                total_failure = len(response.deactivated_registration_ids)
                return self._send_deactivated_message(
                    request, response, total_failure, False
                )
            else:
                response = device.send_message(
                    Message(
                        notification=Notification(
                            title="Test notification", body="Test single notification"
                        )
                    )
                )
                single_responses.append((response, device.registration_id))
                if type(response) != SendResponse:
                    total_failure += 1

        self._send_deactivated_message(request, single_responses, total_failure, False)

    def send_message(self, request, queryset):
        self.send_messages(request, queryset)

    send_message.short_description = _("Send test notification")

    def send_bulk_message(self, request, queryset):
        self.send_messages(request, queryset, True)

    send_bulk_message.short_description = _("Send test notification in bulk")

    def handle_topic_subscription(
        self, request, queryset, should_subscribe: bool, bulk: bool = False
    ):
        """
        Provides error handling for DeviceAdmin bulk_un/subscribe_to_topic and
        un/subscribe_to_topic methods.
        """
        total_failure = 0
        single_responses = []

        for device in queryset:
            device: "FCMDevice"
            if bulk:
                response: "FirebaseResponseDict" = queryset.handle_topic_subscription(
                    should_subscribe,
                    "test-topic",
                )
                total_failure = response.response.failure_count
                single_responses = [
                    (x, response.registration_ids_sent[x.index])
                    for x in response.response.errors
                ]
                break
            else:
                response = device.handle_topic_subscription(
                    should_subscribe,
                    "test-topic",
                )
                single_responses.append(
                    (
                        response.response.errors[0]
                        if len(response.response.errors) > 0
                        else "Success",
                        device.registration_id,
                    )
                )
                total_failure += len(response.deactivated_registration_ids)

        self._send_deactivated_message(request, single_responses, total_failure, True)

    def subscribe_to_topic(self, request, queryset):
        self.handle_topic_subscription(request, queryset, True)

    subscribe_to_topic.short_description = _("Subscribe to test topic")

    def bulk_subscribe_to_topic(self, request, queryset):
        self.handle_topic_subscription(request, queryset, True, True)

    bulk_subscribe_to_topic.short_description = _("Subscribe to test topic in bulk")

    def unsubscribe_to_topic(self, request, queryset):
        self.handle_topic_subscription(request, queryset, False)

    unsubscribe_to_topic.short_description = _("Unsubscribe to test topic")

    def bulk_unsubscribe_to_topic(self, request, queryset):
        self.handle_topic_subscription(request, queryset, False, True)

    bulk_unsubscribe_to_topic.short_description = _("Unsubscribe to test topic in bulk")

    def handle_send_topic_message(self, request, queryset):
        FCMDevice.send_topic_message(
            Message(
                notification=Notification(
                    title="Test notification", body="Test single notification"
                )
            ),
            "test-topic",
        )

    def send_topic_message(self, request, queryset):
        self.handle_send_topic_message(request, queryset)

    send_topic_message.short_description = _("Send message test topic")

    def enable(self, request, queryset):
        queryset.update(active=True)

    enable.short_description = _("Enable selected devices")

    def disable(self, request, queryset):
        queryset.update(active=False)

    disable.short_description = _("Disable selected devices")


admin.site.register(FCMDevice, DeviceAdmin)
