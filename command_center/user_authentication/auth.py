from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed

from user_authentication.models import User


class CustomJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        try:
            user_id = validated_token['user_id']
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise InvalidToken('User not found')
        except Exception:
            raise AuthenticationFailed('Token invalid')