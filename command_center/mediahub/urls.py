from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .media_file_view_set import MediaFileViewSet

router = DefaultRouter()
router.register(r'media', MediaFileViewSet, basename='media')

urlpatterns = [
    path('', include(router.urls)),
] 