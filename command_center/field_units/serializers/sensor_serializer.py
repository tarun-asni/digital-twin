from rest_framework import serializers

from field_units.models import Sensor


class SensorSerializer(serializers.ModelSerializer):
    """Serializer for Sensor model"""
    
    class Meta:
        model = Sensor
        fields = [
            'id', 'name', 'model', 'manufacturer', 'serial_number',
            'latitude', 'longitude', 'altitude', 'is_active', 
            'installation_date', 'last_maintenance', 'notes',
            'sensor_type', 'measurement_unit', 'measurement_range',
            'accuracy', 'sampling_rate', 'power_consumption',
            'communication_protocol',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

class SensorSummarySerializer(serializers.ModelSerializer):
    """Summary serializer for Sensor listing"""
    
    class Meta:
        model = Sensor
        fields = [
            'id', 'name', 'model', 'manufacturer', 'serial_number',
            'latitude', 'longitude', 'is_active', 'sensor_type',
            'installation_date'
        ]