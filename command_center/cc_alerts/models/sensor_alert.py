import uuid

from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from field_units.models import Sensor, Drone, Camera
from cc_alerts.models.alert_status import AlertStatus
from cc_alerts.models import Alert


class SensorAlert(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    sensor = models.ForeignKey(
        Sensor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Sensor referenced to the alert",
    )
    camera = models.ForeignKey(
        Camera,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Camera referenced to the alert",
    )
    alert = models.ForeignKey(
        Alert,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Alert referenced to the sensor alert",
    )

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=8,
        null=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
        help_text="Latitude in decimal degrees",
    )
    longitude = models.DecimalField(
        max_digits=11,
        decimal_places=8,
        null=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
        help_text="Longitude in decimal degrees",
    )

    altitude = models.DecimalField(
        max_digits=11,
        decimal_places=8,
        null=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
        help_text="altitude in decimal degrees",
    )
    
    severity = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical')
        ],
        default='medium',
        help_text="Severity level of the alert",
    )
    
    description = models.TextField(
        max_length=1000,
        null=True,
        blank=True,
        help_text="Detailed description of the sensor alert",
    )
    
    llm_response = models.TextField(
        null=True,
        blank=True,
        help_text="LLM response data related to the alert",
    )

    drone = models.ForeignKey(
        Drone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Drone referenced to the alert",
    )

    status = models.CharField(
        max_length=20, choices=AlertStatus.choices, default=AlertStatus.ACTIVE
    )

    timestamp = models.DateTimeField(
        default=timezone.now, help_text="When the alert was recorded."
    )
    end_time = models.DateTimeField(
        null=True, blank=True, help_text="When the alert was resolved."
    )
    
    is_resolved = models.BooleanField(default=False, help_text="Whether the alert has been resolved by an operator.")
    resolved_at = models.DateTimeField(null=True, blank=True, help_text="When the alert was marked as resolved.")
    resolution_notes = models.TextField(blank=True, null=True, help_text="Notes on how the alert was resolved.")

    class Meta:
        verbose_name = "Sensor Alert"
        verbose_name_plural = "Sensor Alerts"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] Sensor Alert"
