
from django.urls import path, include
from fcm_django.api.rest_framework import FCMDeviceViewSet
from rest_framework.routers import DefaultRouter


router = DefaultRouter()
router.register(r'devices', FCMDeviceViewSet)


urlpatterns = [
    path('', include(router.urls)),
]
