from __future__ import absolute_import
from rest_framework import permissions
from rest_framework.serializers import ModelSerializer, ValidationError, \
    Serializer, CurrentUserDefault
from rest_framework.mixins import CreateModelMixin
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from fcm_django.models import FCMDevice
from django import VERSION as DJ_VERSION
from django.db.models import Q
from fcm_django.settings import FCM_DJANGO_SETTINGS as SETTINGS


# Django 2 and 1 compatibility layer
def is_user_authenticated(user):
    """ Django 2 and 1 compatibility layer.

    Arguments:
    user -- Django User model.
    """

    if DJ_VERSION[0] > 1:
        return user.is_authenticated
    else:
        return user.is_authenticated()


# Serializers
class DeviceSerializerMixin(ModelSerializer):
    class Meta:
        fields = (
            "id", "name", "registration_id", "device_id", "active",
            "date_created", "type"
        )
        read_only_fields = ("date_created",)

        extra_kwargs = {"active": {"default": True}}


class UniqueRegistrationSerializerMixin(Serializer):
    def validate(self, attrs):
        devices = None
        primary_key = None
        request_method = None

        if self.initial_data.get("registration_id", None):
            if self.instance:
                request_method = "update"
                primary_key = self.instance.id
            else:
                request_method = "create"
        else:
            if self.context["request"].method in ["PUT", "PATCH"]:
                request_method = "update"
                primary_key = attrs["id"]
            elif self.context["request"].method == "POST":
                request_method = "create"

        Device = self.Meta.model
        # if request authenticated, unique together with registration_id and
        # user
        user = self.context['request'].user
        if request_method == "update":
            if user is not None and is_user_authenticated(user):
                devices = Device.objects.filter(
                    registration_id=attrs["registration_id"]) \
                    .exclude(id=primary_key)
                if (attrs.get('active', False)):
                    devices.filter(~Q(user=user)).update(active=False)
                devices = devices.filter(user=user)
            else:
                devices = Device.objects.filter(
                    registration_id=attrs["registration_id"]) \
                    .exclude(id=primary_key)
        elif request_method == "create":
            if user is not None and is_user_authenticated(user):
                devices = Device.objects.filter(
                    registration_id=attrs["registration_id"])
                devices.filter(~Q(user=user)).update(active=False)
                devices = devices.filter(user=user, active=True)
            else:
                devices = Device.objects.filter(
                    registration_id=attrs["registration_id"])

        if devices:
            raise ValidationError(
                {'registration_id': 'This field must be unique.'})
        return attrs


class FCMDeviceSerializer(ModelSerializer, UniqueRegistrationSerializerMixin):
    class Meta(DeviceSerializerMixin.Meta):
        model = FCMDevice

        extra_kwargs = {"id": {"read_only": True, "required": False}}
        extra_kwargs.update(DeviceSerializerMixin.Meta.extra_kwargs)


# Permissions
class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # must be the owner to view the object
        return obj.user == request.user


# Mixins
class DeviceViewSetMixin(object):
    lookup_field = "registration_id"

    def perform_create(self, serializer):
        if is_user_authenticated(self.request.user):
            serializer.save(user=self.request.user, commit=False)

            if (SETTINGS["ONE_DEVICE_PER_USER"] and
                    self.request.data.get('active', True)):
                FCMDevice.objects.filter(user=self.request.user).update(
                    active=False)

        return super(DeviceViewSetMixin, self).perform_create(serializer)

    def perform_update(self, serializer):
        if is_user_authenticated(self.request.user):
            serializer.save(user=self.request.user, commit=False)

            if (SETTINGS["ONE_DEVICE_PER_USER"] and
                    self.request.data.get('active', False)):
                FCMDevice.objects.filter(user=self.request.user).update(
                    active=False)

        return super(DeviceViewSetMixin, self).perform_update(serializer)


class AuthorizedMixin(object):
    permission_classes = (permissions.IsAuthenticated, IsOwner)

    def get_queryset(self):
        # filter all devices to only those belonging to the current user
        return self.queryset.filter(user=self.request.user)


# ViewSets
class FCMDeviceViewSet(DeviceViewSetMixin, ModelViewSet):
    queryset = FCMDevice.objects.all()
    serializer_class = FCMDeviceSerializer


class FCMDeviceCreateOnlyViewSet(DeviceViewSetMixin, CreateModelMixin, GenericViewSet):
    queryset = FCMDevice.objects.all()
    serializer_class = FCMDeviceSerializer


class FCMDeviceAuthorizedViewSet(AuthorizedMixin, FCMDeviceViewSet):
    pass
