import logging

from rest_framework import viewsets, status
from django.db.models import Q
from rest_framework.response import Response
from rest_framework.decorators import action

from field_units.models import  Sensor
from field_units.serializers import (  SensorSerializer,  SensorSummarySerializer)
from field_units.decryption_utils import decrypt_payload
from field_units.validate_field_unit import check_device_already_registered

logger = logging.getLogger(__name__)


class SensorViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Sensor operations.
    Provides list, create, retrieve, update, delete operations.
    """
    queryset = Sensor.objects.all()
    serializer_class = SensorSerializer

    def get_serializer_class(self):
        """Use summary serializer for list action"""
        if self.action == 'list':
            return SensorSummarySerializer
        return SensorSerializer

    def get_queryset(self):
        """Filter queryset based on query parameters"""
        queryset = Sensor.objects.all()
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Filter by sensor type
        sensor_type = self.request.query_params.get('sensor_type')
        if sensor_type:
            queryset = queryset.filter(sensor_type=sensor_type)
        
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
        """Get only active sensors"""
        active_sensors = Sensor.objects.filter(is_active=True)
        serializer = SensorSummarySerializer(active_sensors, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a sensor"""
        sensor = self.get_object()
        sensor.is_active = False
        sensor.save()
        return Response({'status': 'sensor deactivated'})

    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Group sensors by type"""
        sensor_types = {}
        for choice in Sensor.SENSOR_TYPE_CHOICES:
            sensor_type = choice[0]
            sensors = Sensor.objects.filter(sensor_type=sensor_type, is_active=True)
            sensor_types[sensor_type] = SensorSummarySerializer(sensors, many=True).data
        return Response(sensor_types)
    
    def create(self, request, *args, **kwargs):
        try:
            data = request.data
            device_id = request.headers.get("Device-Id")

            if check_device_already_registered(device_id=device_id, type="SENSOR"):
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