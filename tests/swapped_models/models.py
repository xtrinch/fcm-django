import uuid

from django.db import models

from fcm_django.models import AbstractFCMDevice


def generate_custom_device_id():
    return uuid.uuid4().hex


class CustomDevice(AbstractFCMDevice):
    # fields could be overwritten
    id = models.CharField(
        primary_key=True,
        max_length=32,
        default=generate_custom_device_id,
        editable=False,
    )
    # NOTE: the max_length could not be supported or enforced on the database level
    # https://docs.djangoproject.com/en/4.2/ref/models/fields/#django.db.models.CharField.max_length
    registration_id = models.CharField(unique=True, max_length=515)
    # could be added new fields
    more_data = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            # could be added custom indexes
            models.Index(fields=["registration_id", "user"]),
        ]
