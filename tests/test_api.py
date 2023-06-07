import base64

import pytest
import swapper

from fcm_django.models import DeviceType

FCMDevice = swapper.load_model("fcm_django", "fcmdevice")


@pytest.fixture
def username() -> str:
    return "someone"


@pytest.fixture
def password() -> str:
    return "something"


@pytest.fixture
def user(django_user_model, username: str, password: str):
    return django_user_model.objects.create_user(username=username, password=password)


@pytest.mark.django_db
def test_tastypie_endpoint_add_device(
    client, user, username, password, registration_id
):
    devices_qty = FCMDevice.objects.count()

    response = client.post(
        "/tastypie/v1/device/apns/",
        {
            "registration_id": registration_id,
            "type": "web",
        },
        content_type="application/json",
        HTTP_AUTHORIZATION="Basic "
        + base64.b64encode(f"{username}:{password}".encode()).decode("utf-8"),
    )

    assert response.status_code == 201
    assert FCMDevice.objects.count() == devices_qty + 1
    device = FCMDevice.objects.get(registration_id=registration_id)
    assert device.type == DeviceType.WEB
    assert device.registration_id == registration_id


@pytest.mark.django_db
def test_drf_endpoint_add_device(client, registration_id):
    devices_qty = FCMDevice.objects.count()

    response = client.post(
        "/drf/devices/",
        {
            "registration_id": registration_id,
            "type": "web",
        },
    )

    assert response.status_code == 201
    assert FCMDevice.objects.count() == devices_qty + 1
    assert FCMDevice.objects.get(registration_id=registration_id).type == DeviceType.WEB


@pytest.mark.django_db
def test_drf_endpoint_add_device_with_existed_token_wont_create_a_new_device(
    client, fcm_device: FCMDevice
):
    assert fcm_device.type == DeviceType.WEB
    devices_qty = FCMDevice.objects.count()

    response = client.post(
        "/drf/devices/",
        {
            "registration_id": fcm_device.registration_id,
            "type": "android",
        },
    )

    assert response.status_code == 200
    assert FCMDevice.objects.count() == devices_qty
    fcm_device.refresh_from_db()
    assert fcm_device.type == DeviceType.ANDROID


@pytest.mark.django_db
def test_drf_endpoint_add_device_with_existed_token_will_override_device_owner(
    client, user, fcm_device: FCMDevice
):
    assert fcm_device.user != user
    client.force_login(user)

    response = client.post(
        "/drf/devices/",
        {
            "registration_id": fcm_device.registration_id,
            "type": "android",
        },
    )

    assert response.status_code == 200
    fcm_device.refresh_from_db()
    assert fcm_device.user == user
