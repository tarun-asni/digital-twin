import logging

from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, action, permission_classes

from common.device import DeviceStatus
from .models import DeviceConfiguration, Device
from .serializers import DeviceConfigurationSerializer

from .device_monitor_service import device_monitor_service

logger = logging.getLogger(__name__)


# Create your views here.
class DeviceConfigurationViewSet(viewsets.ModelViewSet):
    
    serializer_class = DeviceConfigurationSerializer
    queryset = DeviceConfiguration.objects.all()
    
    @action(detail=True, methods=['get'])
    def device(self, request, pk):
        """
        GET command-center/device-config/settings/<device-id>/device/
        """
        
        configs = DeviceConfiguration.objects.filter(device_id=pk)
        serializer = self.get_serializer(configs, many=True)
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes([])
def active_device(request, device_id):
    
    logger.info(f"Device: {device_id} is active")
    try:
        device = Device.objects.get(id=device_id)
        device.status = DeviceStatus.ACTIVE.value
        device.heartbeat_time = timezone.now()
        device.save(update_fields=["status", "heartbeat_time"])
    except Device.DoesNotExist:
        return Response(
            {"error": f"Device {device_id} not found or inactive"},
            status=status.HTTP_404_NOT_FOUND
        )

    configs = DeviceConfiguration.objects.filter(
        device=device,
        status__in=["enabled", "disabled"]
    )

    if not configs.exists():
        return Response(
            {"message": "No active configurations for this device"},
            status=status.HTTP_200_OK
        )

    # Find the first valid config and publish its state
    for config in configs:
        desired_state = device_monitor_service.get_desired_device_state(config)
        device_monitor_service.publish_status_update(config, desired_state, force=True)

        return Response({
            "device_id": str(device.id),
            "config_id": str(config.id),
            "state": "true" if desired_state else "false",
            "start_time": config.start_time,
            "end_time": config.end_time,
            "config_status": config.status,
            "timestamp": timezone.now()
        }, status=status.HTTP_200_OK)

    return Response(
        {"message": "No valid configuration found."}, 
        status=status.HTTP_200_OK
    )