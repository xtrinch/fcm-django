import uuid
from django.db import models

from fcm_django.models import AbstractFCMDevice


class CustomDevice(AbstractFCMDevice, models.Model):
    # fields could be overwritten
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    registration_id = models.CharField(unique=True,max_length=10)  # ToDo: set DB where that will fail, and then fix
    # could be added new fields
    more_data = models.TextField() 
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["registration_id", "user"]),
            models.Index(fields=["user", "device_id"]),
        ]
