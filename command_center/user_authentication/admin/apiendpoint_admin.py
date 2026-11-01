from django.contrib import admin

from user_authentication.models import APIEndpoint
from user_authentication.models import Permission


class APIEndpointInline(admin.TabularInline):
    model = Permission.api_endpoints.through
    extra = 0
    verbose_name = "API Endpoint"
    verbose_name_plural = "API Endpoints"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('apiendpoint')

    def api_endpoint_name(self, obj):
        return obj.apiendpoint.name
    api_endpoint_name.short_description = "Name"

    def api_endpoint_method(self, obj):
        return obj.apiendpoint.method
    api_endpoint_method.short_description = "Method"

    def api_endpoint_path(self, obj):
        return obj.apiendpoint.path
    api_endpoint_path.short_description = "Path"

    fields = ('api_endpoint_name', 'api_endpoint_method', 'api_endpoint_path')
    readonly_fields = ('api_endpoint_name', 'api_endpoint_method', 'api_endpoint_path')

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(APIEndpoint)
class APIEndpointAdmin(admin.ModelAdmin):
    list_display = ['name', 'method', 'path', 'linked_permissions']
    search_fields = ['name', 'path']
    list_filter = ['method']
    readonly_fields = ['name', 'method', 'path']
    
    def linked_permissions(self, obj):
        permissions = obj.permission_set.all()  # Reverse M2M lookup
        return ", ".join(p.name for p in permissions) if permissions else "-"
    linked_permissions.short_description = "Permissions"
    