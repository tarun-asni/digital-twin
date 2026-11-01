from rest_framework.response import Response
from rest_framework.views import APIView

from .llm_handler import LLMHandler
from .voice_executor import VoiceExecutor
from cc_alerts.serializers import AlertSerializer

from cc_alerts.models import AlertDevice


# Create your views here.
class AlertsByVoice(APIView):
    
    def get(self, request, *args, **kwargs):
        """
        GET command-center/audio-listener/alerts/?command="hello"
        """
        # extract the command
        command_to_llm = request.GET.get("command")
        if not command_to_llm:
            return Response({"error": "Missing 'command' parameter"}, status=400)
        
        # Get the user's timezone from the request headers
        user_timezone = request.headers.get('X-User-Timezone', 'UTC')

        # Call to claude
        llm_result = LLMHandler.call_claude_mcp(command_to_llm)
        
        if not llm_result:
            return Response({"error": "No response from LLM"}, status=500)         
        
        # fetch results
        alerts = VoiceExecutor().handle_llm_result(llm_result, user_timezone)
        if not alerts:
            return Response([], status=404)
        
        alerts_data = AlertSerializer(alerts, many=True).data
        
        for alert in alerts_data:
            alert_device = AlertDevice.objects.filter(alert=alert["id"]).filter(primary_device=True).first()
            if alert_device:
                alert['video_url'] = alert_device.video_file.file.url if alert_device.video_file else None

        
        return Response(alerts_data, status=200)