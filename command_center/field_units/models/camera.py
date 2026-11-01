import uuid
import math

from typing import Union, Tuple
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class BaseFieldUnit(models.Model):
    """Abstract base model for all field units"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=200, help_text="Friendly name for the unit")
    model = models.CharField(max_length=100, help_text="Model number/name")
    manufacturer = models.CharField(max_length=100, help_text="Manufacturer name")
    serial_number = models.CharField(max_length=100, unique=True, help_text="Unique serial number of the physical device.")
    
    # Geological location
    latitude = models.DecimalField(
        max_digits=10, 
        decimal_places=8,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
        help_text="Latitude in decimal degrees"
    )
    longitude = models.DecimalField(
        max_digits=11, 
        decimal_places=8,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
        help_text="Longitude in decimal degrees"
    )
    altitude = models.FloatField(null=True, blank=True, help_text="Altitude in meters")
    
    # Status and metadata
    is_active = models.BooleanField(default=True, help_text="Whether the unit is currently active")
    installation_date = models.DateField(help_text="Date when the unit was installed")
    last_maintenance = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, help_text="Additional notes about the unit")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True
        ordering = ['name']
    
    @property
    def location(self):
        """
        Returns (latitude, longitude) as floats. Useful for non-GIS distance calculations.
        """
        return (float(self.latitude), float(self.longitude))

    def distance_to(self, other: Union["BaseFieldUnit", Tuple[float, float]], earth_radius_m=6371000) -> float:
        """
        Calculate great-circle distance (meters) between this unit and another unit or (lat, lon) tuple
        using the haversine formula.

        Usage:
            cam1.distance_to(cam2)  # where cam2 is another Camera/BaseFieldUnit
            cam1.distance_to((lat, lon))
        """
        if isinstance(other, tuple) or isinstance(other, list):
            lat2, lon2 = map(float, other)
        else:
            lat2, lon2 = map(float, (other.latitude, other.longitude))

        lat1, lon1 = map(math.radians, (float(self.latitude), float(self.longitude)))
        lat2, lon2 = map(math.radians, (lat2, lon2))

        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return earth_radius_m * c

    def __str__(self):
        return f"{self.name} ({self.model})"


class Camera(BaseFieldUnit):
    """Model for camera field units"""
    CAMERA_TYPE_CHOICES = [
        ('SECURITY', 'Security Camera'),
        ('THERMAL', 'Thermal Camera'),
        ('INFRARED', 'Infrared Camera'),
        ('WILDLIFE', 'Wildlife Camera'),
        ('TIME_LAPSE', 'Time-lapse Camera'),
        ('PTZ', 'Pan-Tilt-Zoom Camera'),
        ('FIXED', 'Fixed Camera'),
    ]
    
    camera_type = models.CharField(
        max_length=20, 
        choices=CAMERA_TYPE_CHOICES,
        help_text="Type of camera"
    )
    resolution = models.CharField(
        max_length=50, 
        help_text="Camera resolution (e.g., 1920x1080, 4K)"
    )
    edge_url = models.CharField(
        max_length=255,
        unique=False,
        blank=True,
        help_text="Edge URL for camera stream"
    )
    field_of_view = models.FloatField(
        null=True, 
        blank=True,
        help_text="Field of view in degrees"
    )
    has_night_vision = models.BooleanField(default=False)
    has_motion_detection = models.BooleanField(default=False)
    zoom_capability = models.CharField(
        max_length=50, 
        blank=True,
        help_text="Zoom specifications (e.g., 10x optical)"
    )
    power_source = models.CharField(
        max_length=50,
        help_text="Power source (e.g., Solar, Battery, AC)"
    )
    
    class Meta:
        verbose_name = "Camera"
        verbose_name_plural = "Cameras"