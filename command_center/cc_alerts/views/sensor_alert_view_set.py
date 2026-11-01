import json
import logging

from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from user_authentication.permissions import HasAPIPermission

from sensegrid.config import send_ws_update

from cc_alerts.utils import signal_to_drone
from cc_alerts.models import SensorAlert, DroneFlight, AlertStatus, AlertDevice
from cc_alerts.serializers import SensorAlertSerializer
from field_units.serializers import DroneSerializer
from cc_alerts.tasks import (
    get_private_key, decrypt_aes_session_key, decrypt_payload_data
)
from field_units.models import Sensor
from device_configuration.models import Device


logger = logging.getLogger(__name__)


class SensorAlertViewSet(viewsets.ModelViewSet):
    queryset = SensorAlert.objects.all()
    serializer_class = SensorAlertSerializer
    
    def get_permissions(self):
        if self.action == 'signal_drone':
            return [AllowAny()]
        else:
            return [HasAPIPermission()]
    
    def list(self, request, *args, **kwargs):
        """
        Get a list of sensor alerts.
        """
        
        sensor_alerts = SensorAlert.objects.filter(sensor__isnull=False)
        
        payload = []
        for alert in sensor_alerts:
            drone_flight = DroneFlight.objects.filter(sensor_alert=alert).values_list('id', flat=True).first()
            
            payload.append(
                get_sensor_alert_with_devices(alert, drone_flight)
            )
        
        return Response(payload, status=status.HTTP_200_OK)
    
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific sensor alert by ID.
        """
        instance = self.get_object()
        drone_flight_id = DroneFlight.objects.filter(sensor_alert=instance).values_list('id', flat=True).first()
        payload = get_sensor_alert_with_devices(instance, drone_flight_id)
        return Response(payload, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], url_path='signal-drone')
    def signal_drone(self, request, pk=None):
        """
        POST command-center/cc-alerts/sensor-alerts/<id>/signal-drone/
        """
        logger.info('Received POST data')

        if check_latest_alert(pk):
            logger.warning(f"Alert for sensor: {pk} is currently being processed.")
            return Response(
                {"warning": "Alert is currently being processed."},
                status=status.HTTP_200_OK,
            )

        data = request.data
        enc_aes_key = data.get('enc_key')
        enc_payload = data.get('enc_payload')

        if not enc_aes_key or not enc_payload:
            return Response(
                {"error": "Missing encryption fields"},
                status=status.HTTP_400_BAD_REQUEST
            )

        logger.info('Decrypting payload...')

        try:
            private_key = get_private_key(device_id=pk)
            aesgcm = decrypt_aes_session_key(enc_aes_key, private_key)
            plaintext_bytes = decrypt_payload_data(aesgcm, enc_payload)
            payload = json.loads(plaintext_bytes.decode("utf-8"))
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}", exc_info=True)
            return Response({"error": "Failed to decrypt payload."}, status=status.HTTP_400_BAD_REQUEST)

        latitude = payload.get('latitude')
        longitude = payload.get('longitude')
        altitude = payload.get('altitude')

        if not latitude or not longitude or not altitude:
            logger.error("Missing latitude or longitude or altitude in decrypted payload.")
            return Response({"error": "Coordinates are required."}, status=status.HTTP_400_BAD_REQUEST)

        sensor = get_object_or_404(Sensor, pk=pk)
        sensor_alert = SensorAlert.objects.create(
            sensor=sensor, 
            latitude=latitude, 
            longitude=longitude, 
            altitude=altitude,
            description=f"Alert received from sensor: {sensor.name}"
        )
        AlertDevice.objects.create(
            sensor_alert=sensor_alert,
            device=Device.objects.get(id=sensor.id),
            primary_device=True,
        )

        # WebSocket notification for sensor alert
        logger.info(f"Sending WS message for sensor alert: Sensor {sensor_alert.id}")
        send_ws_update(
                message={
                    "sensor_alert_id": str(sensor_alert.id),
                    "sensor_id": str(sensor.id),
                    "sensor_name": sensor.name
                },
                group_name="alert_updates",
                type="sensor.alert"
            )

        logger.info(f"Created SensorAlert: {sensor_alert.id}")
        logger.info(f"\nSensor_ID: {sensor.id}\nLatitude: {latitude}\nLongitude: {longitude}\nAltitude: {altitude}")

        # Signal drone to the requested location
        result = signal_to_drone(sensor_alert, sensor)

        if result is None:
            logger.error('No suitable drone found.')
            return Response({"detail": "No suitable drone found."}, status=status.HTTP_404_NOT_FOUND)

        # If UI approval is required
        if result.get("ui_approval_required"):
            sensor_alert.drone_id = result["drone_id"]
            sensor_alert.save()
            return Response({
                "ui_approval_required": True,
                "drone_id": result["drone_id"],
                "distance": result["distance"],
                "detail": "Nearest drone is in flight. UI approval required for mission injection.",
                "sensor_alert": SensorAlertSerializer(sensor_alert).data
            }, status=status.HTTP_202_ACCEPTED)
        else:
            # Mission assigned to available drone
            sensor_alert.drone_id = result["drone_id"]
            sensor_alert.save()
            return Response({
                "ui_approval_required": False,
                "drone_id": result["drone_id"],
                "distance": result["distance"],
                "detail": "Mission assigned to available drone.",
                "sensor_alert": SensorAlertSerializer(sensor_alert).data
            }, status=status.HTTP_200_OK)


def check_latest_alert(sensor_id) -> bool:
    """
    Check if the latest alert from sensor is currently being processed.
    """

    sensor_alert = (
        SensorAlert.objects.filter(sensor__id=sensor_id).order_by("-timestamp").first()
    )

    return True if sensor_alert and sensor_alert.status == AlertStatus.ACTIVE else False


def get_devices_for_alert(sensor_alert: SensorAlert) -> list:
    """
    Retrieve all devices associated with a given sensor alert.
    """
    alert_devices = AlertDevice.objects.filter(sensor_alert=sensor_alert)
    devices_info = []

    for alert_device in alert_devices:
        devices_info.append({
            "device_id": str(alert_device.id),
            "device_name": alert_device.device.name,
            "primary_device": alert_device.primary_device,
            "status": alert_device.device.status,
            "recording_start": alert_device.recording_start.isoformat() if alert_device.recording_start else None,
            "recording_end": alert_device.recording_end.isoformat() if alert_device.recording_end else None,
            "video_url": alert_device.video_file.file.url if alert_device.video_file else None,
        })

    return devices_info

def get_sensor_alert_with_devices(sensor_alert: SensorAlert, drone_flight: DroneFlight = None):
    """
    Retrieve sensor alert details along with associated devices.
    """
    drone_serializer = DroneSerializer(sensor_alert.drone)
    
    return {
                "sensor_id": str(sensor_alert.sensor.id) if sensor_alert.sensor else None,
                "sensor_alert": str(sensor_alert.id),
                "drone": drone_serializer.data,
                "severity": sensor_alert.severity,
                "status": sensor_alert.status,
                "latitude": sensor_alert.latitude,
                "longitude": sensor_alert.longitude,
                "altitude": sensor_alert.altitude,
                "llm_response": sensor_alert.llm_response,
                "drone_flight_id": str(drone_flight) if drone_flight else None,
                "description": f"Motion detected from {sensor_alert.sensor.name}" if sensor_alert.sensor else "Alert from unknown sensor",
                "timestamp": sensor_alert.timestamp.isoformat() if sensor_alert.timestamp else None,
                "end_time": getattr(sensor_alert, "end_time", None),
                "devices": get_devices_for_alert(sensor_alert),
            }