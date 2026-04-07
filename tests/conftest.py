from unittest.mock import AsyncMock, sentinel

import pytest
import swapper
from django.conf import settings
from django.db.backends.base.introspection import BaseDatabaseIntrospection
from firebase_admin.exceptions import FirebaseError
from firebase_admin.messaging import Message
from pytest_mock import MockerFixture

from fcm_django.models import DeviceType

FCMDevice = swapper.load_model("fcm_django", "fcmdevice")


@pytest.fixture(scope="session", autouse=True)
def include_legacy_swapped_device_table_in_flush():
    if not getattr(settings, "IS_SWAP", False):
        yield
        return

    original = BaseDatabaseIntrospection.django_table_names

    def django_table_names(self, only_existing=False, include_views=True):
        tables = original(
            self, only_existing=only_existing, include_views=include_views
        )
        legacy_table = "fcm_django_fcmdevice"
        if legacy_table in tables:
            return tables
        if not only_existing:
            return [*tables, legacy_table]

        existing_tables = set(self.table_names(include_views=include_views))
        if self.identifier_converter(legacy_table) in existing_tables:
            return [*tables, legacy_table]
        return tables

    BaseDatabaseIntrospection.django_table_names = django_table_names
    try:
        yield
    finally:
        BaseDatabaseIntrospection.django_table_names = original


@pytest.fixture
def username() -> str:
    return "someone"


@pytest.fixture
def password() -> str:
    return "something"


@pytest.fixture
def user(django_user_model, username: str, password: str):
    return django_user_model.objects.create_user(username=username, password=password)


@pytest.fixture
def registration_id() -> str:
    return "123456"


@pytest.fixture
def fcm_device(registration_id: str):
    instance = FCMDevice.objects.create(
        registration_id=registration_id, type=DeviceType.WEB
    )
    return instance


@pytest.fixture
def message() -> Message:
    return Message(data={"foo": "bar"})


@pytest.fixture
def firebase_error() -> FirebaseError:
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
def mock_firebase_send_each(mocker: MockerFixture):
    mock = mocker.patch("fcm_django.models.messaging.send_each")
    mock.return_value = sentinel.FIREBASE_SEND_EACH_RESPONSE
    mock.return_value.responses = []
    return mock


@pytest.fixture
def mock_firebase_send_each_async(mocker: MockerFixture):
    mock = mocker.patch(
        "fcm_django.models.messaging.send_each_async", new_callable=AsyncMock
    )
    mock.return_value = sentinel.FIREBASE_SEND_EACH_ASYNC_RESPONSE
    mock.return_value.responses = []
    return mock
