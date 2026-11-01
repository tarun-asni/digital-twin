from django.contrib import admin

from cc_alerts.models import Alert


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = [
        'severity', 'detection_class', 'confidence',
        'alert_analysis', 'start_time', 'is_resolved'
    ]
    list_filter = ['severity', 'is_resolved']
    search_fields = ['id', 'detection_class']