from rest_framework import serializers

from cc_alerts.models import AlertDevice

class AlertDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertDevice
        fields = "__all__"