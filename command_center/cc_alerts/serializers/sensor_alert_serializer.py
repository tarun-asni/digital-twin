from rest_framework import serializers
from cc_alerts.models import SensorAlert


class SensorAlertSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = SensorAlert
        fields = "__all__"
        read_only_fields = ['id']