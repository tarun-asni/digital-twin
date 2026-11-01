import logging

from django.db.models import Q
from cc_alerts.models import AlertDevice
from cc_alerts.serializers import AlertSerializer
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action

from field_units.models import Camera
from field_units.decryption_utils import decrypt_payload
from field_units.serializers import (  CameraSerializer,CameraSummarySerializer )
from field_units.validate_field_unit import check_device_already_registered

logger = logging.getLogger(__name__)


class CameraViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Camera operations.
    Provides list, create, retrieve, update, delete operations.
    """
    queryset = Camera.objects.all()
    serializer_class = CameraSerializer

    def get_serializer_class(self):
        """Use summary serializer for list action"""
        if self.action == 'list':
            return CameraSummarySerializer
        return CameraSerializer

    def get_queryset(self):
        """Filter queryset based on query parameters"""
        queryset = Camera.objects.all()
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Filter by camera type
        camera_type = self.request.query_params.get('camera_type')
        if camera_type:
            queryset = queryset.filter(camera_type=camera_type)
        
        # Search by name or model
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(model__icontains=search) |
                Q(manufacturer__icontains=search)
            )
        
        return queryset.order_by('name')

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get only active cameras"""
        active_cameras = Camera.objects.filter(is_active=True)
        serializer = CameraSummarySerializer(active_cameras, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a camera"""
        camera = self.get_object()
        camera.is_active = False
        camera.save()
        return Response({'status': 'camera deactivated'})
    
    def retrieve(self, request, *args, **kwargs):
        """
        GET /cameras/<pk>/
        Custom logic before / after the default behaviour.
        """
        pk = kwargs.get("pk")
        camera = self.get_queryset().get(pk=pk)

        alert_devices = AlertDevice.objects.filter(device_id=camera.id)
        alerts_data = [build_alert_data_with_video(alert_device) for alert_device in alert_devices]

        serializer = self.get_serializer(camera)
        data = serializer.data
        data['alerts'] = alerts_data

        return Response(data, status=status.HTTP_200_OK)
    
    def create(self, request, *args, **kwargs):
        try:
            data = request.data
            device_id = request.headers.get("Device-Id")

            if check_device_already_registered(device_id=device_id, type="CAMERA"):
                return Response({"message": "Device already registered"}, status=status.HTTP_200_OK)

            if "enc_key" in data and "enc_payload" in data:
                # Decrypt incoming payload
                decrypted_data = decrypt_payload(data["enc_key"], data["enc_payload"], device_id)
                logger.info(f"Decrypted Camera Payload: {decrypted_data}")
            else:
                return Response(
                    {"error": "Missing required fields: 'enc_key' and/or 'enc_payload'"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = self.get_serializer(data=decrypted_data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

        except Exception as e:
            logger.error(f"Failed to create camera: {e}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


def build_alert_data_with_video(alert_device: AlertDevice):
    alert = alert_device.alert
    video_file = alert_device.video_file

    alert_data = AlertSerializer(alert).data
    
    if video_file:
        alert_data['video_url'] = video_file.file.url
    
    return alert_data