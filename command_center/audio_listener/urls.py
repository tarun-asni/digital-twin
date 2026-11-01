from django.urls import path
from .alerts_by_voice import AlertsByVoice


urlpatterns = [
    path('alerts/', AlertsByVoice.as_view(), name="get_alerts_by_voice"),
] 