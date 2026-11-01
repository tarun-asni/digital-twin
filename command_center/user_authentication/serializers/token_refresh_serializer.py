from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.settings import api_settings

from user_authentication.models import User


class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        refresh = RefreshToken(attrs['refresh'])

        try:
            user_id = refresh['user_id']
            user = User.objects.get(id=user_id)
        except (KeyError, User.DoesNotExist):
            raise serializers.ValidationError('Invalid token')

        data = {'access': str(refresh.access_token)}
        
        if api_settings.ROTATE_REFRESH_TOKENS:
            if api_settings.BLACKLIST_AFTER_ROTATION:
                try:
                    refresh.blacklist()
                except AttributeError:
                    pass
            data['refresh'] = str(RefreshToken.for_user(user))

        return data