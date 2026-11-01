from django.utils import timezone
from django.contrib.auth.hashers import check_password
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from user_authentication.models import User

MAX_LOGIN_ATTEMPTS = 5


class LoginView(APIView):
    permission_classes = []

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {"detail": "Username and password are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            try:
                user = User.objects.get(email=username)
            except User.DoesNotExist:
                return Response(
                    {"detail": "No active account found with the given credentials."},
                    status=status.HTTP_401_UNAUTHORIZED
                )

        is_bootstrap_admin = user.is_bootstrap_admin

        if not is_bootstrap_admin and user.is_locked:
            return Response(
                {"detail": "Account locked due to too many failed attempts. Contact administrator."},
                status=status.HTTP_403_FORBIDDEN
            )

        # 🔑 Authenticate password
        if not check_password(password, user.password):
            if not is_bootstrap_admin:
                user.failed_attempt()
                if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
                    user.lock_account()
                    return Response(
                        {"detail": "Account locked due to too many failed attempts. Contact administrator."},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            return Response(
                {"detail": "No active account found with the given credentials."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # ✅ Login successful
        if not user.is_active:
            return Response(
                {"detail": "User account is disabled."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not is_bootstrap_admin:
            user.reset_login_attempts()

        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role.name
        refresh['username'] = user.username
        refresh['email'] = user.email
        
        payload = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
        
        if user.is_superuser:
            payload['is_superuser'] = True

        return Response(payload, status=status.HTTP_200_OK)