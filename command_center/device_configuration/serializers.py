from rest_framework import serializers
from .models import DeviceConfiguration


class DeviceConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceConfiguration
        fields = '__all__'