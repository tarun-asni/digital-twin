from django.contrib import admin

from device_configuration.models import DeviceConfiguration


# Register your models here.
@admin.register(DeviceConfiguration)
class DeviceConfigurationAdmin(admin.ModelAdmin):
    list_display = ['device_name', 'status', 'start_time', 'end_time']
    list_filter = ['device', 'status']
    search_fields = ['device__name', 'status']

    def device_name(self, obj):
        return obj.device.name
    device_name.admin_order_field = 'device__name'
    device_name.short_description = 'Device Name'