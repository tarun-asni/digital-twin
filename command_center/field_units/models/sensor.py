from django.db import models

from . import BaseFieldUnit


class Sensor(BaseFieldUnit):
    """Model for sensor field units"""
    SENSOR_TYPE_CHOICES = [
        ('TEMPERATURE', 'Temperature Sensor'),
        ('HUMIDITY', 'Humidity Sensor'),
        ('SOIL_MOISTURE', 'Soil Moisture Sensor'),
        ('LIGHT', 'Light Sensor'),
        ('PRESSURE', 'Pressure Sensor'),
        ('WIND', 'Wind Sensor'),
        ('RAIN', 'Rain Sensor'),
        ('CO2', 'CO2 Sensor'),
        ('PH', 'pH Sensor'),
        ('MOTION', 'Motion Sensor'),
        ('VIBRATION', 'Vibration Sensor'),
        ('PROXIMITY', 'Proximity Sensor'),
    ]
    
    sensor_type = models.CharField(
        max_length=20,
        choices=SENSOR_TYPE_CHOICES,
        help_text="Type of sensor"
    )
    measurement_unit = models.CharField(
        max_length=20,
        help_text="Unit of measurement (e.g., °C, %, m/s)"
    )
    measurement_range = models.CharField(
        max_length=100,
        help_text="Measurement range (e.g., -40°C to 85°C)"
    )
    accuracy = models.CharField(
        max_length=50,
        help_text="Sensor accuracy (e.g., ±0.5°C)"
    )
    sampling_rate = models.CharField(
        max_length=50,
        help_text="Sampling rate (e.g., 1Hz, every 5 minutes)"
    )
    power_consumption = models.CharField(
        max_length=50,
        help_text="Power consumption (e.g., 3.3V, 10mA)"
    )
    communication_protocol = models.CharField(
        max_length=50,
        help_text="Communication protocol (e.g., LoRaWAN, WiFi, Bluetooth)"
    )
    
    class Meta:
        verbose_name = "Sensor"
        verbose_name_plural = "Sensors"