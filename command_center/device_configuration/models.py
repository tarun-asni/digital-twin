from django.db import models
from django.core.exceptions import ValidationError


# Create your models here.
class Device(models.Model):
    id = models.UUIDField(primary_key=True)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50)
    status = models.CharField(max_length=50)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)
    heartbeat_time = models.DateTimeField(null=True, blank=True)
    configured_heartbeat_interval = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "devices"
        managed = False
    
    def __str__(self):
        return self.name


class Certificate(models.Model):
    id = models.UUIDField(primary_key=True)
    device = models.ForeignKey(Device, on_delete=models.CASCADE, db_column='device_id')
    cert_data = models.TextField()
    key_data = models.TextField()
    aes_key = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "certificates"
        managed = False


class Key(models.Model):
    id = models.UUIDField(primary_key=True)
    device = models.ForeignKey(Device, on_delete=models.CASCADE, db_column='device_id')
    public_key = models.TextField()
    private_key = models.TextField()
    aes_key = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "keys"
        managed = False
        
    def __str__(self):
        return str(self.id)


class Inventory(models.Model):
    id = models.IntegerField(primary_key=True)
    device = models.ForeignKey(Device, on_delete=models.CASCADE, db_column='device_id')
    hw_data = models.JSONField(null=True)
    sw_data = models.JSONField(null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "inventories"
        managed = False
        
    def __str__(self):
        return f"Inventory for {self.device}"


class DeviceConfiguration(models.Model):
    
    class Status(models.TextChoices):
        ENABLED = "enabled", "Enabled"
        DISABLED = "disabled", "Disabled"

    class PublishedState(models.TextChoices):
        TRUE = "true", "True"
        FALSE = "false", "False"

    device = models.ForeignKey("Device", on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ENABLED
    )
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    last_published_state = models.CharField(
        max_length=10,
        choices=PublishedState.choices,
        default=PublishedState.FALSE,
        blank=True,
        null=True,
        help_text="Tracks last MQTT state published (true/false)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'device_configuration'
        verbose_name = "Device Configuration"
        verbose_name_plural = "Device Configurations"
        ordering = ['-updated_at']
    
    def clean(self):
        if self.start_time == self.end_time:
            raise ValidationError("Start time and end time cannot be the same")
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.device.name} - {self.start_time} to {self.end_time}"