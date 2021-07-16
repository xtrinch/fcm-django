from tastypie.authentication import BasicAuthentication
from tastypie.authorization import Authorization
from tastypie.resources import ModelResource

from fcm_django.models import FCMDevice


class FCMDeviceResource(ModelResource):
    class Meta:
        authorization = Authorization()
        queryset = FCMDevice.objects.all()
        resource_name = "device/apns"


class APNSDeviceAuthenticatedResource(FCMDeviceResource):
    # user = ForeignKey(UserResource, "user")

    class Meta(FCMDeviceResource.Meta):
        authentication = BasicAuthentication()

    # authorization = SameUserAuthorization()

    def obj_create(self, bundle, **kwargs):
        # See https://github.com/toastdriven/django-tastypie/issues/854
        return super().obj_create(bundle, user=bundle.request.user, **kwargs)
