from rest_framework import serializers
from cc_alerts.models import DroneFlight
from field_units.serializers import DroneSerializer


class DroneFlightSerializer(serializers.ModelSerializer):

    drone = DroneSerializer(read_only=True)
    sensor_alert = serializers.UUIDField(format='hex_verbose', allow_null=True, source='sensor_alert.id')
    video_file = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = DroneFlight
        fields = "__all__"
        read_only_fields = ['id']