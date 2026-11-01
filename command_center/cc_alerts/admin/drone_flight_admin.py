from django.contrib import admin

from cc_alerts.models import DroneFlight


@admin.register(DroneFlight)
class DroneFlightAdmin(admin.ModelAdmin):
    list_display = ['start_time', 'end_time']
    list_filter = []
    search_fields = ['drone__name', 'id']