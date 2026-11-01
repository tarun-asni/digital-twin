from django.contrib import admin

from cc_alerts.models import Path


@admin.register(Path)
class PathAdmin(admin.ModelAdmin):
    list_display = ['path', 'sensor']
    list_filter = ['sensor']
    search_fields = ['sensor', 'path']