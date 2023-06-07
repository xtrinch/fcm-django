# ToDo: add test for swap user when another user use the same token
# ToDo: add test for django admin

import base64

import pytest
import swapper

from fcm_django.models import DeviceType

FCMDevice = swapper.load_model("fcm_django", "fcmdevice")


@pytest.fixture
def registration_id():
    return "001"


@pytest.mark.django_db
def test_tastypie_endpoint_add_device(client, django_user_model, registration_id):
    username = "someone"
    password = "something"
    django_user_model.objects.create_user(username=username, password=password)
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
    client, registration_id
):
    device = FCMDevice.objects.create(
        registration_id=registration_id, type=DeviceType.ANDROID
    )
    devices_qty = FCMDevice.objects.count()

    response = client.post(
        "/drf/devices/",
        {
            "registration_id": registration_id,
            "type": "web",
        },
    )

    assert response.status_code == 200
    assert FCMDevice.objects.count() == devices_qty
    device.refresh_from_db()
    assert device.type == DeviceType.WEB
