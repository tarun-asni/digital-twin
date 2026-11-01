from django.db import models
from . import APIEndpoint


class Permission(models.Model):
    """Logical permission that groups API endpoints"""
    name = models.CharField(max_length=100, unique=True)  # e.g., 'full_access', 'viewer_access'
    description = models.TextField(blank=True)
    api_endpoints = models.ManyToManyField(APIEndpoint, blank=True)

    def __str__(self):
        return self.name