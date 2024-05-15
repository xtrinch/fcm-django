import swapper
from django.db.models import Q
from rest_framework import permissions, status
from rest_framework.mixins import CreateModelMixin
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer, Serializer, ValidationError
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from fcm_django.settings import FCM_DJANGO_SETTINGS as SETTINGS

FCMDevice = swapper.load_model("fcm_django", "fcmdevice")


# Serializers
class DeviceSerializerMixin(ModelSerializer):
    class Meta:
        fields = (
            "id",
            "name",
            "registration_id",
            "device_id",
            "active",
            "date_created",
            "type",
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
                primary_key = self.instance.id
            elif self.context["request"].method == "POST":
                request_method = "create"

        Device = self.Meta.model
        # if request authenticated, unique together with registration_id and
        # user
        user = self.context["request"].user
        registration_id = attrs.get("registration_id")

        if request_method == "update":
            if registration_id:
                if user is not None and user.is_authenticated:
                    devices = Device.objects.filter(
                        registration_id=registration_id
                    ).exclude(id=primary_key)
                    if attrs.get("active", False):
                        devices.filter(~Q(user=user)).update(active=False)
                    devices = devices.filter(user=user)
                else:
                    devices = Device.objects.filter(
                        registration_id=registration_id
                    ).exclude(id=primary_key)
        elif request_method == "create":
            if user is not None and user.is_authenticated:
                devices = Device.objects.filter(registration_id=registration_id)
                devices.filter(~Q(user=user)).update(active=False)
                devices = devices.filter(user=user, active=True)
            else:
                devices = Device.objects.filter(registration_id=registration_id)

        if devices:
            raise ValidationError({"registration_id": "This field must be unique."})
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
class DeviceViewSetMixin:
    lookup_field = "registration_id"

    def create(self, request, *args, **kwargs):
        serializer = None
        is_update = False
        if (
            SETTINGS.get("UPDATE_ON_DUPLICATE_REG_ID")
            and "registration_id" in request.data
        ):
            instance = self.queryset.model.objects.filter(
                registration_id=request.data["registration_id"]
            ).first()
            if instance:
                serializer = self.get_serializer(instance, data=request.data)
                is_update = True
        if not serializer:
            serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        if is_update:
            self.perform_update(serializer)
            return Response(serializer.data)
        else:
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(
                serializer.data, status=status.HTTP_201_CREATED, headers=headers
            )

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            if SETTINGS["ONE_DEVICE_PER_USER"] and self.request.data.get(
                "active", True
            ):
                FCMDevice.objects.filter(user=self.request.user).update(active=False)
            return serializer.save(user=self.request.user)
        return serializer.save()

    def perform_update(self, serializer):
        if self.request.user.is_authenticated:
            if SETTINGS["ONE_DEVICE_PER_USER"] and self.request.data.get(
                "active", False
            ):
                FCMDevice.objects.filter(user=self.request.user).update(active=False)

            return serializer.save(user=self.request.user)
        return serializer.save()


class AuthorizedMixin:
    permission_classes = (permissions.IsAuthenticated, IsOwner)

    def get_queryset(self):
        # filter all devices to only those belonging to the current user
        return self.queryset.filter(user=self.request.user)


# ViewSets
class FCMDeviceViewSet(DeviceViewSetMixin, ModelViewSet):
    queryset = FCMDevice.objects.order_by("-id")
    serializer_class = FCMDeviceSerializer


class FCMDeviceCreateOnlyViewSet(DeviceViewSetMixin, CreateModelMixin, GenericViewSet):
    queryset = FCMDevice.objects.all()
    serializer_class = FCMDeviceSerializer


class FCMDeviceAuthorizedViewSet(AuthorizedMixin, FCMDeviceViewSet):
    pass
