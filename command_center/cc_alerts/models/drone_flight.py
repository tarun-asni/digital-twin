import uuid

from django.utils import timezone
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from field_units.models import Drone
from cc_alerts.models import SensorAlert
from mediahub.models import MediaFile


class DroneFlight(models.Model):
    """Model for storing drone flight data and telemetry"""

    HEALTH_STATUS_CHOICES = [
        ('EXCELLENT', 'Excellent'),
        ('GOOD', 'Good'),
        ('POOR', 'Poor'),
        ('CRITICAL', 'Critical'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    drone = models.ForeignKey(
        Drone,
        on_delete=models.CASCADE,
        related_name='flights',
        help_text="Associated drone for this flight"
    )
    health = models.CharField(
        max_length=20,
        choices=HEALTH_STATUS_CHOICES,
        default='EXCELLENT',
        help_text="Overall health status of the drone"
    )
    sensor_alert = models.ForeignKey(
        SensorAlert,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='drone_flights',
        help_text="Associated sensor alert for this flight"
    )
    video_file = models.ForeignKey(
        MediaFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='drone_flights',
        help_text="Related media file (image or video) for this flight."
    )
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
        help_text="Target latitude in decimal degrees"
    )
    longitude = models.DecimalField(
        max_digits=11,
        decimal_places=7,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
        help_text="Target longitude in decimal degrees"
    )
    altitude = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="Target altitude in meters"
    )
    hovering_duration = models.DurationField(
        null=True,
        blank=True,
        help_text="Total hovering duration"
    )
    distance_to_target = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Distance to target location in meters"
    )
    start_time = models.DateTimeField(
        default=timezone.now,
        help_text="Flight start timestamp"
    )
    end_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Flight end timestamp"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Drone Flight"
        verbose_name_plural = "Drone Flights"
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['start_time']),
        ]

    def __str__(self):
        drone_name = self.drone.name if self.drone else "Unknown Drone"
        health_display = str(self.get_health_display()) if hasattr(self, 'get_health_display') else str(self.health)
        return f"Flight {self.id} - {drone_name} ({health_display})"

    @property
    def flight_duration(self):
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return None

    @property
    def coordinates(self):
        return (float(self.latitude), float(self.longitude), float(self.altitude))