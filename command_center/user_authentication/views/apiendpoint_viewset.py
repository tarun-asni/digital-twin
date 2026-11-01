from rest_framework import viewsets

from user_authentication.models import APIEndpoint
from user_authentication.serializers import APIEndpointSerializer


class APIEndpointViewSet(viewsets.ModelViewSet):
    queryset = APIEndpoint.objects.all()
    serializer_class = APIEndpointSerializer