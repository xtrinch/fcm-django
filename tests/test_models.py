import asyncio
from typing import Any, Optional
from unittest.mock import MagicMock, sentinel
from uuid import UUID

import pytest
import swapper
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from firebase_admin.exceptions import FirebaseError, InvalidArgumentError
from firebase_admin.messaging import Message, SendResponse

from fcm_django.models import DeviceType, FCMDeviceTopic
from fcm_django.signals import device_deactivated
from fcm_django.types import FirebaseResponseDict

FCMDevice = swapper.load_model("fcm_django", "fcmdevice")


@pytest.mark.django_db
def test_registration_id_size():
    """
    Verifies recommendation to allow for up to 4kb in size for FCM
    registration token (registration_id).
    """
    # 4096 / 8 = 512 characters in ascii
    _4kb_standard = ("a" * 512).encode("ascii")
    device = FCMDevice(
        registration_id=_4kb_standard,
        type=DeviceType.WEB,
    )
    device.save()


@pytest.mark.django_db
def test_fields_on_the_device_can_be_redefined_by_swapped_model(fcm_device: FCMDevice):
    assert isinstance(fcm_device.id, UUID if settings.IS_SWAP else int)


@pytest.mark.django_db
def test_fields_on_the_device_can_be_added_by_swapped_model(fcm_device: FCMDevice):
    assert hasattr(fcm_device, "more_data") == settings.IS_SWAP
    if settings.IS_SWAP:
        before_update = timezone.now()
        fcm_device.save()
        assert before_update < fcm_device.updated_at < timezone.now()


def test_firebase_response_dict_summary_for_batch_response(mocker):
    ok_response = mocker.Mock(spec=SendResponse)
    ok_response.exception = None
    failed_exception = FirebaseError(code="unknown", message="firebase failed")
    failed_response = mocker.Mock(spec=SendResponse)
    failed_response.exception = failed_exception
    batch_response = mocker.Mock()
    batch_response.responses = [ok_response, failed_response]
    batch_response.success_count = 1
    batch_response.failure_count = 1

    result = FirebaseResponseDict(
        response=batch_response,
        registration_ids_sent=["token-1", "token-2"],
        deactivated_registration_ids=[],
    )

    assert result.success_count == 1
    assert result.failure_count == 1
    assert result.has_failures is True
    assert result.all_failed is False
    assert result.failed_registration_ids == ["token-2"]
    assert result.failed_exceptions == [failed_exception]
    assert result.summary["failed_registration_ids"] == ["token-2"]


def test_firebase_response_dict_summary_for_topic_response(mocker):
    failed_error = mocker.Mock()
    failed_error.index = 1
    failed_error.reason = "messaging/mismatched-credential"
    topic_response = mocker.Mock()
    topic_response.errors = [failed_error]
    topic_response.success_count = 1
    topic_response.failure_count = 1

    result = FirebaseResponseDict(
        response=topic_response,
        registration_ids_sent=["token-1", "token-2"],
        deactivated_registration_ids=[],
    )

    assert result.success_count == 1
    assert result.failure_count == 1
    assert result.has_failures is True
    assert result.all_failed is False
    assert result.failed_registration_ids == ["token-2"]
    assert result.failed_exceptions == ["messaging/mismatched-credential"]


@pytest.mark.django_db
def test_queryset_handle_topic_subscription_aggregates_topic_errors(mocker):
    registration_ids = ["token-1", "token-2", "token-3"]

    mock_subscribe = mocker.patch("fcm_django.models.messaging.subscribe_to_topic")
    mock_subscribe.side_effect = [
        mocker.Mock(
            spec=["errors"],
            errors=[mocker.Mock(index=1, reason="messaging/mismatched-credential")],
        ),
        mocker.Mock(
            spec=["errors"],
            errors=[
                mocker.Mock(
                    index=0,
                    reason="messaging/registration-token-not-registered",
                )
            ],
        ),
    ]
    mocker.patch("fcm_django.models.MAX_DEVICES_PER_SUBSCRIBE_REQUEST", 2)

    response = FCMDevice.objects.none().handle_topic_subscription(
        True,
        topic="topic-name",
        skip_registration_id_lookup=True,
        additional_registration_ids=registration_ids,
    )

    assert mock_subscribe.call_args_list == [
        mocker.call(
            ["token-1", "token-2"],
            "topic-name",
            app=None,
        ),
        mocker.call(
            ["token-3"],
            "topic-name",
            app=None,
        ),
    ]
    assert response.failure_count == 2
    assert response.failed_registration_ids == ["token-2", "token-3"]
    assert [error.index for error in response.response.errors] == [1, 2]


@pytest.mark.django_db
def test_queryset_handle_topic_subscription_tracks_successful_subscriptions(mocker):
    first_device = FCMDevice.objects.create(
        registration_id="token-1", type=DeviceType.WEB
    )
    FCMDevice.objects.create(registration_id="token-2", type=DeviceType.WEB)

    mock_subscribe = mocker.patch("fcm_django.models.messaging.subscribe_to_topic")
    mock_subscribe.return_value = mocker.Mock(
        spec=["errors"],
        errors=[mocker.Mock(index=1, reason="messaging/mismatched-credential")],
    )

    with override_settings(FCM_DJANGO_SETTINGS={"TRACK_TOPIC_SUBSCRIPTIONS": True}):
        response = FCMDevice.objects.filter(
            registration_id__in=["token-1", "token-2"]
        ).handle_topic_subscription(True, topic="/topics/news")

    assert response.failed_registration_ids == ["token-2"]
    assert list(first_device.subscribed_topics) == ["news"]
    assert list(
        FCMDevice.objects.subscribed_to_topic("news").values_list(
            "registration_id", flat=True
        )
    ) == ["token-1"]


@pytest.mark.django_db
def test_device_handle_topic_subscription_removes_tracked_subscription(mocker):
    device = FCMDevice.objects.create(registration_id="token-1", type=DeviceType.WEB)
    FCMDeviceTopic.objects.create(device=device, topic="news")

    mock_unsubscribe = mocker.patch(
        "fcm_django.models.messaging.unsubscribe_from_topic"
    )
    mock_unsubscribe.return_value = mocker.Mock(spec=["errors"], errors=[])

    with override_settings(FCM_DJANGO_SETTINGS={"TRACK_TOPIC_SUBSCRIPTIONS": True}):
        device.handle_topic_subscription(False, topic="news")

    assert not device.topic_subscriptions.exists()


@pytest.mark.django_db
def test_topic_subscriptions_follow_swapped_device_model(fcm_device: FCMDevice):
    FCMDeviceTopic.objects.create(device=fcm_device, topic="news")

    assert list(fcm_device.subscribed_topics) == ["news"]


@pytest.mark.django_db
class TestFCMDeviceSendMessage:
    def assert_sent_successfully(
        self,
        result: Any,
        fcm_device: FCMDevice,
        message: Message,
        mock_firebase_send: MagicMock,
        message_id: str,
        app: Any = None,
        send_message_kwargs: Optional[dict] = None,
    ):
        send_message_kwargs = send_message_kwargs or {}

        assert fcm_device.registration_id
        assert message.token == fcm_device.registration_id

        mock_firebase_send.assert_called_once_with(
            message, app=app, **send_message_kwargs
        )

        # Ensure we properly construct the response with the exact same message that was
        # obtained from messaging.send call
        assert isinstance(result, SendResponse)
        assert result.message_id == message_id

    def test_ok(
        self,
        fcm_device: FCMDevice,
        message: Message,
        mock_firebase_send: MagicMock,
        firebase_message_id_send: str,
    ):
        """
        Ensure a message is being sent properly with default arguments
        """
        result = fcm_device.send_message(message, None)

        self.assert_sent_successfully(
            result, fcm_device, message, mock_firebase_send, firebase_message_id_send
        )

    def test_custom_params(
        self,
        fcm_device: FCMDevice,
        message: Message,
        mock_firebase_send: MagicMock,
        firebase_message_id_send: str,
    ):
        """
        Ensure custom firebase app and send_message_kwargs are being passed to
        firebase_admin.messaging.send
        """
        custom_firebase_app = sentinel.CUSTOM_FIREBASE_APP
        send_message_kwargs = {"foo": "bar"}

        result = fcm_device.send_message(
            message, custom_firebase_app, **send_message_kwargs
        )

        self.assert_sent_successfully(
            result,
            fcm_device,
            message,
            mock_firebase_send,
            firebase_message_id_send,
            app=custom_firebase_app,
            send_message_kwargs=send_message_kwargs,
        )

    def test_uses_overridden_default_firebase_app(
        self,
        fcm_device: FCMDevice,
        message: Message,
        mock_firebase_send: MagicMock,
        firebase_message_id_send: str,
    ):
        with override_settings(
            FCM_DJANGO_SETTINGS={"DEFAULT_FIREBASE_APP": sentinel.DEFAULT_APP}
        ):
            result = fcm_device.send_message(message)

        self.assert_sent_successfully(
            result,
            fcm_device,
            message,
            mock_firebase_send,
            firebase_message_id_send,
            app=sentinel.DEFAULT_APP,
        )

    def test_firebase_error(
        self,
        fcm_device: FCMDevice,
        message: Message,
        mock_firebase_send: MagicMock,
        firebase_error: FirebaseError,
    ):
        """
        Ensure when happened unknown firebase error device is still active and raised the FirebaseError
        """
        mock_firebase_send.side_effect = firebase_error

        with pytest.raises(FirebaseError, match=str(firebase_error)):
            fcm_device.send_message(message)

        fcm_device.refresh_from_db()
        # device is still active because error is unknown
        assert fcm_device.active

    def test_firebase_invalid_registration_error(
        self,
        fcm_device: FCMDevice,
        message: Message,
        mock_firebase_send: MagicMock,
    ):
        """
        Ensure when Invalid registration firebase error device is still active and raised the FirebaseError
        """
        firebase_invalid_registration_error = InvalidArgumentError(
            message="Error", cause="Invalid registration"
        )
        mock_firebase_send.side_effect = firebase_invalid_registration_error

        with pytest.raises(
            FirebaseError, match=str(firebase_invalid_registration_error)
        ):
            fcm_device.send_message(message)

        fcm_device.refresh_from_db()
        # ensure that device deactivated
        assert not fcm_device.active

    def test_firebase_invalid_argument_error_does_not_deactivate_device(
        self,
        fcm_device: FCMDevice,
        message: Message,
        mock_firebase_send: MagicMock,
    ):
        firebase_invalid_argument_error = InvalidArgumentError(
            message="Error", cause="Invalid TTL"
        )
        mock_firebase_send.side_effect = firebase_invalid_argument_error

        with pytest.raises(FirebaseError, match=str(firebase_invalid_argument_error)):
            fcm_device.send_message(message)

        fcm_device.refresh_from_db()
        assert fcm_device.active


class TestFCMDeviceSendTopicMessage:
    def assert_sent_successfully(
        self,
        result: Any,
        message: Message,
        topic: str,
        mock_firebase_send: MagicMock,
        message_id: str,
        app: Any = None,
        send_message_kwargs: Optional[dict] = None,
    ):
        send_message_kwargs = send_message_kwargs or {}

        assert message.topic == topic

        mock_firebase_send.assert_called_once_with(
            message, app=app, **send_message_kwargs
        )

        # Ensure we properly construct the response with the exact same message that was
        # obtained from messaging.send call
        assert isinstance(result, SendResponse)
        assert result.message_id == message_id

    def test_ok(
        self,
        message: Message,
        mock_firebase_send: MagicMock,
        firebase_message_id_send: str,
    ):
        """
        Ensure a topic message is being sent properly with default arguments
        """
        topic = "topic"

        result = FCMDevice.send_topic_message(message, topic)

        self.assert_sent_successfully(
            result, message, topic, mock_firebase_send, firebase_message_id_send
        )

    def test_custom_params(
        self,
        message: Message,
        mock_firebase_send: MagicMock,
        firebase_message_id_send: str,
    ):
        """
        Ensure custom firebase app and send_message_kwargs are being passed to
        firebase_admin.messaging.send
        """
        topic = "topic"
        custom_firebase_app = sentinel.CUSTOM_FIREBASE_APP
        send_message_kwargs = {"foo": "bar"}

        result = FCMDevice.send_topic_message(
            message, topic, custom_firebase_app, **send_message_kwargs
        )

        self.assert_sent_successfully(
            result,
            message,
            topic,
            mock_firebase_send,
            firebase_message_id_send,
            custom_firebase_app,
            send_message_kwargs,
        )

    def test_firebase_error(
        self,
        message: Message,
        mock_firebase_send: MagicMock,
        firebase_error: FirebaseError,
    ):
        """
        Ensure we raise an error in case firebase_admin.messaging.send throws one
        """
        mock_firebase_send.side_effect = firebase_error

        with pytest.raises(FirebaseError, match=str(firebase_error)):
            FCMDevice.send_topic_message(message, "example")


@pytest.mark.django_db
class TestFCMDeviceQuerySetSendBulkPersonalizedMessages:
    def test_ok(
        self,
        mocker,
        mock_firebase_send_each: MagicMock,
    ):
        first_device = FCMDevice.objects.create(
            registration_id="token-1", type=DeviceType.WEB
        )
        second_device = FCMDevice.objects.create(
            registration_id="token-2", type=DeviceType.WEB
        )
        first_response = mocker.Mock(spec=SendResponse)
        second_response = mocker.Mock(spec=SendResponse)
        mock_firebase_send_each.return_value.responses = [
            first_response,
            second_response,
        ]

        result = FCMDevice.objects.send_bulk_personalized_messages(
            title_template="Hello {name}",
            body_template="You have {count} updates",
            message_data={
                first_device.registration_id: {"name": "Alice", "count": 3},
                second_device.registration_id: {"name": "Bob", "count": 7},
            },
            data_fields={"kind": "digest"},
            dry_run=True,
        )

        assert sorted(result.registration_ids_sent) == sorted(
            [
                first_device.registration_id,
                second_device.registration_id,
            ]
        )
        assert result.deactivated_registration_ids == []
        mock_firebase_send_each.assert_called_once()
        messages = mock_firebase_send_each.call_args.args[0]
        messages_by_token = {message.token: message for message in messages}
        assert set(messages_by_token) == {
            first_device.registration_id,
            second_device.registration_id,
        }
        assert (
            messages_by_token[first_device.registration_id].notification.title
            == "Hello Alice"
        )
        assert (
            messages_by_token[second_device.registration_id].notification.title
            == "Hello Bob"
        )
        assert (
            messages_by_token[first_device.registration_id].notification.body
            == "You have 3 updates"
        )
        assert (
            messages_by_token[second_device.registration_id].notification.body
            == "You have 7 updates"
        )
        assert all(message.data == {"kind": "digest"} for message in messages)
        assert mock_firebase_send_each.call_args.kwargs["app"] is None
        assert mock_firebase_send_each.call_args.kwargs["dry_run"] is True

    def test_missing_template_values_are_left_unchanged(
        self,
        mock_firebase_send_each: MagicMock,
    ):
        device = FCMDevice.objects.create(
            registration_id="token-1", type=DeviceType.WEB
        )

        FCMDevice.objects.send_bulk_personalized_messages(
            title_template="Hello {name}",
            body_template="You have {count} updates",
            message_data={device.registration_id: {"name": "Alice"}},
        )

        message = mock_firebase_send_each.call_args.args[0][0]
        assert message.notification.title == "Hello Alice"
        assert message.notification.body == "You have {count} updates"


@pytest.mark.django_db(transaction=True)
class TestFCMDeviceQuerySetAsyncSendMessage:
    def test_ok(
        self,
        fcm_device: FCMDevice,
        message: Message,
        mock_firebase_send_each_async: MagicMock,
        mocker,
    ):
        response = mocker.Mock(spec=SendResponse)
        mock_firebase_send_each_async.return_value.responses = [response]

        result = asyncio.run(
            FCMDevice.objects.filter(pk=fcm_device.pk).asend_message(
                message,
                dry_run=True,
            )
        )

        assert result.registration_ids_sent == [fcm_device.registration_id]
        assert result.deactivated_registration_ids == []
        mock_firebase_send_each_async.assert_awaited_once()
        sent_message = mock_firebase_send_each_async.call_args.args[0][0]
        assert sent_message.token == fcm_device.registration_id
        assert mock_firebase_send_each_async.call_args.kwargs["app"] is None
        assert mock_firebase_send_each_async.call_args.kwargs["dry_run"] is True

    def test_invalid_argument_error_does_not_deactivate_device(
        self,
        fcm_device: FCMDevice,
        message: Message,
        mock_firebase_send_each_async: MagicMock,
        mocker,
    ):
        failed_response = mocker.Mock(spec=SendResponse)
        failed_response.exception = InvalidArgumentError(
            message="Error", cause="Invalid TTL"
        )
        mock_firebase_send_each_async.return_value.responses = [failed_response]

        result = asyncio.run(
            FCMDevice.objects.filter(pk=fcm_device.pk).asend_message(message)
        )

        assert result.failed_exceptions == [failed_response.exception]
        assert result.deactivated_registration_ids == []
        fcm_device.refresh_from_db()
        assert fcm_device.active

    def test_delete_inactive_devices_follows_override_settings(
        self,
        fcm_device: FCMDevice,
        message: Message,
        mock_firebase_send_each_async: MagicMock,
        mocker,
    ):
        failed_response = mocker.Mock(spec=SendResponse)
        failed_response.exception = InvalidArgumentError(
            message="Error", cause="Invalid registration"
        )
        mock_firebase_send_each_async.return_value.responses = [failed_response]

        with override_settings(FCM_DJANGO_SETTINGS={"DELETE_INACTIVE_DEVICES": True}):
            asyncio.run(
                FCMDevice.objects.filter(pk=fcm_device.pk).asend_message(message)
            )

        assert not FCMDevice.objects.filter(pk=fcm_device.pk).exists()

    def test_invalid_registration_emits_device_deactivated_signal_when_enabled(
        self,
        fcm_device: FCMDevice,
        message: Message,
        mock_firebase_send_each_async: MagicMock,
        mocker,
    ):
        failed_response = mocker.Mock(spec=SendResponse)
        failed_response.exception = InvalidArgumentError(
            message="Error", cause="Invalid registration"
        )
        mock_firebase_send_each_async.return_value.responses = [failed_response]
        receiver = mocker.Mock()
        device_deactivated.connect(receiver)

        try:
            with override_settings(
                FCM_DJANGO_SETTINGS={"EMIT_DEVICE_DEACTIVATED_SIGNAL": True}
            ):
                result = asyncio.run(
                    FCMDevice.objects.filter(pk=fcm_device.pk).asend_message(message)
                )
        finally:
            device_deactivated.disconnect(receiver)

        assert result.deactivated_registration_ids == [fcm_device.registration_id]
        receiver.assert_called_once()
        _, kwargs = receiver.call_args
        assert kwargs["sender"] is FCMDevice
        assert kwargs["registration_ids"] == [fcm_device.registration_id]
        assert kwargs["device_ids"] == [fcm_device.id]
        assert kwargs["user_ids"] == []
        assert kwargs["reason"] == "firebase_error"
        assert kwargs["source"] == "send_message"
        assert kwargs["metadata"] == {"failed_exceptions": ["INVALID_ARGUMENT"]}


@pytest.mark.django_db(transaction=True)
class TestFCMDeviceQuerySetAsyncSendBulkPersonalizedMessages:
    def test_ok(
        self,
        mocker,
        mock_firebase_send_each_async: MagicMock,
    ):
        first_device = FCMDevice.objects.create(
            registration_id="token-1", type=DeviceType.WEB
        )
        second_device = FCMDevice.objects.create(
            registration_id="token-2", type=DeviceType.WEB
        )
        first_response = mocker.Mock(spec=SendResponse)
        second_response = mocker.Mock(spec=SendResponse)
        mock_firebase_send_each_async.return_value.responses = [
            first_response,
            second_response,
        ]

        result = asyncio.run(
            FCMDevice.objects.asend_bulk_personalized_messages(
                title_template="Hello {name}",
                body_template="You have {count} updates",
                message_data={
                    first_device.registration_id: {"name": "Alice", "count": 3},
                    second_device.registration_id: {"name": "Bob", "count": 7},
                },
                data_fields={"kind": "digest"},
                dry_run=True,
            )
        )

        assert sorted(result.registration_ids_sent) == sorted(
            [
                first_device.registration_id,
                second_device.registration_id,
            ]
        )
        assert result.deactivated_registration_ids == []
        mock_firebase_send_each_async.assert_awaited_once()
        messages = mock_firebase_send_each_async.call_args.args[0]
        messages_by_token = {message.token: message for message in messages}
        assert set(messages_by_token) == {
            first_device.registration_id,
            second_device.registration_id,
        }
        assert (
            messages_by_token[first_device.registration_id].notification.title
            == "Hello Alice"
        )
        assert (
            messages_by_token[second_device.registration_id].notification.title
            == "Hello Bob"
        )
        assert (
            messages_by_token[first_device.registration_id].notification.body
            == "You have 3 updates"
        )
        assert (
            messages_by_token[second_device.registration_id].notification.body
            == "You have 7 updates"
        )
        assert all(message.data == {"kind": "digest"} for message in messages)
        assert mock_firebase_send_each_async.call_args.kwargs["app"] is None
        assert mock_firebase_send_each_async.call_args.kwargs["dry_run"] is True

    def test_missing_template_values_are_left_unchanged(
        self,
        mock_firebase_send_each_async: MagicMock,
    ):
        device = FCMDevice.objects.create(
            registration_id="token-1", type=DeviceType.WEB
        )

        asyncio.run(
            FCMDevice.objects.asend_bulk_personalized_messages(
                title_template="Hello {name}",
                body_template="You have {count} updates",
                message_data={device.registration_id: {"name": "Alice"}},
            )
        )

        message = mock_firebase_send_each_async.call_args.args[0][0]
        assert message.notification.title == "Hello Alice"
        assert message.notification.body == "You have {count} updates"


@pytest.mark.django_db
def test_queryset_send_message_invalid_argument_error_does_not_deactivate_device(
    fcm_device: FCMDevice,
    message: Message,
    mocker,
    mock_firebase_send_each: MagicMock,
):
    failed_response = mocker.Mock(spec=SendResponse)
    failed_response.exception = InvalidArgumentError(
        message="Error", cause="Invalid TTL"
    )
    mock_firebase_send_each.return_value.responses = [failed_response]

    result = FCMDevice.objects.filter(pk=fcm_device.pk).send_message(message)

    assert result.failed_exceptions == [failed_response.exception]
    assert result.deactivated_registration_ids == []
    fcm_device.refresh_from_db()
    assert fcm_device.active


@pytest.mark.django_db
def test_queryset_send_message_delete_inactive_devices_follows_override_settings(
    fcm_device: FCMDevice,
    message: Message,
    mocker,
    mock_firebase_send_each: MagicMock,
):
    failed_response = mocker.Mock(spec=SendResponse)
    failed_response.exception = InvalidArgumentError(
        message="Error", cause="Invalid registration"
    )
    mock_firebase_send_each.return_value.responses = [failed_response]

    with override_settings(FCM_DJANGO_SETTINGS={"DELETE_INACTIVE_DEVICES": True}):
        FCMDevice.objects.filter(pk=fcm_device.pk).send_message(message)

    assert not FCMDevice.objects.filter(pk=fcm_device.pk).exists()


@pytest.mark.django_db
def test_device_deactivated_signal_not_emitted_by_default(mocker):
    device = FCMDevice.objects.create(registration_id="token-1", type=DeviceType.WEB)
    response = mocker.Mock(spec=SendResponse)
    response.exception = InvalidArgumentError(
        message="Error", cause="Invalid registration"
    )
    receiver = mocker.Mock()
    device_deactivated.connect(receiver)

    try:
        deactivated_ids = FCMDevice.objects.deactivate_devices_with_error_results(
            [device.registration_id], [response]
        )
    finally:
        device_deactivated.disconnect(receiver)

    assert deactivated_ids == [device.registration_id]
    receiver.assert_not_called()


@pytest.mark.django_db
def test_device_deactivated_signal_emitted_when_enabled(mocker):
    user = get_user_model().objects.create(username="signal-user")
    device = FCMDevice.objects.create(
        registration_id="token-1",
        type=DeviceType.WEB,
        user=user,
    )
    response = mocker.Mock(spec=SendResponse)
    response.exception = InvalidArgumentError(
        message="Error", cause="Invalid registration"
    )
    receiver = mocker.Mock()
    device_deactivated.connect(receiver)

    try:
        with override_settings(
            FCM_DJANGO_SETTINGS={"EMIT_DEVICE_DEACTIVATED_SIGNAL": True}
        ):
            deactivated_ids = FCMDevice.objects.deactivate_devices_with_error_results(
                [device.registration_id], [response]
            )
    finally:
        device_deactivated.disconnect(receiver)

    assert deactivated_ids == [device.registration_id]
    receiver.assert_called_once()
    _, kwargs = receiver.call_args
    assert kwargs["sender"] is FCMDevice
    assert kwargs["registration_ids"] == [device.registration_id]
    assert kwargs["device_ids"] == [device.id]
    assert kwargs["user_ids"] == [user.id]
    assert kwargs["reason"] == "firebase_error"
    assert kwargs["source"] == "send_message"
    assert kwargs["metadata"] == {"failed_exceptions": ["INVALID_ARGUMENT"]}


@pytest.mark.django_db
def test_deactivate_emits_signal_with_explicit_reason_and_source(mocker):
    user = get_user_model().objects.create(username="duplicate-user")
    device = FCMDevice.objects.create(
        registration_id="shared-token",
        type=DeviceType.WEB,
        user=user,
    )
    receiver = mocker.Mock()
    device_deactivated.connect(receiver)

    try:
        with override_settings(
            FCM_DJANGO_SETTINGS={"EMIT_DEVICE_DEACTIVATED_SIGNAL": True}
        ):
            deactivated_ids = FCMDevice.objects.filter(pk=device.pk).deactivate(
                reason="duplicate_registration_id",
                source="serializer_create",
                metadata={
                    "request_method": "create",
                    "target_user_id": 999,
                },
            )
    finally:
        device_deactivated.disconnect(receiver)

    assert deactivated_ids == [device.registration_id]
    receiver.assert_called_once()
    _, kwargs = receiver.call_args
    assert kwargs["registration_ids"] == [device.registration_id]
    assert kwargs["device_ids"] == [device.id]
    assert kwargs["user_ids"] == [user.id]
    assert kwargs["reason"] == "duplicate_registration_id"
    assert kwargs["source"] == "serializer_create"
    assert kwargs["metadata"] == {
        "request_method": "create",
        "target_user_id": 999,
    }
