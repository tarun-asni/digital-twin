from rest_framework import viewsets

from user_authentication.models import Role
from user_authentication.serializers import RoleSerializer


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer