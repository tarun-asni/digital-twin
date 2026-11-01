import logging

from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response

from field_units.models import Camera, Sensor, Drone
from field_units.serializers import CameraSerializer, SensorSerializer, DroneSerializer

from device_configuration.models import Device

logger = logging.getLogger(__name__)


class DeviceListView(APIView):
    """
    GET command-center/field-units/devices/

    Returns the list of registered devices.
    """

    def get(self, request):
        try:
            devices = Device.objects.all()
            # devices = db.query(Device).all()
            device_list = [
                {
                    "id": str(d.id),
                    "name": d.name,
                    "type": d.type,
                    "status": d.status,
                    "created_at": d.created_at.isoformat(),
                    "updated_at": d.updated_at.isoformat(),
                    "heartbeat_time": d.heartbeat_time,
                    "configured_heartbeat_interval": d.configured_heartbeat_interval,
                }
                for d in devices
            ]
            return Response(device_list, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error retrieving device list: {e}")
            return Response(
                {"error": "Failed to fetch devices."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class DeviceDetailsView(APIView):
    """
    GET command-center/field-units/devices/<device_id>/

    Returns the cameras, sensors, and drones linked to the given device_id.
    """

    def get(self, request, device_id):
        # Fetch all linked items
        cameras = Camera.objects.filter(id=device_id)
        sensors = Sensor.objects.filter(id=device_id)
        drones = Drone.objects.filter(id=device_id)

        # Serialize them
        camera_data = CameraSerializer(cameras, many=True).data
        sensor_data = SensorSerializer(sensors, many=True).data
        drone_data = DroneSerializer(drones, many=True).data

        return Response({
            "device_id": device_id,
            "cameras": camera_data,
            "sensors": sensor_data,
            "drones": drone_data
        }, status=status.HTTP_200_OK)