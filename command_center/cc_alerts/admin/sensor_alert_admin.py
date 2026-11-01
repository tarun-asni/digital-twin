from django.contrib import admin

from cc_alerts.models import SensorAlert


@admin.register(SensorAlert)
class SensorAlertAdmin(admin.ModelAdmin):
    list_display = ['sensor', 'latitude', 'longitude', 'timestamp']
    list_filter = ['sensor', 'timestamp']
    search_fields = ['sensor', 'timestamp']