from django.db import models
from django.db.models import UniqueConstraint
from django.db.models.functions import Lower
from . import Permission


class Role(models.Model):
    """Role assigned to users"""
    name = models.CharField(max_length=50)
    permissions = models.ManyToManyField(Permission, blank=True)

    def __str__(self):
        return self.name
    
    class Meta:
        constraints = [
            UniqueConstraint(
                Lower('name'),
                name='role_name_unique_ci'
            )
        ]