from django.db import models
from django.utils import timezone

from field_units.models import Sensor, Camera


class Path(models.Model):
    
    path = models.CharField(max_length=1000, help_text="Path name.")
    
    sensor = models.ForeignKey(
        Sensor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='Sensor referenced to the alert'
    )
    
    camera = models.ForeignKey(
        Camera,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='Camera referenced to the alert'
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Path {self.path}"