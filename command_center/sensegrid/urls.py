"""
URL configuration for sensegrid project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static

from sensegrid.swagger import schema_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('command-center/media/', include('mediahub.urls')),
    path('command-center/field-units/', include('field_units.urls')),
    path('command-center/cc-alerts/', include('cc_alerts.urls')),
    path('command-center/audio-listener/', include('audio_listener.urls')),
    path('command-center/device-config/', include('device_configuration.urls')),
    path('command-center/user-auth/', include('user_authentication.urls')),
    
    # swagger
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    re_path(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    re_path(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)