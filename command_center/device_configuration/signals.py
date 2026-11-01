import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import DeviceConfiguration
from .device_monitor_service import device_monitor_service

logger = logging.getLogger(__name__)


@receiver(post_save, sender=DeviceConfiguration)
def check_device_status_on_config_change(sender, instance, **kwargs):
    """Trigger status check whenever a DeviceConfiguration is saved"""
    
    if instance.device.status == "ACTIVE":
        desired = device_monitor_service.get_desired_device_state(instance)
        logger.info(f"Desired state for device {instance.device.id}: {desired}")
        device_monitor_service.publish_status_update(instance, desired, force=True)