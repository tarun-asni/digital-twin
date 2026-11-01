import sys
import os
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from device_configuration.models import Device
from common.device import DeviceStatus


class DeviceStatusService:
    """
    Service to check and update the status of devices based on their heartbeat.
    """
    
    def check_heartbeats(self):
        """
        Checks all devices and updates their status to 'INACTIVE' if their
        heartbeat has not been updated in the last minute.
        """
        one_minute_ago = timezone.now() - (timedelta(minutes=1) + timedelta(seconds=2))
        
        # Find devices that are considered active but have an old heartbeat
        devices_to_update = Device.objects.exclude(
            status__in=[DeviceStatus.INACTIVE.value, DeviceStatus.CREATED.value]
        ).filter(
            Q(heartbeat_time__lt=one_minute_ago) | Q(heartbeat_time__isnull=True)
        )

        updated_devices = []
        for device in devices_to_update:
            device.status = DeviceStatus.INACTIVE.value
            device.save()
            updated_devices.append(device.name)

        return updated_devices


device_status_service = DeviceStatusService()