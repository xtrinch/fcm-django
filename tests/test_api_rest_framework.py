import base64

import pytest
import swapper
from django.test import override_settings

from fcm_django.api.rest_framework import FCMDeviceSerializer
from fcm_django.models import DeviceType
from fcm_django.signals import device_deactivated

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


@pytest.fixture
def concurrent_insert(monkeypatch):
    """Insert a device with the same registration_id once the create request has
    passed validation, simulating a concurrent request winning the
    check-then-insert race."""
    original_is_valid = FCMDeviceSerializer.is_valid
    inserted = []

    def is_valid(self, *args, **kwargs):
        result = original_is_valid(self, *args, **kwargs)
        if self.instance is None and not inserted:
            inserted.append(
                FCMDevice.objects.create(
                    registration_id=self.validated_data["registration_id"],
                    type=DeviceType.WEB,
                )
            )
        return result

    monkeypatch.setattr(FCMDeviceSerializer, "is_valid", is_valid)


@pytest.mark.django_db
def test_drf_endpoint_add_device_concurrent_duplicate_updates_existing(
    client, registration_id, concurrent_insert
):
    response = client.post(
        "/drf/devices/",
        {
            "registration_id": registration_id,
            "type": "android",
        },
    )

    assert response.status_code == 200
    assert FCMDevice.objects.filter(registration_id=registration_id).count() == 1
    assert (
        FCMDevice.objects.get(registration_id=registration_id).type
        == DeviceType.ANDROID
    )


@pytest.mark.django_db
def test_drf_endpoint_add_device_concurrent_duplicate_without_update_returns_400(
    client, registration_id, concurrent_insert
):
    with override_settings(FCM_DJANGO_SETTINGS={"UPDATE_ON_DUPLICATE_REG_ID": False}):
        response = client.post(
            "/drf/devices/",
            {
                "registration_id": registration_id,
                "type": "android",
            },
        )

    assert response.status_code == 400
    assert "registration_id" in response.json()
    assert FCMDevice.objects.filter(registration_id=registration_id).count() == 1
