from rest_framework import viewsets

from cc_alerts.models import Path
from cc_alerts.serializers import PathSerializer


class PathViewSet(viewsets.ModelViewSet):
    
    queryset = Path.objects.all()
    serializer_class = PathSerializer