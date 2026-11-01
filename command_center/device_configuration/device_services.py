from common.device import DeviceStatus
from cc_alerts.models import AlertDevice

def update_device_status(alert_device: AlertDevice, status: DeviceStatus=DeviceStatus.ACTIVE, failed: bool=False, failure_reason: str=""):
    device = alert_device.device
    
    if failed:
        alert_device.status = 'failed'
        alert_device.failure_reason = failure_reason or "Unknown failure"
    else:
        alert_device.status = 'uploaded'
    alert_device.save()
    
    device.status = status.value
    device.save()
