from django.core.files.storage import default_storage
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import MediaFile
from .serializers import MediaFileSerializer


# Create your views here.
class MediaFileViewSet(viewsets.ModelViewSet):
    queryset = MediaFile.objects.all()
    serializer_class = MediaFileSerializer

    def perform_create(self, serializer):
        file = self.request.FILES.get('file')
        if not file:
            return Response(
                {'error': 'No file provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Determine media type based on file content type
        content_type = file.content_type
        media_type = 'video' if 'video' in content_type else 'image'

        serializer.save(
            media_type=media_type,
            mime_type=content_type,
            file_size=file.size
        )

    @action(detail=True, methods=['delete'])
    def delete_file(self, request, pk=None):
        media_file = self.get_object()
        try:
            # Delete the file from storage
            default_storage.delete(media_file.file.path)
            # Delete the database record
            media_file.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
