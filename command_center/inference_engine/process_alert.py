import logging

from common.device import DeviceStatus
from cc_alerts.models import Alert, AlertDevice
from sensegrid.config import publish_mqtt_message
from inference_engine.tasks import fetch_video_clip

from device_configuration.device_services import update_device_status

logger = logging.getLogger(__name__)


def process_pending_alert(alert_id):
    """
    Process a pending alert by its ID.
    This function can be expanded to include logic for processing the alert.
    """

    try:
        alert = Alert.objects.get(id=alert_id)
        alert_devices = AlertDevice.objects.filter(alert=alert).filter(status='recording')
        
        for alert_device in alert_devices:
            
            device = alert_device.device
            
            if device.status == DeviceStatus.INACTIVE.value:
                failure_reason = f'Device {device.name} is not responding.'
                update_device_status(alert_device=alert_device, status=DeviceStatus.INACTIVE, failed=True, failure_reason=failure_reason)
                logger.error(failure_reason)
                continue
            
            if alert.start_time and alert.end_time and not alert_device.primary_device:
                # fetch full clip and process it
                logger.info(f'Fetching full video for alert {alert.id} from camera {alert_device.device.name}')
                alert['id'] = str(alert.id)
                alert['start_time'] = alert.start_time.isoformat()
                alert['end_time'] = alert.end_time.isoformat() if alert.end_time else None
                
                publish_fetch_clip(alert, alert_device.device.id)
            else:
                # fetch partial clip and send for inference.
                logger.info(f'Fetching initial video for alert {alert.id} from camera {alert_device.device.name}')
                fetch_video_clip(alert_id=alert.id, camera_id=alert_device.device.id, start_time=alert.start_time, duration=30)
                
    except Alert.DoesNotExist:
        logger.error(f"Alert with ID {alert_id} not found.")
        

def publish_fetch_clip(alert_data, device_id):
    
    topic = f"device/{device_id}/clip/full-clip"
    payload = alert_data
    logger.info(f'Publishing message to {topic}')
    publish_mqtt_message(topic=topic, payload=payload, qos=2)