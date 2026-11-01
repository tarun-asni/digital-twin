from django.contrib import admin
from .models import MediaFile

# Register your models here.
@admin.register(MediaFile)
class MediaFileAdmin(admin.ModelAdmin):
    list_display = ('title', 'media_type', 'mime_type', 'file_size', 'uploaded_at', 'is_public')
    search_fields = ('title', 'description')
    list_filter = ('media_type', 'is_public')
    ordering = ('-uploaded_at',)
    