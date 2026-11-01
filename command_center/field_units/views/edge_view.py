import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

logger = logging.getLogger(__name__)


class TriggerDetectionResponseView(APIView):
    
    permission_classes = [AllowAny]
    
    def post(self, request, device_id):
        data = request.data
        logger.info(f"Received response from device {device_id}: {data}")
        return Response({"received": True}, status=status.HTTP_200_OK)