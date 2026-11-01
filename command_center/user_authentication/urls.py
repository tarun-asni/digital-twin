from django.urls import path, include
from rest_framework.routers import DefaultRouter

from user_authentication.views import (
    LoginView, LogoutView, BootstrapAdminView, CustomTokenRefreshView,
    UserViewSet, RoleViewSet, PermissionViewSet, APIEndpointViewSet
    )

router = DefaultRouter()
router.register(r'auth', UserViewSet, basename='auth')
router.register(r'role', RoleViewSet, basename='role')
router.register(r'permission', PermissionViewSet, basename='permission')
router.register(r'api-endpoint', APIEndpointViewSet, basename='api-endpoint')

urlpatterns = [
    path('', include(router.urls)),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token-refresh'),
    path('bootstrap-admin/', BootstrapAdminView.as_view(), name='bootstrap-admin'),
]