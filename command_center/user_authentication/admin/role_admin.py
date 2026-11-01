from django.contrib import admin

from user_authentication.models import Role


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'permissions_count', 'permissions_list']
    search_fields = ['name']
    filter_horizontal = ['permissions']
    
    def permissions_count(self, obj):
        return obj.permissions.count()
    permissions_count.short_description = "Permission Count"
    permissions_count.admin_order_field = "permissions__count"

    def permissions_list(self, obj):
        """Return a comma-separated string of permission names."""
        return ", ".join(p.name for p in obj.permissions.all()[:5])
    permissions_list.short_description = "Permissions (first 5)"