import uuid

from django.db import models
from django.utils import timezone

from mediahub.models import MediaFile
from device_configuration.models import Device
from cc_alerts.models import Alert
from cc_alerts.models.sensor_alert import SensorAlert


class AlertDevice(models.Model):
    """
    Records which camera captured which video for an alert.
    Enables multi-angle video tracking for the same alert.
    """
    STATUS_CHOICES = [
        ('recording', 'Recording'),
        ('uploaded', 'Uploaded'),
        ('failed', 'Failed')
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    alert = models.ForeignKey(
        Alert,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alert_recordings'
    )
    
    sensor_alert = models.ForeignKey(
        SensorAlert,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sensor_alert_recordings',
    )
    
    device = models.ForeignKey(
        Device,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='device_recordings'
    )
    
    video_file = models.ForeignKey(
        MediaFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alert_camera_recordings'
    )
    
    video_file_for_process = models.ForeignKey(
        MediaFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alert_camera_recording_for_process'
    )
    
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='recording')
    
    failure_reason = models.TextField(
        blank=True,
        help_text="Reason for the failure, if any."
    )
    
    primary_device = models.BooleanField(
        default=False,
        help_text="Indicates if this is the primary device for the alert"
    )

    # Recording metadata
    recording_start = models.DateTimeField(default=timezone.now)
    recording_end = models.DateTimeField(null=True, blank=True)

    # Camera position when recording (for PTZ cameras)
    pan_angle = models.FloatField(null=True, blank=True, help_text="Pan angle in degrees")
    tilt_angle = models.FloatField(null=True, blank=True, help_text="Tilt angle in degrees")
    zoom_level = models.FloatField(null=True, blank=True, help_text="Zoom level")
    
    # Angle description for UI
    angle_description = models.CharField(
        max_length=100,
        blank=True,
        help_text="Human-readable description of this camera angle (e.g., 'Front view', 'Side angle')"
    )
    
    class Meta:
        unique_together = ('alert', 'device')
        verbose_name = "Alert Device"
        verbose_name_plural = "Alert Devices"
        ordering = ['-recording_start']

    def __str__(self):
        device_name = self.device.name if self.device else "Unknown"
        return f"{device_name} - Recording for Alert {self.alert.id}"
