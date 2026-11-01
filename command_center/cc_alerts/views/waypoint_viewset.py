from rest_framework import viewsets
from cc_alerts.models import WayPoint
from cc_alerts.serializers import WayPointSerializer


class WayPointViewSet(viewsets.ModelViewSet):
    
    queryset = WayPoint.objects.all()
    serializer_class = WayPointSerializer