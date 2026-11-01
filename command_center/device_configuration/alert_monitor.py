from cc_alerts.models import AlertDevice
from django_q.tasks import async_task

def check_pending_alerts():
    """
    Check for pending alerts and process them.
    This function can be expanded to include logic for handling alerts.
    """
    
    pending_alerts = AlertDevice.objects.filter(status='recording')
    
    for alert_device in pending_alerts:
        
       async_task('inference_engine.process_alert.process_pending_alert', alert_device.alert.id)