import pytest
from django.test import override_settings
from firebase_admin.exceptions import FirebaseError

from fcm_django.signals import device_deactivated


@pytest.fixture
def base_admin_url(settings) -> str:
    if settings.IS_SWAP:
        return "/admin/swapped_models/customdevice/"
    else:
        return "/admin/fcm_django/fcmdevice/"


@pytest.fixture(autouse=True)
def _login_as_admin(client, admin_user) -> None:
    client.force_login(admin_user)


@pytest.mark.django_db
def test_able_to_open_admin_panel(client, base_admin_url):
    response = client.get(base_admin_url)

    assert response.status_code == 200


@pytest.mark.django_db
def test_able_to_review_device_at_admin_panel(client, base_admin_url, fcm_device):
    response = client.get(f"{base_admin_url}{fcm_device.id}/change/")

    assert response.status_code == 200


@pytest.mark.django_db
def test_send_message_action_handles_firebase_error(
    client, base_admin_url, fcm_device, mocker
):
    mocker.patch(
        "fcm_django.models.messaging.send",
        side_effect=FirebaseError(code="unknown", message="firebase failed"),
    )

    response = client.post(
        base_admin_url,
        {
            "action": "send_message",
            "_selected_action": [str(fcm_device.pk)],
        },
        follow=True,
    )

    assert response.status_code == 200
    messages = [message.message for message in response.context["messages"]]
    assert "firebase failed" in messages


@pytest.mark.django_db
def test_send_topic_message_action_handles_firebase_error(
    client, base_admin_url, fcm_device, mocker
):
    mocker.patch(
        "fcm_django.models.messaging.send",
        side_effect=FirebaseError(code="unknown", message="firebase failed"),
    )

    response = client.post(
        base_admin_url,
        {
            "action": "send_topic_message",
            "_selected_action": [str(fcm_device.pk)],
        },
        follow=True,
    )

    assert response.status_code == 200
    messages = [message.message for message in response.context["messages"]]
    assert "firebase failed" in messages


@pytest.mark.django_db
def test_disable_action_emits_device_deactivated_signal(
    client, base_admin_url, fcm_device, mocker
):
    receiver = mocker.Mock()
    device_deactivated.connect(receiver)

    try:
        with override_settings(
            FCM_DJANGO_SETTINGS={"EMIT_DEVICE_DEACTIVATED_SIGNAL": True}
        ):
            response = client.post(
                base_admin_url,
                {
                    "action": "disable",
                    "_selected_action": [str(fcm_device.pk)],
                },
                follow=True,
            )
    finally:
        device_deactivated.disconnect(receiver)

    assert response.status_code == 200
    fcm_device.refresh_from_db()
    assert fcm_device.active is False
    receiver.assert_called_once()
    _, kwargs = receiver.call_args
    assert kwargs["registration_ids"] == [fcm_device.registration_id]
    assert kwargs["device_ids"] == [fcm_device.id]
    assert kwargs["user_ids"] == []
    assert kwargs["reason"] == "manual_disable"
    assert kwargs["source"] == "admin_action"
    assert kwargs["metadata"] == {}
