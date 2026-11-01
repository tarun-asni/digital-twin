from rest_framework import viewsets

from user_authentication.models import User
from user_authentication.serializers import UserSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer