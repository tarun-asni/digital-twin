import logging
import json

from rest_framework import viewsets, status
from django.db.models import Q
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from user_authentication.permissions import HasAPIPermission

from field_units.models import Drone
from field_units.serializers import ( DroneSerializer, DroneSummarySerializer)
from field_units.decryption_utils import decrypt_payload
from cc_alerts.utils import send_emergency_land, send_return_to_launch,publish_mqtt_message
from field_units.validate_field_unit import check_device_already_registered
from sensegrid.config import send_ws_update

logger = logging.getLogger(__name__)


class DroneViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Drone operations.
    Provides list, create, retrieve, update, delete operations.
    """
    queryset = Drone.objects.all()
    serializer_class = DroneSerializer
    
    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action not in ['list', 'create', 'retrieve', 'update', 'destroy']:
            return [AllowAny()]
        else:
            return [HasAPIPermission()]

    def get_serializer_class(self):
        """Use summary serializer for list action"""
        if self.action == 'list':
            return DroneSummarySerializer
        return DroneSerializer

    def get_queryset(self):
        """Filter queryset based on query parameters"""
        queryset = Drone.objects.all()
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Filter by drone type
        drone_type = self.request.query_params.get('drone_type')
        if drone_type:
            queryset = queryset.filter(drone_type=drone_type)
        
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
        """Get only active drones"""
        active_drones = Drone.objects.filter(is_active=True)
        serializer = DroneSummarySerializer(active_drones, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a drone"""
        drone = self.get_object()
        drone.is_active = False
        drone.save()
        return Response({'status': 'drone deactivated'})

    @action(detail=False, methods=['get'])
    def flight_ready(self, request):
        """Get drones that are active and have GPS enabled"""
        ready_drones = Drone.objects.filter(is_active=True, gps_enabled=True)
        serializer = DroneSummarySerializer(ready_drones, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def emergency_land(self, request, pk=None):
        """Trigger emergency landing for a drone"""
        drone = self.get_object()

        try:
            send_emergency_land(drone.id)
            logger.info(f"Emergency land command sent for drone {drone.id}")
            return Response({'status': 'Emergency land command sent successfully'})
        except Exception as e:
            logger.error(f"Failed to send emergency land command for drone {drone.id}: {e}")
            return Response(
                {'error': f'Failed to send emergency land command: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def return_to_launch(self, request, pk=None):
        """Trigger return to launch for a drone"""
        drone = self.get_object()


        try:
            send_return_to_launch(drone.id)
            logger.info(f"RTL command sent for drone {drone.id}")
            return Response({'status': 'RTL command sent successfully'})
        except Exception as e:
            logger.error(f"Failed to send RTL command for drone {drone.id}: {e}")
            return Response(
                {'error': f'Failed to send RTL command: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def create(self, request, *args, **kwargs):
        try:
            data = request.data
            device_id = request.headers.get("Device-Id")

            if check_device_already_registered(device_id=device_id, type="DRONE"):
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

    @action(detail=True, methods=['post'])
    def inject_state(self, request, pk=None):
        """
        Endpoint for drone to notify command center of its inject state.
        """
        drone = self.get_object()
        inject_state = request.data.get("inject_state")
        device_name = request.data.get("device_name", "Unknown Sensor")
        if not inject_state:
            return Response({"error": "inject_state is required"}, status=400)
        payload = {
            "drone_id": str(drone.id),
            "inject_state": inject_state,
            "mission_injection": True,
            "device_name": device_name
        }
        send_ws_update(
                message=payload,
                group_name="alert_updates",
                type="drone.mission",
            )
        return Response({"status": "received", "inject_state": inject_state})

    @action(detail=True, methods=['post'])
    def inject_approval(self, request, pk=None):
        """
        Endpoint for UI to approve/reject mission injection.
        """
        drone = self.get_object()
        approved = request.data.get("approved")
        if approved is None:
            return Response({"error": "approved is required"}, status=400)
        # Relay approval to drone via MQTT
        topic = f"drones/{drone.id}/inject_approval"
        payload = json.dumps({"approved": bool(approved)})
        publish_mqtt_message(topic, payload, qos=2)
        return Response({"status": "sent", "approved": bool(approved)})