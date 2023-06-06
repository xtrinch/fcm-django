from unittest.mock import sentinel

import pytest
from firebase_admin.exceptions import FirebaseError
from firebase_admin.messaging import Message
from pytest_mock import MockerFixture

from fcm_django.models import DeviceType, FCMDevice


@pytest.fixture
def fcm_device():
    instance = FCMDevice(registration_id="123456", type=DeviceType.WEB)
    return instance


@pytest.fixture
def message():
    return Message(data={"foo": "bar"})


@pytest.fixture
def firebase_error():
    return FirebaseError(code=500, message="message")


@pytest.fixture
def firebase_message_id_send():
    """
    Sentinel value representing message_id returned from `firebase_admin.messaging.send`
    """
    return sentinel.FIREBASE_MESSAGE_ID_SEND


@pytest.fixture(autouse=True)
def mock_firebase_send(mocker: MockerFixture, firebase_message_id_send):
    mock = mocker.patch("fcm_django.models.messaging.send")
    mock.return_value = firebase_message_id_send
    return mock


@pytest.fixture
def mock_fcm_device_deactivate(mocker: MockerFixture):
    return mocker.patch(
        "fcm_django.models.FCMDevice.deactivate_devices_with_error_result",
        autospec=True,
    )
