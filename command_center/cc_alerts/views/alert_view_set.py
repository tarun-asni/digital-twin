import os
import logging

from inference_engine.modify_analysis import modify_analysis
from django_q.tasks import async_task
from django.conf import settings
from rest_framework import  viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from common.device import DeviceStatus

from cc_alerts.models import Alert, AlertDevice, AlertStatus, DroneFlight, SensorAlert
from device_configuration.models import Device
from field_units.models import Camera
from cc_alerts.serializers import AlertSerializer
from cc_alerts.services import AlertManagementService

from rest_framework.permissions import AllowAny
from user_authentication.permissions import HasAPIPermission
from cc_alerts.utils import get_drone_payload
from sensegrid.config import send_ws_update

logger = logging.getLogger(__name__)


class AlertViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows alerts to be viewed or created.
    POST requests are typically from edge devices.
    """
    queryset = Alert.objects.all()
    serializer_class = AlertSerializer
    
    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action not in ['list', 'retrieve', 'update', 'destroy']:
            return [AllowAny()]
        else:
            return [HasAPIPermission()]

    def create(self, request, *args, **kwargs):

        # [x] Save alert
        serializer: AlertSerializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        alert_instance: Alert = serializer.instance
        
        camera_id = request.data.get('camera_id')
        camera = Camera.objects.get(id=camera_id)
        device = Device.objects.get(id=camera_id)
        
        device.status = DeviceStatus.STREAMING.value
        device.save()
        
        # [x] Save Alert Device
        AlertDevice.objects.create(
            alert=alert_instance,
            device=device,
            primary_device=True
        )
        
        # [ ] PTZ control to focus on alert location
        logger.info(f"Requesting nearby cameras to focus on alert {alert_instance.id}")
        AlertManagementService().publish_nearby_cameras(alert=alert_instance, source_camera=camera, radius_meters=70)
        
        headers = self.get_success_headers(serializer.data)
 
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def partial_update(self, request, *args, **kwargs):

        instance = self.get_object()

        data = request.data
        device_id = data.get('device_id')

        alert_device = AlertDevice.objects.filter(alert=instance, device__id=device_id).first()

        total_chunks = int(data.get('total_chunks'))

        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        instance = serializer.instance
        
        alert_data = {
                       "id": str(instance.id),
                       "start_time": instance.start_time.isoformat(),
                       "end_time": instance.end_time.isoformat() if instance.end_time else None,
                      }
        
        if alert_device.primary_device:
            payload = {
                    "alert_id": str(instance.id),
                }
            
            send_ws_update(
                group_name="alert_updates",
                type="alert.complete",
                message=payload
            )
            logger.info(f"WS message sent for alert completion: {instance.id}")
            
            devices = AlertDevice.objects.filter(alert=instance, primary_device=False).values_list('device', flat=True)
            logger.info(f"Resuming nearby cameras for alert {instance.id}")
            AlertManagementService().resume_nearby_cameras(alert_data, devices=devices)
        
        async_task(
                'inference_engine.inference_engine.reassemble_and_process_alert_zip',
                alert_device.id,
                total_chunks
            )

        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['patch'], url_path='update')
    def update_alert(self, request, *args, **kwargs):
        """
        Update an alert instance.
        PATCH /alerts/{id}/update/
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='chunks')
    def chunks(self, request, pk=None):
        """
        POST /alerts/{id}/chunks/
        Handle chunked upload for large ZIP files.
        """
        try:
            instance = self.get_object()
        except Alert.DoesNotExist:
            return Response({"error": "Alert not found"}, status=status.HTTP_404_NOT_FOUND)

        chunk = request.FILES.get('chunk')
        chunk_index = request.data.get('chunk_index')
        total_chunks = request.data.get('total_chunks')
        device_id = request.data.get('device_id')
        
        device = AlertDevice.objects.filter(alert=instance, device__id=device_id).first()

        if device and device.primary_device:
            instance.end_time = request.data.get('end_time')
            instance.save(update_fields=['end_time'])

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
        
        chunk_dir_name = f'alert_{instance.id}_device_{device.device.id}'

        chunk_dir = os.path.join(settings.MEDIA_ROOT, 'alert_chunks', chunk_dir_name)
        os.makedirs(chunk_dir, exist_ok=True)

        chunk_path = os.path.join(chunk_dir, f'chunk_{chunk_index}.bin')

        try:
            with open(chunk_path, 'wb') as f:
                for chunk_part in chunk.chunks():
                    f.write(chunk_part)
        except Exception as e:
            logger.error(f"Failed to save chunk {chunk_index} for alert {instance.id}: {e}")
            return Response(
                {"error": "Failed to save chunk"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        received_chunks = len([
            f for f in os.listdir(chunk_dir)
            if f.startswith('chunk_') and f.endswith('.bin')
        ])

        if received_chunks == total_chunks:
            logger.info(f"All chunks received for alert {instance.id}")

        return Response({
            "status": "Chunk received",
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
            "received_chunks": received_chunks
        }, status=status.HTTP_200_OK)
    
    def list(self, request, *args, **kwargs):
        """
        List all alerts with their associated devices.
        """
        
        alerts = self.get_queryset()
        alerts_data = [AlertManagementService().alert_with_devices(alert) for alert in alerts]
        
        return Response(alerts_data)
    
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific alert with its associated devices.
        """
        
        alert = self.get_object()
        alert_data = AlertManagementService().alert_with_devices(alert)

        return Response(alert_data)
    
    @action(detail=False, methods=['get'], url_path='active-alerts')
    def active_alerts(self, request, *args, **kwargs):
        """
        List all active alerts.
        """
        
        active_alerts = Alert.objects.filter(
            alert_analysis__in=[AlertStatus.ACTIVE]
            )
        alerts_data = [AlertManagementService().alert_with_devices(alert) for alert in active_alerts]
        
        active_sensor_alerts = SensorAlert.objects.filter(
            status=AlertStatus.ACTIVE,
            sensor__isnull=False
        )
        
        sensor_alerts_data = []
        for sensor_alert in active_sensor_alerts:
            
            drone_flight = DroneFlight.objects.filter(sensor_alert=sensor_alert).first()
            
            sensor_alerts_data.append(
                get_drone_payload(
                    drone=drone_flight.drone if drone_flight else None, 
                    drone_flight=drone_flight
                )
            )
        
        payload = {
            "alerts_data": alerts_data,
            "sensor_alerts_data": sensor_alerts_data
        }
        
        return Response(payload)
    
    @action(detail=True, methods=['post'], url_path='update-response')
    def update_llm_response(self, request, pk=None, *args, **kwargs):

        message = ""
        inference_analysis = ""
        
        alert = Alert.objects.filter(id=pk).first()
        
        if alert:
            message = alert.message
            inference_analysis = alert.inference_analysis if alert.inference_analysis else ""
        else:
            alert = SensorAlert.objects.filter(id=pk).first()
            message = alert.description
            inference_analysis = alert.llm_response
            
        modify_analysis(alert=alert, message=message, inference_analysis=inference_analysis)
        
        return Response({"status": "LLM response updated"}, status=status.HTTP_200_OK)