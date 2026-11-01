from rest_framework import serializers
from cc_alerts.models import Path


class PathSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Path
        fields = "__all__"
        read_only_fields = ['id']