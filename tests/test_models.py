from typing import Any, Optional
from unittest.mock import MagicMock, sentinel

import pytest
from firebase_admin.exceptions import FirebaseError
from firebase_admin.messaging import Message, SendResponse

from fcm_django.models import DeviceType, FCMDevice


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
        mock_fcm_device_deactivate: MagicMock,
    ):
        """
        Ensure we call deactivate_devices_with_error_result and raise the FirebaseError
        """
        mock_firebase_send.side_effect = firebase_error

        with pytest.raises(FirebaseError, match=str(firebase_error)):
            fcm_device.send_message(message)

        mock_fcm_device_deactivate.assert_called_once_with(
            fcm_device, fcm_device.registration_id, firebase_error
        )


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
