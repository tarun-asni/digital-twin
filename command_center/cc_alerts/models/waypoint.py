from django.db import models
from django.utils import timezone

from cc_alerts.models import Path


class WayPoint(models.Model):
    
    latitude = models.DecimalField(max_digits=12, decimal_places=8)
    longitude = models.DecimalField(max_digits=12, decimal_places=8)
    altitude = models.FloatField(null=True, blank=True)
    hover_duration = models.FloatField(null=True, blank=True, help_text="Hover duration in seconds")
    
    path = models.ForeignKey(
        Path,
        on_delete=models.CASCADE, 
        null=True,
        blank=True,
        related_name='waypoints'
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)