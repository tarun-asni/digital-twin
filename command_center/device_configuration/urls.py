from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .device_configuration_viewset import active_device, DeviceConfigurationViewSet

router = DefaultRouter()
router.register(r'settings', DeviceConfigurationViewSet, basename='device-config')

urlpatterns = [
    path('<str:device_id>/active/', active_device, name="active_device"),
    path('', include(router.urls)),
]