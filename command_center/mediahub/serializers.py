from rest_framework import serializers
from .models import MediaFile

class MediaFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaFile
        fields = ['id', 'file', 'media_type', 'title', 'description', 
                 'uploaded_at', 'file_size', 'mime_type', 'is_public']
        read_only_fields = ['file_size', 'uploaded_at'] 