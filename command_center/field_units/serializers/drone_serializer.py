from rest_framework import serializers

from field_units.models import Drone


class DroneSerializer(serializers.ModelSerializer):
    """Serializer for Drone model"""

    class Meta:
        model = Drone
        fields = [
            'id', 'name', 'model', 'manufacturer', 'serial_number',
            'latitude', 'longitude', 'altitude', 'is_active',
            'installation_date', 'last_maintenance', 'notes', 'drone_type', 
            'is_interrupted', 'mission_inject', 'max_flight_time', 'max_range',
            'is_available', 'is_in_flight', 'edge_url',
            'max_altitude', 'payload_capacity', 'camera_specs',
            'gps_enabled', 'obstacle_avoidance', 'autonomous_flight',
            'weather_resistance', 'battery_type', 'battery_percentage',
            'current_waypoint', 'last_waypoint', 'is_hovering',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class DroneSummarySerializer(serializers.ModelSerializer):
    """Summary serializer for Drone listing"""
    
    class Meta:
        model = Drone
        fields = [
            'id', 'name', 'model', 'manufacturer', 'serial_number',
            'latitude', 'longitude', 'is_active', 'drone_type',
            'installation_date'
        ] 