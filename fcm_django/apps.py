from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class FcmDjangoConfig(AppConfig):
    name = 'fcm_django'
    verbose_name = _('FCM Django')
