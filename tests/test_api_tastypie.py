import base64

import pytest

from fcm_django.models import DeviceType, get_fcm_device_model

FCMDevice = get_fcm_device_model()


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
