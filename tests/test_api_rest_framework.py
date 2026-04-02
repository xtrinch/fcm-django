import base64
import json

import pytest
import swapper
from django.test import override_settings
from django.utils import timezone

from fcm_django.models import DeviceType
from fcm_django.signals import device_deactivated

FCMDevice = swapper.load_model("fcm_django", "fcmdevice")


@pytest.mark.django_db
def test_drf_endpoint_add_device(client, registration_id):
    before_create = timezone.now()
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
    device = FCMDevice.objects.get(registration_id=registration_id)
    assert device.type == DeviceType.WEB
    assert before_create <= device.token_updated_at <= timezone.now()


@pytest.mark.django_db
def test_drf_endpoint_add_device_with_existed_token_wont_create_a_new_device(
    client, fcm_device: FCMDevice
):
    assert fcm_device.type == DeviceType.WEB
    before_update = fcm_device.token_updated_at
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
    assert fcm_device.token_updated_at == before_update


@pytest.mark.django_db
def test_drf_endpoint_updates_token_updated_at_when_registration_id_changes(
    client, fcm_device: FCMDevice
):
    before_update = fcm_device.token_updated_at

    response = client.put(
        f"/drf/devices/{fcm_device.registration_id}/",
        data=json.dumps(
            {
                "registration_id": "new-token",
                "type": "web",
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 200
    fcm_device.refresh_from_db()
    assert fcm_device.registration_id == "new-token"
    assert before_update < fcm_device.token_updated_at <= timezone.now()


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


@pytest.mark.django_db
def test_authorized_drf_endpoint_delete_device_with_explicit_as_view_route(
    client, user, registration_id
):
    device = FCMDevice.objects.create(
        registration_id=registration_id,
        type=DeviceType.WEB,
        user=user,
    )
    client.force_login(user)

    response = client.delete(f"/drf-authorized/devices/{registration_id}")

    assert response.status_code == 204
    assert not FCMDevice.objects.filter(pk=device.pk).exists()


@pytest.mark.django_db
def test_drf_endpoint_emits_signal_for_one_device_per_user(client, user, mocker):
    old_device = FCMDevice.objects.create(
        registration_id="old-token",
        type=DeviceType.WEB,
        user=user,
        active=True,
    )
    client.force_login(user)
    receiver = mocker.Mock()
    device_deactivated.connect(receiver)

    try:
        with override_settings(
            FCM_DJANGO_SETTINGS={
                "EMIT_DEVICE_DEACTIVATED_SIGNAL": True,
                "ONE_DEVICE_PER_USER": True,
            }
        ):
            response = client.post(
                "/drf/devices/",
                {
                    "registration_id": "new-token",
                    "type": "web",
                    "active": True,
                },
            )
    finally:
        device_deactivated.disconnect(receiver)

    assert response.status_code == 201
    old_device.refresh_from_db()
    assert old_device.active is False
    receiver.assert_called_once()
    _, kwargs = receiver.call_args
    assert kwargs["registration_ids"] == ["old-token"]
    assert kwargs["device_ids"] == [old_device.id]
    assert kwargs["user_ids"] == [user.id]
    assert kwargs["reason"] == "one_device_per_user"
    assert kwargs["source"] == "perform_create"
    assert kwargs["metadata"] == {"user_id": user.id}
