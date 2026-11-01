from django.db import models

from cc_alerts.models import AlertDevice


# Create your models here.
class  InferenceVideoStatus(models.Model):
    
    start_time = models.DateTimeField()
    start_frame = models.IntegerField(null=True, blank=True, default=0)
    end_frame = models.IntegerField(null=True, blank=True, default=0)
    total_frames = models.IntegerField(null=True, default=0)
    clip_count = models.IntegerField(null=True, default=0)
    clip_list = models.JSONField(default=list)
    state = models.CharField(null=True, blank=True)
    fps = models.FloatField(null=True, blank=True, default=20.0)
    frame_width = models.IntegerField(null=True, blank=True, default=0)
    frame_height = models.IntegerField(null=True, blank=True, default=0)
    alert_device = models.ForeignKey(
        AlertDevice, 
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Inference Video Status"
        verbose_name_plural = "Inference Video Status"
    
    def add_clip_at_end(self, media_file):
        """Append at the end"""
        self.clip_list.append(media_file.id)
        self.clip_count = len(self.clip_list)
        self.save(update_fields=["clip_list", "clip_count", "updated_at"])

    def add_clip_at_start(self, media_file):
        """Prepend at the start"""
        self.clip_list.insert(0, media_file.id)
        self.clip_count = len(self.clip_list)
        self.save(update_fields=["clip_list", "clip_count", "updated_at"])

    def get_clips(self):
        """Return actual MediaFile objects in order"""
        from mediahub.models import MediaFile
        return MediaFile.objects.filter(id__in=self.clip_list).order_by(
            models.Case(*[models.When(id=pk, then=pos) for pos, pk in enumerate(self.clip_list)])
        )
