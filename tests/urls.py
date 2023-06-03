from django.urls import include, path
from rest_framework.routers import DefaultRouter

from fcm_django.api.rest_framework import FCMDeviceViewSet

router = DefaultRouter()
router.register(r"devices", FCMDeviceViewSet)


urlpatterns = [
    path("", include(router.urls)),
]
