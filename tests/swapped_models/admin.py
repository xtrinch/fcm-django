from django.contrib import admin

from fcm_django.admin import DeviceAdmin

from .models import CustomDevice

admin.site.unregister(CustomDevice)
admin.site.register(CustomDevice, DeviceAdmin)
