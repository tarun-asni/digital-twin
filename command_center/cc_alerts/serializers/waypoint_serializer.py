from rest_framework import serializers
from cc_alerts.models import WayPoint


class WayPointSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = WayPoint
        fields = "__all__"
        read_only_fields = ['id']