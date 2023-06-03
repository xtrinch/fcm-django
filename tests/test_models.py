import pytest
from firebase_admin.exceptions import FirebaseError
from firebase_admin.messaging import Message

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


@pytest.mark.django_db
def test_firebase_raises(monkeypatch):
    def _firebase_raises(*args, **kwargs):
        raise FirebaseError(code=500, message="message")

    monkeypatch.setattr("firebase_admin.messaging.send", _firebase_raises)

    device = FCMDevice(
        registration_id="test",
        type=DeviceType.WEB,
    )
    with pytest.raises(FirebaseError):
        device.send_message(message=Message())

    with pytest.raises(FirebaseError):
        device.send_topic_message(message=Message(), topic_name="topic")
