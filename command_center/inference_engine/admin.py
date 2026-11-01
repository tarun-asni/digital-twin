from django.contrib import admin

from .models import InferenceVideoStatus


# Register your models here.
@admin.register(InferenceVideoStatus)
class InferenceVideoStatusAdmin(admin.ModelAdmin):
    
    list_display = ['alert_device', 'start_time', 'start_frame', 'end_frame', 'state']
    search_fields = ['alert_device__id']
