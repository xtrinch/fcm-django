# ToDo: add test for swap user when another user use the same token
# ToDo: add test when unsuccessfully activation
# ToDo: add test for tastypie

from django.conf import settings

import swapper
import pytest

from fcm_django.models import DeviceType
FCMDevice = swapper.load_model('fcm_django', 'fcmdevice')


@pytest.fixture
def registration_id():
    return '001'


@pytest.mark.django_db
def test_drf_endpoint_add_device(client, registration_id):
    devices_qty = FCMDevice.objects.count()

    response = client.post('/devices/', {
        'registration_id': registration_id,
        'type': 'web',
    })

    assert response.status_code == 201
    assert FCMDevice.objects.count() == devices_qty + 1
    assert FCMDevice.objects.get(registration_id=registration_id).type == DeviceType.WEB


@pytest.mark.django_db
def test_drf_endpoint_add_device_with_existed_token_wont_create_a_new_device(client, registration_id):
    FCMDevice.objects.create(registration_id=registration_id, type=FCMDevice)
    devices_qty = FCMDevice.objects.count()

    response = client.post('/devices/', {
        'registration_id': registration_id,
        'type': 'web',
    })

    assert response.status_code == 200
    assert FCMDevice.objects.count() == devices_qty
