import json
import time
import logging
import threading

from .models import DeviceConfiguration, Device
from sensegrid.config import publish_mqtt_message
from django.utils import timezone

logger = logging.getLogger(__name__)

class DeviceMonitorService:
    def __init__(self):
        self.running = False
        self.thread = None
    
    def publish_status_update(self, config: DeviceConfiguration, status: bool, force: bool = False):
        state = "true" if status else "false"
        
        if not force and config.last_published_state == state:
            logger.debug(f"Skipping publish for device {config.device.id}: state unchanged ({state})")
            return

        try:
            detection_topic = f"device/{config.device.id}/trigger-detection"
            payload = json.dumps({"state": state})
            publish_mqtt_message(detection_topic, payload, qos=2)
            logger.info(f"Published state={state} for device {config.device.id} (force={force})")

            # Update without triggering signals
            DeviceConfiguration.objects.filter(id=config.id).update(
                last_published_state=state,
                updated_at=timezone.now()
            )
        except Exception as e:
            logger.error(f"MQTT publish error: {e}")

    def check_all_devices(self):
        active_devices = Device.objects.filter(status='ACTIVE')
        active_configs = DeviceConfiguration.objects.filter(
            device__in=active_devices
        )

        for config in active_configs:
            desired_state = self.get_desired_device_state(config)
            self.publish_status_update(config, desired_state)
    
    def get_desired_device_state(self, config: DeviceConfiguration) -> bool:
        """Compute final desired state based on config status and time window."""
        in_time_window = self.device_in_time_window(config)
        
        if config.status == "enabled":
            return in_time_window
        else:
            return False
    
    def device_in_time_window(self, config: DeviceConfiguration):
        """Check if current time falls within the config time window"""        
        start = config.start_time
        end = config.end_time
        
        if not start or not end:
            return False

        now = timezone.now().time()

        if start <= end:
            return start <= now <= end
        else:
            return now >= start or now <= end
    
    def start_periodic_check(self, interval=5):
        """Start periodic status checking"""
        self.running = True
        
        def check_loop():
            while self.running:
                try:
                    self.check_all_devices()
                except Exception as e:
                    logger.error(f"Error in device status check: {e}")
                time.sleep(interval)
        
        self.thread = threading.Thread(target=check_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop the periodic checking"""
        self.running = False
        if self.thread:
            self.thread.join()


device_monitor_service = DeviceMonitorService()
