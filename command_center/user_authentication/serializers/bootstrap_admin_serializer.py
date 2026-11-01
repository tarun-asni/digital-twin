from rest_framework import serializers

from user_authentication.models import User, Role


class BootstrapAdminSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        extra_kwargs = {
            'email': {'required': True}
        }

    def validate(self, attrs):
        if User.objects.filter(username=attrs['username']).exists():
            raise serializers.ValidationError("Username already taken")
        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError("Email already taken")
        return attrs

    def create(self, validated_data):
        # Force role=admin and set superuser flags
        role = Role.objects.get(name='admin')
        if not role:
            raise serializers.ValidationError("Role 'admin' does not exist")
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            role=role
        )
        user.is_bootstrap_admin = True
        user.is_superuser = True
        user.is_staff = True
        user.save()
        return user