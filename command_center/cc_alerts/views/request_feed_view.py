from rest_framework import views, status
from rest_framework.response import Response

from cc_alerts.tasks import publish_clip_request


class RequestFeedFromEdge(views.APIView):
    """
    Command Center API to request a specific video clip from an edge device.
    Expects: start (ISO timestamp), duration (in seconds)
    GET command-center/cc-alerts/request-feed/<camera_id>/?start=20250627_123400&duration=30
    """

    def get(self, request, camera_id):

        start = request.query_params.get("start")
        duration = request.query_params.get("duration")
        if not start or not duration:
            return Response(
                {"error": "Missing 'start' or 'duration' parameters"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        publish_clip_request(camera_id, start, duration)

        return Response({"message": "Clip request sent via MQTT."}, status=status.HTTP_200_OK)