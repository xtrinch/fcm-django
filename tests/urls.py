from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from tastypie.api import Api

from fcm_django.api.rest_framework import (
    FCMDeviceAuthorizedViewSet,
    FCMDeviceViewSet,
)
from fcm_django.api.tastypie import APNSDeviceAuthenticatedResource

api = Api()
api.register(APNSDeviceAuthenticatedResource())


router = DefaultRouter()
router.register(r"devices", FCMDeviceViewSet)


urlpatterns = [
    path("tastypie/", include(api.urls)),
    path("drf/", include(router.urls)),
    path(
        "drf-authorized/devices",
        FCMDeviceAuthorizedViewSet.as_view({"post": "create"}),
        name="authorized_create_fcm_device",
    ),
    path(
        "drf-authorized/devices/<str:registration_id>",
        FCMDeviceAuthorizedViewSet.as_view({"delete": "destroy"}),
        name="authorized_delete_fcm_device",
    ),
    path("admin/", admin.site.urls),
]
