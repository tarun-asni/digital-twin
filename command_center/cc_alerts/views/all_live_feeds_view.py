import logging
import requests

from django.shortcuts import get_object_or_404
from django.urls import reverse
from rest_framework import views, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from field_units.models import Camera
from device_configuration.models import Device

logger = logging.getLogger(__name__)


class AllLiveFeedsView(views.APIView):

    def get(self, request):
        feed_data = []
        
        devices = Device.objects.filter(status__in=["ACTIVE", "STREAMING"]).values_list("id", flat=True)
        for cam in Camera.objects.filter(id__in=devices).filter(is_active=True):
            
            feed_data.append({
                "camera_id": cam.id,
                "name": cam.name or f"Camera {cam.id}",
                "stream_url": request.build_absolute_uri(
                    reverse("stream", args=[cam.id])
                ),
                "type": "multipart/x-mixed-replace"
            })
        return Response(feed_data)


@api_view(["POST"])
def trigger_config_for_detection(request, device_id):
    '''
    GET command-center/cc_alerts/<str:device_id>/detection-config/
    
    Detection classes like: ['Person', 'NO-Hardhat', 'NO-Safety Vest']
    '''
    detection_classes = request.data.get("detection_classes")
    start = request.data.get("start")
    end = request.data.get("end")
    
    # No verification added for start and end
    
    # Verify detection_classes
    if not isinstance(detection_classes, list):
        logger.error("Unsupported data type. Expecting list...")
        return Response(
                {"error": "Unsupported data type. Expecting list..."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Verify device
    camera: Camera = get_object_or_404(Camera, pk=device_id)
    
    # Payload creation
    url = f'{camera.edge_url}/get-config'
    data = {
        "detection_classes": detection_classes,
        "start": start,
        "end": end
    }
    
    # Triggering endpoint
    response = requests.post(url, json=data)
    
    # Verifying the response
    if response.status_code != 201:
        logger.error(f"Config not sent: {response.text}")
        return Response(
            {"error": f"Unexpected error, {str(response.text)}"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    logger.info("Config sent successfully!!")
    return Response(
        {"status": "Success", "Message": f"Config sent successfully for Device Id: {device_id}"},
        status=status.HTTP_201_CREATED
    )