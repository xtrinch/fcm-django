from typing import Any, Optional
from unittest.mock import MagicMock, sentinel

import pytest
from firebase_admin.exceptions import FirebaseError
from firebase_admin.messaging import Message, SendResponse
from pytest_mock import MockerFixture

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


@pytest.mark.django_db
def test_firebase_raises(monkeypatch):
    def _firebase_raises(*args, **kwargs):
        raise FirebaseError(code=500, message="message")

    monkeypatch.setattr("firebase_admin.messaging.send", _firebase_raises)

    device = FCMDevice(
        registration_id="test",
        type=DeviceType.WEB,
    )
    with pytest.raises(FirebaseError):
        device.send_message(message=Message())

    with pytest.raises(FirebaseError):
        device.send_topic_message(message=Message(), topic_name="topic")


class TestFCMDeviceSendMessage:
    RESPONSE_MESSAGE_SEND = sentinel.RESPONSE_MESSAGE_SEND

    @pytest.fixture
    def device(self):
        instance = FCMDevice(registration_id="123456", type=DeviceType.WEB)
        return instance

    @pytest.fixture
    def message(self):
        return Message(data={"foo": "bar"})

    @pytest.fixture(autouse=True)
    def mock_send(self, mocker: MockerFixture):
        mock = mocker.patch("fcm_django.models.messaging.send")
        mock.return_value = self.RESPONSE_MESSAGE_SEND
        return mock

    def assert_sent_successfully(
        self,
        result: Any,
        device: FCMDevice,
        message: Message,
        mock_send: MagicMock,
        app: Any = None,
        send_message_kwargs: Optional[dict] = None,
    ):
        send_message_kwargs = send_message_kwargs or {}

        assert device.registration_id
        assert message.token == device.registration_id

        mock_send.assert_called_once_with(message, app=app, **send_message_kwargs)

        # Ensure we properly construct the response with the exact same message that was
        # obtained from messaging.send call
        assert isinstance(result, SendResponse)
        assert result.message_id == self.RESPONSE_MESSAGE_SEND

    def test_ok(
        self,
        device: FCMDevice,
        message: Message,
        mock_send: MagicMock,
    ):
        """
        Ensure a message is being sent properly with default arguments
        """
        result = device.send_message(message, None)

        self.assert_sent_successfully(result, device, message, mock_send)

    def test_custom_params(
        self,
        device: FCMDevice,
        message: Message,
        mock_send: MagicMock,
    ):
        """
        Ensure custom firebase app and send_message_kwargs are being passed to
        firebase_admin.messaging.send
        """
        custom_firebase_app = sentinel.CUSTOM_FIREBASE_APP
        send_message_kwargs = {"foo": "bar"}

        result = device.send_message(
            message, custom_firebase_app, **send_message_kwargs
        )

        self.assert_sent_successfully(
            result,
            device,
            message,
            mock_send,
            app=custom_firebase_app,
            send_message_kwargs=send_message_kwargs,
        )
