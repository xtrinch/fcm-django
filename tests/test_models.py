from typing import Any, Optional
from unittest.mock import MagicMock, sentinel
from uuid import UUID

import pytest
import swapper
from django.conf import settings
from django.utils import timezone
from firebase_admin.exceptions import FirebaseError, InvalidArgumentError
from firebase_admin.messaging import Message, SendResponse

from fcm_django.models import DeviceType

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
