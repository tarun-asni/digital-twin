from django.db import models


class APIEndpoint(models.Model):
    """Represents a single API endpoint (e.g., GET /cameras/123/stream)"""
    path = models.CharField(max_length=200)
    method = models.CharField(max_length=10)     # GET, POST, etc.
    name = models.CharField(max_length=100, unique=True)  # e.g., 'camera_stream'

    def __str__(self):
        return f"{self.name}"