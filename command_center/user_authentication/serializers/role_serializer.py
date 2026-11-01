from rest_framework import serializers
from user_authentication.models import Role


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = '__all__'
    
    def validate_name(self, value):
        # Check for case-insensitive duplicates
        if Role.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError("Role with this name already exists.")
        return value