from django.contrib import admin
from field_units.models import Camera


@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'model', 'manufacturer', 'camera_type', 'edge_url',
        'is_active', 'installation_date', 'latitude', 'longitude'
    ]
    list_filter = [
        'camera_type', 'is_active', 'has_night_vision', 
        'has_motion_detection', 'installation_date'
    ]
    search_fields = ['name', 'model', 'manufacturer', 'serial_number']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'model', 'manufacturer', 'serial_number', 'edge_url')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude', 'altitude')
        }),
        ('Camera Specifications', {
            'fields': (
                'camera_type', 'resolution', 'field_of_view',
                'has_night_vision', 'has_motion_detection', 
                'zoom_capability', 'power_source'
            )
        }),
        ('Status & Maintenance', {
            'fields': (
                'is_active', 'installation_date', 
                'last_maintenance', 'notes'
            )
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )