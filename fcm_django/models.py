from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _

from .settings import FCM_DJANGO_SETTINGS as SETTINGS


class Device(models.Model):
    name = models.CharField(
        max_length=255,
        verbose_name=_("Name"),
        blank=True,
        null=True
    )
    active = models.BooleanField(
        verbose_name=_("Is active"), default=True,
        help_text=_("Inactive devices will not be sent notifications")
    )
    user = models.ForeignKey(SETTINGS["USER_MODEL"], blank=True, null=True,
                             on_delete=models.CASCADE)
    date_created = models.DateTimeField(
        verbose_name=_("Creation date"), auto_now_add=True, null=True
    )

    class Meta:
        abstract = True

    def __str__(self):
        return (
            self.name or str(self.device_id or "") or
            "%s for %s" % (self.__class__.__name__, self.user or "unknown user")
        )


class FCMDeviceManager(models.Manager):
    def get_queryset(self):
        return FCMDeviceQuerySet(self.model)


class FCMDeviceQuerySet(models.query.QuerySet):
    def send_message(
            self,
            title=None,
            body=None,
            icon=None,
            data=None,
            sound=None,
            badge=None,
            api_key=None,
            **kwargs):
        """
        Send notification for all active devices in queryset and deactivate if
        DELETE_INACTIVE_DEVICES setting is set to True.
        """
        if self:
            from .fcm import fcm_send_bulk_message

            registration_ids = list(self.filter(active=True).values_list(
                'registration_id',
                flat=True
            ))
            if len(registration_ids) == 0:
                return [{'failure': len(self), 'success': 0}]

            result = fcm_send_bulk_message(
                registration_ids=registration_ids,
                title=title,
                body=body,
                icon=icon,
                data=data,
                sound=sound,
                badge=badge,
                api_key=api_key,
                **kwargs
            )

            self._deactivate_devices_with_error_results(
                registration_ids,
                result['results']
            )
            return result

    def send_data_message(
            self,
            api_key=None,
            condition=None,
            collapse_key=None,
            delay_while_idle=False,
            time_to_live=None,
            restricted_package_name=None,
            low_priority=False,
            dry_run=False,
            data_message=None,
            content_available=None,
            timeout=5,
            json_encoder=None):
        """
        Send data messages for all active devices in queryset and deactivate if
        DELETE_INACTIVE_DEVICES setting is set to True.
        """
        if self:
            from .fcm import fcm_send_bulk_data_messages

            registration_ids = list(self.filter(active=True).values_list(
                'registration_id',
                flat=True
            ))
            if len(registration_ids) == 0:
                return [{'failure': len(self), 'success': 0}]

            result = fcm_send_bulk_data_messages(
                api_key=api_key,
                registration_ids=registration_ids,
                condition=condition,
                collapse_key=collapse_key,
                delay_while_idle=delay_while_idle,
                time_to_live=time_to_live,
                restricted_package_name=restricted_package_name,
                low_priority=low_priority,
                dry_run=dry_run,
                data_message=data_message,
                content_available=content_available,
                timeout=timeout,
                json_encoder=json_encoder,
            )

            self._deactivate_devices_with_error_results(
                registration_ids,
                result['results']
            )

            return result

    def _deactivate_devices_with_error_results(self, registration_ids, results):
        for (index, item) in enumerate(results):
            if 'error' in item:
                error_list = ['MissingRegistration', 'MismatchSenderId', 'InvalidRegistration', 'NotRegistered']
                if item['error'] in error_list:
                    registration_id = registration_ids[index]
                    self.filter(registration_id=registration_id).update(
                        active=False
                    )
                    self._delete_inactive_devices_if_requested(registration_id)

    def _delete_inactive_devices_if_requested(self, registration_id):
        if SETTINGS["DELETE_INACTIVE_DEVICES"]:
            self.filter(registration_id=registration_id).delete()


class AbstractFCMDevice(Device):
    DEVICE_TYPES = (
        (u'ios', u'ios'),
        (u'android', u'android'),
        (u'web', u'web')
    )

    device_id = models.CharField(
        verbose_name=_("Device ID"), blank=True, null=True, db_index=True,
        help_text=_("Unique device identifier"),
        max_length=150
    )
    registration_id = models.TextField(verbose_name=_("Registration token"))
    type = models.CharField(choices=DEVICE_TYPES, max_length=10)
    objects = FCMDeviceManager()

    class Meta:
        abstract = True
        verbose_name = _("FCM device")

    def send_message(
            self,
            title=None,
            body=None,
            icon=None,
            data=None,
            sound=None,
            badge=None,
            api_key=None,
            **kwargs):
        """
        Send single notification message.
        """
        from .fcm import fcm_send_message
        result = fcm_send_message(
            registration_id=str(self.registration_id),
            title=title,
            body=body,
            icon=icon,
            data=data,
            sound=sound,
            badge=badge,
            api_key=api_key,
            **kwargs
        )

        self._deactivate_device_on_error_result(result)
        return result

    def send_data_message(
            self,
            condition=None,
            collapse_key=None,
            delay_while_idle=False,
            time_to_live=None,
            restricted_package_name=None,
            low_priority=False,
            dry_run=False,
            data_message=None,
            content_available=None,
            api_key=None,
            timeout=5,
            json_encoder=None):
        """
        Send single data message.
        """
        from .fcm import fcm_send_single_device_data_message
        result = fcm_send_single_device_data_message(
            registration_id=str(self.registration_id),
            condition=condition,
            collapse_key=collapse_key,
            delay_while_idle=delay_while_idle,
            time_to_live=time_to_live,
            restricted_package_name=restricted_package_name,
            low_priority=low_priority,
            dry_run=dry_run,
            data_message=data_message,
            content_available=content_available,
            api_key=api_key,
            timeout=timeout,
            json_encoder=json_encoder,
        )

        self._deactivate_device_on_error_result(result)
        return result

    def _deactivate_device_on_error_result(self, result):
        device = FCMDevice.objects.filter(registration_id=self.registration_id)
        if 'error' in result['results'][0]:
            error_list = ['MissingRegistration', 'MismatchSenderId', 'InvalidRegistration', 'NotRegistered']
            if result['results'][0]['error'] in error_list:
              device.update(active=False)
              self._delete_inactive_device_if_requested(device)

    @staticmethod
    def _delete_inactive_device_if_requested(device):
        if SETTINGS["DELETE_INACTIVE_DEVICES"]:
            device.delete()


class FCMDevice(AbstractFCMDevice):
    class Meta:
        verbose_name = _('FCM device')
        verbose_name_plural = _('FCM devices')

