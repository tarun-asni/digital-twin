import logging
import requests

from django.shortcuts import get_object_or_404
from django.http import StreamingHttpResponse
from rest_framework.response import Response
from rest_framework import views

from cc_alerts.tasks import stream_proxy
from field_units.models import Camera
from device_configuration.models import Device

logger = logging.getLogger(__name__)


class RequestStreamFromEdge(views.APIView):
    """
    GET command-center/cc-alerts/camera/<camera_id>/stream/?annotate=False

    A view that proxies the MJPEG stream from a camera.
    """
    
    permission_classes = []

    def get(self, request, camera_id):
        
        device = Device.objects.filter(id=camera_id, status__in=["ACTIVE", "STREAMING"]).first()
        if not device:
            return Response(
                {"error": "Device not active."},
                status=400
                )

        camera = get_object_or_404(Camera, pk=camera_id)
        annotate = request.query_params.get('annotate', '').lower() == 'true'
        
        stream_url = f"{camera.edge_url}/annotated_feed" if annotate else f"{camera.edge_url}/video_feed"
            
        logger.info(f"annotate : {annotate},  stream_url : {stream_url}")
        
        logger.info(f"Checking connection to camera : {camera_id}")
        
        if not check_stream_connection(camera.id):
            return Response(
                {"error": "Camera stream unavailable"},
                status=503
                )

        return StreamingHttpResponse(
                stream_proxy(stream_url),
                content_type="multipart/x-mixed-replace; boundary=frame",
                headers={
                    "X-Camera-ID": str(camera.id),
                    "X-Accel-Buffering": "no",
                    "Cache-Control": "no-cache",
                },
            )
    
def check_stream_connection(device_id):
    """
    Check if the stream URL is accessible.
    """
    try:
        camera = Camera.objects.get(id=device_id)
        stream_url = f"{camera.edge_url}/video_feed"
        
        resp = requests.get(stream_url, stream=True, timeout=(5, 5), verify=False)
        resp.raise_for_status()
        first_chunk = next(resp.iter_content(4096))
        if b"--frame" not in first_chunk:
            raise ValueError("Invalid stream format")
        resp.close()
        return True
    except Exception as e:
        logger.error("Failed to connect to stream URL %s: %s", stream_url, e)
        return False