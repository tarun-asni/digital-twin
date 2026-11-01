import json
import logging

from django.http import JsonResponse
from rest_framework import  status, views
from rest_framework.response import Response
from rest_framework.decorators import api_view

from sensegrid.config import publish_mqtt_message

from field_units.models import Camera, Sensor, Drone

logger = logging.getLogger(__name__)


class ValidateFieldUnit(views.APIView):
    
    def get(self, request):

        serial = request.query_params.get('serial')
        logger.info(f"serial number: {serial}")
        camera = Camera.objects.get(serial_number=serial)

        if not camera:
            return Response({'error': 'Camera is not registered'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'id': camera.id,
            'name': camera.name,
            'type': 'camera',
            'serial_number': camera.serial_number
        }, status=status.HTTP_200_OK)


@api_view(['GET'])
def trigger_detection(request, device_id):
    """
    Publishes MQTT message to trigger detection on edge device
    URL: GET /command-center/field-units/<device_id>/trigger-detection/?state=True
    """

    state = request.GET.get('state', 'False').lower()
    
    # camera = get_object_or_404(Camera, pk=device_id) # not using this
    
    logger.info("Entered trigger detection method")
    
    topic = f"device/{device_id}/trigger-detection"
    logger.info(f"publishing to topic name : {topic}")
    payload = json.dumps({"state": state})
    
    publish_mqtt_message(topic, payload, qos=2)
    
    logger.info("Message published")
    return JsonResponse({'status': 'success', 'device_id': device_id, 'state': state}, status=status.HTTP_200_OK)


def check_device_already_registered(device_id: str, type: str):
    """
    Checks if device is already registered
    """
    
    if not device_id or not type:
        return False
    
    if type == "CAMERA":
        return Camera.objects.filter(pk=device_id).first()
    
    elif type == "SENSOR":
        return Sensor.objects.filter(pk=device_id).first()
    
    elif type == "DRONE":
        return Drone.objects.filter(pk=device_id).first()
    
    else:
        return None
