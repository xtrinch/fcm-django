import pytest
from firebase_admin.exceptions import FirebaseError


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
