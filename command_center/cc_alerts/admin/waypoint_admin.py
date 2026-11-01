from django.contrib import admin

from cc_alerts.models import WayPoint


@admin.register(WayPoint)
class WayPointAdmin(admin.ModelAdmin):
    list_display = ['latitude', 'longitude', 'altitude','path']
    list_filter = ['path']
    search_fields = ['path', 'latitude', 'longitude']