import json
import logging

from math import atan2, degrees
# from geopy.distance import geodesic

from sensegrid.config import send_ws_update, publish_mqtt_message

from device_configuration.models import Device

from common.device import DeviceStatus

from cc_alerts.models import Alert, AlertDevice, SensorAlert
from cc_alerts.utils import signal_to_drone
from field_units.models import Camera
from cc_alerts.serializers import AlertSerializer
from field_units.serializers import CameraSummarySerializer

from cc_alerts.views.request_stream_view import check_stream_connection

logger = logging.getLogger(__name__)

SUPPRESS_TOPIC_FMT = "device/{device_id}/control"

class AlertManagementService():
    """
    Manages multi-camera alert coverage.
    Finds nearby cameras and assigns them to monitor alerts.
    """
    
    SEARCH_RADIUS_METERS = 100  # Search nearby cameras within 100m
    MAX_ASSIGNED_CAMERAS = 5  # Maximum cameras per alert
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    

    def publish_nearby_cameras(self, alert: Alert, source_camera: Camera, radius_meters: float=100):
        """
        Publish a list of nearby cameras to monitor the alert.
        """
        # Fetch cameras within radius_meters of source_camera
        devices = Device.objects.exclude(id=source_camera.id).filter(status=DeviceStatus.ACTIVE.value)
        cameras = Camera.objects.filter(id__in=devices.values_list('id', flat=True))
        nearby = []

        for cam in cameras:
            distance = source_camera.distance_to(cam)
            if distance <= radius_meters:
                nearby.append(cam)
                
                # Get or create the corresponding Device
                device = Device.objects.get(id=cam.id)
                
                if check_stream_connection(cam.id):
                    device.status = DeviceStatus.STREAMING.value
                else:
                    device.status = DeviceStatus.FAIL_TO_STREAM.value
                device.save()
                
                AlertDevice.objects.create(
                    alert=alert,
                    device=device
                )
        
        # Build ws payload
        alert_data = self.alert_with_devices(alert)
        send_ws_update(
            message=alert_data,
            group_name="alert_updates",
            type="alert.update"
        )

        payload = {
            "action": "monitor_alert",
            "alert_id": str(alert.id),
            "cameras": [str(cam.id) for cam in nearby],
            "latitude": str(alert.latitude),
            "longitude": str(alert.longitude),
        }
        for cam in nearby:
            self.publish_control(str(cam.id), payload)
        
        # signal one drone
        self._assign_drone_for_alert(alert, source_camera)

    def publish_control(self, device_id: str, payload: dict):
        topic = SUPPRESS_TOPIC_FMT.format(device_id=device_id)
        logger.info(f"Publishing control to {topic}: {payload.get('action')}")
        publish_mqtt_message(topic, json.dumps(payload), qos=2)

    def resume_nearby_cameras(self, alert_data, devices):
        payload = {"action": "resume_alerts", "alert_data": alert_data}
        
        AlertDevice.objects.filter(alert__id=alert_data['id']).update(
            recording_end=alert_data['end_time']
        )
        
        for device_id in devices:
            self.publish_control(str(device_id), payload)
    
    def calculate_camera_angles(self, camera, alert):
        """
        Calculate pan/tilt angles for PTZ camera to focus on alert location.
        
        Args:
            camera: Camera model instance
            alert: Alert model instance
            
        Returns:
            tuple: (pan_angle, tilt_angle)
        """
        camera_loc = (float(camera.latitude), float(camera.longitude))
        alert_loc = (float(alert.latitude), float(alert.longitude))
        
        return self._calculate_angles(camera_loc, alert_loc)
    
    def _calculate_angles(self, camera, alert):
        """Calculate pan/tilt angles for PTZ camera to focus on alert."""
        
        camera_loc = (float(camera.latitude), float(camera.longitude))
        alert_loc = (float(alert.latitude), float(alert.longitude))
        
        dlon = alert_loc[1] - camera_loc[1]
        dlat = alert_loc[0] - camera_loc[0]
        
        pan_angle = degrees(atan2(dlon, dlat))
        tilt_angle = 0  # Would need altitude for accurate tilt
        
        return pan_angle, tilt_angle
    
    def alert_with_devices(self, alert):
    
        alert_data = AlertSerializer(alert).data
        
        alert_devices = AlertDevice.objects.filter(alert=alert)

        devices_data = [
            {
                'id': str(dev.id),
                'alert_id': alert_data['id'],
                'camera': CameraSummarySerializer(Camera.objects.get(id=dev.device.id)).data,
                'camera_name': dev.device.name if dev.device else None,
                'video_url': (
                    dev.video_file.file.url if dev.video_file else "stream_url"
                ),
                'status': dev.device.status,
                'recorded_at': alert_data['start_time'],
                'primary_device': dev.primary_device
            }
            for dev in alert_devices
        ]

        alert_data['devices'] = devices_data
        
        primary_device = alert_devices.filter(primary_device=True).first()
        if primary_device:
            alert_data['video_url'] = primary_device.video_file.file.url if primary_device.video_file else "stream_url"

        return alert_data
    
    def _assign_drone_for_alert(self, alert: Alert, source_camera: Camera):
        
        sensor_alert = SensorAlert.objects.create(
            camera=source_camera,
            latitude=alert.latitude,
            longitude=alert.longitude,
            alert=alert,
            altitude=10
        )
        
        signal_to_drone(camera=source_camera, sensor_alert=sensor_alert, alert_id=alert.id)