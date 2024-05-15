import pytest


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
