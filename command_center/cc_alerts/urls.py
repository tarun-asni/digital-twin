from django.urls import path, include
from rest_framework.routers import DefaultRouter

from cc_alerts.views import (
    RequestStreamFromEdge, RequestFeedFromEdge, AllLiveFeedsView, trigger_config_for_detection,
    SensorAlertViewSet, AlertViewSet, ClipUploadView, PathViewSet, WayPointViewSet, DroneFlightViewSet
)

router = DefaultRouter()
router.register(r'alerts', AlertViewSet, basename='alerts')
router.register(r'sensor-alerts', SensorAlertViewSet, basename='sensor-alerts')
router.register(r'paths', PathViewSet, basename='paths')
router.register(r'waypoints', WayPointViewSet, basename='waypoints')
router.register(r'drone-flight', DroneFlightViewSet, basename='drone_flight')

urlpatterns = [
    path('camera/<str:camera_id>/stream/', RequestStreamFromEdge.as_view(), name="stream"),
    path('request-feed/<str:camera_id>/', RequestFeedFromEdge.as_view(), name="request_feed"),
    path('live-feeds/', AllLiveFeedsView.as_view(), name="all_live_feeds"),
    path('<str:device_id>/detection-config/', trigger_config_for_detection, name="send_edge_config"),
    path("clip-upload/", ClipUploadView.as_view(), name="clip_upload"),
    path('', include(router.urls)),
]
