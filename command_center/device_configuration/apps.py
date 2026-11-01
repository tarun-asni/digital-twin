from django.apps import AppConfig


class DeviceConfigurationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'device_configuration'

    def ready(self):
        import device_configuration.signals