import uuid
import logging

from rest_framework import serializers
from cc_alerts.models import Alert

logger = logging.getLogger(__name__)


class AlertSerializer(serializers.ModelSerializer):

    def validate_id(self, value):
        """Ensure provided ID is a valid UUID"""
        try:
            uuid.UUID(str(value))
        except ValueError:
            raise serializers.ValidationError("Invalid UUID format.")
        return value
    
    def create(self, validated_data):
        """
        Only create alert record in POST.
        """
        alert_id = validated_data.get('id')
        if alert_id:
            # Ensure it's a UUID
            validated_data['id'] = uuid.UUID(str(alert_id))
            
        return Alert.objects.create(**validated_data)
    
    class Meta:
        model = Alert
        fields = "__all__"