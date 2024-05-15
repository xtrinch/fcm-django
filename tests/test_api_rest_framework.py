import base64

import pytest
import swapper

from fcm_django.models import DeviceType

FCMDevice = swapper.load_model("fcm_django", "fcmdevice")


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
