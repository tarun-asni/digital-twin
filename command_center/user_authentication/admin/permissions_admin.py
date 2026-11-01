from django.contrib import admin

from user_authentication.models import Permission


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'api_endpoints_count']
    search_fields = ['name', 'description']
    filter_horizontal = ('api_endpoints',)

    def api_endpoints_count(self, obj):
        return obj.api_endpoints.count()
    api_endpoints_count.short_description = "Mapped Endpoints"