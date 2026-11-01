import os
import logging

from django.conf import settings
from django_q.tasks import async_task
from rest_framework import viewsets
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from sensegrid.config import send_ws_update
from cc_alerts.models import DroneFlight
from cc_alerts.serializers import DroneFlightSerializer
from device_configuration.models import Device
from common.device import DeviceStatus


logger = logging.getLogger(__name__)

class DroneFlightViewSet(viewsets.ModelViewSet):
    
    queryset = DroneFlight.objects.all()
    serializer_class = DroneFlightSerializer
    
    def partial_update(self, request, *args, **kwargs):
        
        instance = self.get_object()

        data = request.data
        
        device = Device.objects.get(id=instance.id)
        device.status = DeviceStatus.ACTIVE.value
        device.save(update_fields=["status"])

        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], url_path='chunks')
    def chunks(self, request, pk=None):
        """
        POST /drone-flight/{id}/chunks/
        Handle chunked upload for large ZIP files.
        """
        try:
            instance = DroneFlight.objects.get(id=pk)
        except DroneFlight.DoesNotExist:
            error_msg = f"DroneFlight with id {pk} does not exist."
            logger.error(error_msg)
            return Response({"error": error_msg}, status=status.HTTP_404_NOT_FOUND)

        chunk = request.FILES.get('chunk')
        chunk_index = request.data.get('chunk_index')
        total_chunks = request.data.get('total_chunks')

        if not all([chunk, chunk_index, total_chunks]):
            return Response(
                {"error": "Missing required fields: chunk, chunk_index, total_chunks"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            chunk_index = int(chunk_index)
            total_chunks = int(total_chunks)
            if chunk_index < 0 or total_chunks <= 0 or chunk_index >= total_chunks:
                raise ValueError("Invalid chunk index or total")
        except (ValueError, TypeError):
            return Response(
                {"error": "chunk_index and total_chunks must be valid integers"},
                status=status.HTTP_400_BAD_REQUEST
            )

        chunk_dir = os.path.join(settings.MEDIA_ROOT, 'chunks', str(instance.id))
        os.makedirs(chunk_dir, exist_ok=True)

        chunk_path = os.path.join(chunk_dir, f'chunk_{chunk_index}.bin')

        try:
            with open(chunk_path, 'wb') as f:
                for chunk_part in chunk.chunks():
                    f.write(chunk_part)
        except Exception as e:
            logger.error(f"Failed to save chunk {chunk_index} for record {instance.id}: {e}")
            return Response(
                {"error": "Failed to save chunk"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        received_chunks = len([
            f for f in os.listdir(chunk_dir)
            if f.startswith('chunk_') and f.endswith('.bin')
        ])

        if received_chunks == total_chunks:
            logger.info(f"All chunks received for flight {instance.id}")
            # Trigger background reassembly + processing (merge + save MediaFile)
            async_task(
                'inference_engine.chunks_handler.reassemble_and_process_chunks',
                instance.id,
                total_chunks
            )
            
            sensor_alert = instance.sensor_alert
            
            alert = sensor_alert.alert if sensor_alert.alert else sensor_alert
            
            # WebSocket notification for completion
            logger.info(f"Sending WS message for drone flight completion: Alert {alert.id}")
            send_ws_update(
                message={
                    "alert_id": str(alert.id) if alert else None,
                    "drone_id": str(instance.drone.id) if instance.drone else None,
                    "drone_flight_id": str(instance.id),
                    "sensor_alert_id": str(sensor_alert.id) if sensor_alert else None,
                    "status": "Drone flight data upload complete"
                },
                group_name="alert_updates",
                type="drone.complete"
            )

        return Response({
            "status": "Chunk received",
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
            "received_chunks": received_chunks
        }, status=status.HTTP_200_OK)

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action in ['end_mission', 'chunks']:
            return [AllowAny()]
        return super().get_permissions()

    @action(detail=True, methods=['patch'], url_path='end-mission')
    def end_mission(self, request, pk=None):
        """
        PATCH /cc-alerts/drone-flight/{id}/end-mission/
        Allows RPi device agent to update end_time without authentication.
        """
        try:
            instance = self.get_object()
        except DroneFlight.DoesNotExist:
            return Response({"error": "DroneFlight not found"}, status=status.HTTP_404_NOT_FOUND)

        end_time = request.data.get('end_time')
        if not end_time:
            return Response({"error": "end_time is required"}, status=status.HTTP_400_BAD_REQUEST)

        instance.end_time = end_time
        instance.save()
        sensor_alert = getattr(instance, 'sensor_alert', None)
        if sensor_alert:
            sensor_alert.end_time = end_time
            sensor_alert.save()

        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)
