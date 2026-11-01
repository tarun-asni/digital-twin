from django.db import models
from django.utils import timezone

class MediaFile(models.Model):
    MEDIA_TYPES = (
        ('image', 'Image'),
        ('video', 'Video'),
    )

    file = models.FileField(upload_to='media/%Y/%m/%d/')
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPES)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(default=timezone.now)
    file_size = models.BigIntegerField(help_text='File size in bytes')
    mime_type = models.CharField(max_length=100)
    is_public = models.BooleanField(default=False)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.title} ({self.media_type})"

    def save(self, *args, **kwargs):
        if not self.file_size:
            self.file_size = self.file.size
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        if self.file:
            self.file.delete(save=False)
        super().delete(*args, **kwargs)
