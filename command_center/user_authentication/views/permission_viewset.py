from rest_framework import viewsets

from user_authentication.models import Permission
from user_authentication.serializers import PermissionSerializer


class PermissionViewSet(viewsets.ModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer