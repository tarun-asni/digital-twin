from django.contrib import admin
from field_units.models import Sensor


@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'model', 'manufacturer', 'sensor_type', 
        'is_active', 'installation_date', 'latitude', 'longitude'
    ]
    list_filter = [
        'sensor_type', 'is_active', 'installation_date',
        'communication_protocol'
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
        ('Sensor Specifications', {
            'fields': (
                'sensor_type', 'measurement_unit', 'measurement_range',
                'accuracy', 'sampling_rate', 'power_consumption',
                'communication_protocol'
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