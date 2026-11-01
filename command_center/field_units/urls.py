from django.urls import path, include
from rest_framework.routers import DefaultRouter

from field_units.views import (
    CameraViewSet, DroneViewSet, SensorViewSet,
    DeviceListView, DeviceDetailsView, SignalDrone,
    TriggerDetectionResponseView
)
from .validate_field_unit import ValidateFieldUnit,trigger_detection

# Create router and register viewsets
router = DefaultRouter()
router.register(r'cameras', CameraViewSet, basename='cameras')
router.register(r'sensors', SensorViewSet, basename='sensors')
router.register(r'drones', DroneViewSet, basename='drones')

app_name = 'field_units'

urlpatterns = [
    path('', include(router.urls)),
    path('validate/', ValidateFieldUnit.as_view(), name="validate_field_unit"),
    path('<str:device_id>/trigger-detection/', trigger_detection, name='trigger_detection'),
    path('<str:device_id>/signal-drone/', SignalDrone.as_view(), name="signal_drone"),
    path('devices', DeviceListView.as_view(), name="device-list"),
    path('<str:device_id>/trigger-response/', TriggerDetectionResponseView.as_view()),
    path('device/<str:device_id>/',DeviceDetailsView.as_view(),name='device-details'),
] 