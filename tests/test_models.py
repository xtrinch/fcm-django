import pytest

from fcm_django.models import DeviceType, FCMDevice


@pytest.mark.django_db
def test_registration_id_size():
    """
    Verifies recommendation to allow for up to 4kb in size for FCM
    registration token (registration_id).
    """
    # 4096 / 8 = 512 characters in ascii
    _4kb_standard = ("a" * 512).encode("ascii")
    device = FCMDevice(
        registration_id=_4kb_standard,
        type=DeviceType.WEB,
    )
    device.save()
