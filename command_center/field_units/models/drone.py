from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from . import BaseFieldUnit


class Drone(BaseFieldUnit):
    """Model for drone field units"""
    DRONE_TYPE_CHOICES = [
        ('QUADCOPTER', 'Quadcopter'),
        ('HEXACOPTER', 'Hexacopter'),
        ('OCTOCOPTER', 'Octocopter'),
        ('FIXED_WING', 'Fixed Wing'),
        ('HYBRID', 'Hybrid (VTOL)'),
    ]
    
    drone_type = models.CharField(
        max_length=20,
        choices=DRONE_TYPE_CHOICES,
        help_text="Type of drone"
    )
    edge_url = models.CharField(
        max_length=255,
        unique=False,
        blank=True,
        help_text="Edge URL for drone"
    )
    max_flight_time = models.IntegerField(
        help_text="Maximum flight time in minutes"
    )
    max_range = models.FloatField(
        help_text="Maximum range in kilometers"
    )
    max_altitude = models.FloatField(
        help_text="Maximum altitude in meters"
    )
    payload_capacity = models.FloatField(
        help_text="Payload capacity in kilograms"
    )
    camera_specs = models.TextField(
        blank=True,
        help_text="Camera specifications if equipped"
    )
    gps_enabled = models.BooleanField(default=True)
    obstacle_avoidance = models.BooleanField(default=False)
    autonomous_flight = models.BooleanField(default=False)
    weather_resistance = models.CharField(
        max_length=50,
        help_text="Weather resistance rating (e.g., IP43)"
    )
    battery_type = models.CharField(
        max_length=50,
        help_text="Battery type and capacity"
    )
    battery_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        null=True,
        blank=True,
        help_text="Battery percentage at time of log"
    )
    is_available = models.BooleanField(default=True, help_text="Whether the drone is available for missions")
    is_in_flight = models.BooleanField(default=False, help_text="Whether the drone is currently in flight")
    is_interrupted = models.BooleanField(default=False, help_text="Whether the drone flight was interrupted (emergency land or RTL)")
    mission_inject = models.BooleanField(default=False, help_text="Whether a new mission is being injected while in flight")
    current_waypoint = models.IntegerField(default=0, help_text="Current waypoint index")
    last_waypoint = models.IntegerField(default=0, help_text="Last waypoint index")
    is_hovering = models.BooleanField(default=False, help_text="Is drone hovering at current waypoint")
    
    class Meta:
        verbose_name = "Drone"
        verbose_name_plural = "Drones"