from __future__ import absolute_import
from rest_framework import permissions
from rest_framework.serializers import ModelSerializer, ValidationError, Serializer, CurrentUserDefault
from rest_framework.viewsets import ModelViewSet
from fcm_django.models import FCMDevice
from django.db.models import Q
from fcm_django.settings import FCM_DJANGO_SETTINGS as SETTINGS

# Fields


# Serializers
class DeviceSerializerMixin(ModelSerializer):
	class Meta:
		fields = ("id", "name", "registration_id", "device_id", "active", "date_created", "type")
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
		# if request authenticated, unique together with registration_id and user
		user = self.context['request'].user
		if request_method == "update":
			if user is not None and user.is_authenticated():
				devices = Device.objects.filter(registration_id=attrs["registration_id"]) \
					.exclude(id=primary_key)
				if (attrs["active"]):
					devices.filter(~Q(user=user)).update(active=False)
				devices = devices.filter(user=user)
			else:
				devices = Device.objects.filter(registration_id=attrs["registration_id"]) \
					.exclude(id=primary_key)
		elif request_method == "create":
			if user is not None and user.is_authenticated():
				devices = Device.objects.filter(registration_id=attrs["registration_id"])
				devices.filter(~Q(user=user)).update(active=False)
				devices = devices.filter(user=user)
			else:
				devices = Device.objects.filter(registration_id=attrs["registration_id"])

		if devices:
			raise ValidationError({'registration_id': 'This field must be unique.'})
		return attrs

class FCMDeviceSerializer(ModelSerializer, UniqueRegistrationSerializerMixin):

	class Meta(DeviceSerializerMixin.Meta):
		model = FCMDevice

		extra_kwargs = {"id": {"read_only": False, "required": False}}


# Permissions
class IsOwner(permissions.BasePermission):
	def has_object_permission(self, request, view, obj):
		# must be the owner to view the object
		return obj.user == request.user


# Mixins
class DeviceViewSetMixin(object):
	lookup_field = "registration_id"

	def perform_create(self, serializer):
		if self.request.user.is_authenticated():
			serializer.save(user=self.request.user)

			if SETTINGS["ONE_DEVICE_PER_USER"]:
				active = self.request.data.get('active', True)
				if active:
					FCMDevice.objects.filter(user=self.request.user).update(active=False)

		return super(DeviceViewSetMixin, self).perform_create(serializer)

	def perform_update(self, serializer):
		if self.request.user.is_authenticated():
			serializer.save(user=self.request.user)

			if SETTINGS["ONE_DEVICE_PER_USER"]:
				active = self.request.data.get('active', False)
				if active:
					FCMDevice.objects.filter(user=self.request.user).update(active=False)

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


class FCMDeviceAuthorizedViewSet(AuthorizedMixin, FCMDeviceViewSet):
	pass
