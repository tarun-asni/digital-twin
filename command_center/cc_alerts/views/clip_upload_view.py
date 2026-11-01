import os
import logging

from django.shortcuts import get_object_or_404
from django.conf import settings
from django_q.tasks import async_task
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from mediahub.models import MediaFile
from cc_alerts.models import Alert, AlertDevice

logger = logging.getLogger(__name__)


class ClipUploadView(APIView):
    
    permission_classes = [AllowAny]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def post(self, request):
        file = request.FILES.get("file")
        
        data = request.POST
        if not file:
            data = request.data
        
        camera_id = data.get("camera_id")
        start = data.get("start")
        duration = data.get("duration")
        alert_id = data.get("alert_id")
        
        
        alert = get_object_or_404(Alert, id=alert_id)
        alert_device = AlertDevice.objects.filter(alert=alert, device_id=camera_id).first()
        

        if not file or not camera_id or not start:
            if not file:
                logger.error(f"Missing file for alert: {alert_id}")
                alert_device.video_file_for_process = None
                alert_device.save()
                async_task(
                    'inference_engine.inference_engine.run_inference_for_event',
                    alert_device.id
                )
                return Response({"message": "Request uploaded"}, status=200)
            
            return Response({"error": "Missing file, camera_id, or start"}, status=400)
        
        logger.info(f"Video file returned from edge device for alert: {alert_id}")

        filename = f"clip_{camera_id}_{start}.mp4"
        relative_path = os.path.join("requested_clips", filename)
        final_path = os.path.join(settings.MEDIA_ROOT, relative_path)
        os.makedirs(os.path.dirname(final_path), exist_ok=True)

        with open(final_path, "wb") as f:
            for chunk in file.chunks():
                f.write(chunk)

        media_file = MediaFile.objects.create(
            file=relative_path,
            media_type="video",
            title=f"Requested Clip - Camera {camera_id}",
            description=f"Requested from edge at {start} for {duration} secs",
            file_size=os.path.getsize(final_path),
            mime_type="video/mp4",
            is_public=False,
        )

        alert_device.video_file_for_process = media_file
        alert_device.save()
        
        async_task(
                'inference_engine.inference_engine.run_inference_for_event',
                alert_device.id
            )

        return Response({"message": "File uploaded", "media_id": media_file.id})