from django.contrib import admin
from field_units.models import Drone


@admin.register(Drone)
class DroneAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'model', 'manufacturer', 'drone_type', 
        'is_active', 'installation_date', 'latitude', 'longitude'
    ]
    list_filter = [
        'drone_type', 'is_active', 'gps_enabled', 
        'obstacle_avoidance', 'autonomous_flight', 'installation_date'
    ]
    search_fields = ['name', 'model', 'manufacturer', 'serial_number']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'model', 'manufacturer', 'serial_number')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude', 'altitude')
        }),
        ('Drone Specifications', {
            'fields': (
                'drone_type', 'max_flight_time', 'max_range',
                'max_altitude', 'payload_capacity', 'camera_specs',
                'weather_resistance', 'battery_type'
            )
        }),
        ('Capabilities', {
            'fields': (
                'gps_enabled', 'obstacle_avoidance', 'autonomous_flight'
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