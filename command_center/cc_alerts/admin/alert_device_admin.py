from django.contrib import admin

from cc_alerts.models import AlertDevice


@admin.register(AlertDevice)
class AlertDeviceAdmin(admin.ModelAdmin):
    list_display = ['alert', 'device', 'status']
    list_filter = ['alert', 'device', 'status']
    search_fields = ['alert', 'device__name']
