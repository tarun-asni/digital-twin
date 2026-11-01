from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from user_authentication.models import User
from user_authentication.serializers import BootstrapAdminSerializer


class BootstrapAdminView(APIView):
    permission_classes = []

    def post(self, request):
        if User.objects.filter(role__name='admin').exists():
            return Response(
                {"error": "Admin user already exists. This endpoint is disabled."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user_data = request.data
        user_data['is_superuser'] = True
        user_data['is_staff'] = True
        serializer = BootstrapAdminSerializer(data=user_data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Admin user created successfully!"},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)