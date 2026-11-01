import logging

from django.http import Http404
from django.core.exceptions import PermissionDenied, BadRequest
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.exceptions import InvalidToken

logger = logging.getLogger(__name__)


def handle_exceptions(exc, context):
    """
    Custom exception handler logic.
    """

    request = context.get('request')
    
    if not request.path.startswith('/command-center/'):
        return None
    
    response = exception_handler(exc, context)

    if isinstance(exc, InvalidToken):
        detail = getattr(exc, "detail", {"detail": str(exc)})

        message = None

        if isinstance(detail, dict) and "detail" in detail:
            message = detail["detail"]

        elif "messages" in detail and isinstance(detail["messages"], list):
            msg_obj = detail["messages"][0]
            if isinstance(msg_obj, dict):
                message = msg_obj.get("message")

        if not message:
            message = "Token is invalid or expired"

        logger.error(message)

        return Response(
            data={"detail": message, "code": "token_not_valid"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    elif isinstance(exc, Http404):
        response = Response({}, status=status.HTTP_200_OK)
        logger.error(f"API 404: {request.path if request else 'Unknown path'}")
    
    elif isinstance(exc, PermissionDenied):
        response = Response({'error': 'Permission denied', 'status_code': 403}, status=status.HTTP_403_FORBIDDEN)
        logger.error("API PermissionDenied error")
    
    elif isinstance(exc, BadRequest):
        response = Response({'error': 'Bad request', 'status_code': 400}, status=status.HTTP_400_BAD_REQUEST)
        logger.error("API BadRequest error")
    
    # Handle any other unexpected server errors
    elif response is None:
        logger.error(f"API Server Error: {exc}", exc_info=True)
        response = Response({'error': 'Internal server error', 'status_code': 500}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return response