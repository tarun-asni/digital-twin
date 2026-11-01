from rest_framework import serializers

from field_units.models import Camera


class CameraSerializer(serializers.ModelSerializer):
    """Serializer for Camera model"""
    
    class Meta:
        model = Camera
        fields = [
            'id', 'name', 'model', 'manufacturer', 'serial_number', 'edge_url',
            'latitude', 'longitude', 'altitude', 'is_active', 
            'installation_date', 'last_maintenance', 'notes',
            'camera_type', 'resolution', 'field_of_view', 
            'has_night_vision', 'has_motion_detection', 
            'zoom_capability', 'power_source',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

class CameraSummarySerializer(serializers.ModelSerializer):
    """Summary serializer for Camera listing"""
    
    class Meta:
        model = Camera
        fields = [
            'id', 'name', 'model', 'manufacturer', 'serial_number', 'edge_url',
            'latitude', 'longitude', 'altitude', 'is_active', 'camera_type',
            'installation_date'
        ]