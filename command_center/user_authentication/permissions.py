from rest_framework import permissions
from django.urls import resolve

from user_authentication.models import APIEndpoint


class HasAPIPermission(permissions.BasePermission):

    def has_permission(self, request, view):
        if not request.user.is_authenticated or not request.user.role:
            return False

        match = resolve(request.path_info)
        endpoint_name = f"{request.method.lower()}_{match.url_name.replace('-', '_')}"

        try:
            endpoint = APIEndpoint.objects.get(name=endpoint_name)
        except APIEndpoint.DoesNotExist:
            return False

        # Check if any of user's role's permissions includes this endpoint
        return request.user.role.permissions.filter(
            api_endpoints=endpoint
        ).exists()
