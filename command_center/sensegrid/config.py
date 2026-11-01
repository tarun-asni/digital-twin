import os
import ssl

import paho.mqtt.client as mqtt

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from dotenv import load_dotenv

load_dotenv()

# LLM config
API_KEY = os.getenv("API_KEY", None)
MCP_URL = os.getenv("MCP_URL", None)
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", None)
ANTHROPIC_VERSION = os.getenv("ANTHROPIC_VERSION", None)

# For pending alerts
HOURLY_TASK_WAIT_TIME = int(os.getenv("HOURLY_TASK_WAIT_TIME", 1))
HEARTBEAT_INTERVAL_MINUTES = int(os.getenv("HEARTBEAT_INTERVAL_MINUTES", 1))


CERTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "certificates")
)

CA_CERT = os.path.join(CERTS_DIR, "rootCA.pem")
CLIENT_CERT = os.path.join(CERTS_DIR, "command_center_cert.pem")
CLIENT_KEY = os.path.join(CERTS_DIR, "command_center_cert_key.pem")

MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", 8883))



def _get_mqtt_client():
    
    client = mqtt.Client(client_id="command_center", clean_session=False)
    client.tls_set(ca_certs=CA_CERT,
                   certfile=CLIENT_CERT,
                   keyfile=CLIENT_KEY,
                   tls_version=ssl.PROTOCOL_TLSv1_2)
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    
    return client


def publish_mqtt_message(topic, payload, qos=2):
    
    mqtt_client = _get_mqtt_client()
    
    mqtt_client.loop_start()
    mqtt_client.publish(topic, payload, qos=qos)
    mqtt_client.loop_stop()
    
    mqtt_client.disconnect()

def send_ws_update(message, group_name, type):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        group_name,  # Must match the group name in your consumer
        {
            "type": type,  # Must match method name in consumer 
            "message": message
        }
    )


# Current count 43 endpoints
API_ENDPOINTS = [
    # Format: (url_name, http_method, description)
    ('logout', 'POST', 'User logout'),
    ('token-refresh', 'POST', 'Refresh access token'),
    
    # List endpoints (/auth/)
    ('auth-list', 'GET', 'List users'),
    ('auth-list', 'POST', 'Create user'),

    # Detail endpoints (/auth/{id}/)
    ('auth-detail', 'GET', 'Retrieve user'),
    ('auth-detail', 'PUT', 'Update user'),
    ('auth-detail', 'PATCH', 'Partially update user'),
    ('auth-detail', 'DELETE', 'Delete user'),
    
    # Device configuration
    ('device-config-list', 'GET', 'List all device configurations'),
    ('device-config-list', 'POST', 'Create a new device configuration'),

    ('device-config-detail', 'GET', 'Retrieve a specific device configuration'),
    ('device-config-detail', 'PUT', 'Update a specific device configuration'),
    ('device-config-detail', 'PATCH', 'Partially update a specific device configuration'),
    ('device-config-detail', 'DELETE', 'Delete a specific device configuration'),
    ('device-config-device', 'GET', 'Retrieve all device configurations for a specific device'),
    
    # List endpoints (/media/)
    ('media-list', 'GET', 'List media files'),
    ('media-list', 'POST', 'Upload media file'),

    # Detail endpoints (/media/{id}/)
    ('media-detail', 'GET', 'Retrieve media file'),
    ('media-detail', 'PUT', 'Update media file'),
    ('media-detail', 'PATCH', 'Partially update media file'),
    ('media-detail', 'DELETE', 'Delete media file'),
    
    # Cameras
    ('cameras-list', 'GET', 'List cameras'),
    ('cameras-list', 'POST', 'Create camera'),
    ('cameras-detail', 'GET', 'Retrieve camera'),
    ('cameras-detail', 'PUT', 'Update camera'),
    ('cameras-detail', 'PATCH', 'Partially update camera'),
    ('cameras-detail', 'DELETE', 'Delete camera'),

    # Sensors
    ('sensors-list', 'GET', 'List sensors'),
    ('sensors-list', 'POST', 'Create sensor'),
    ('sensors-detail', 'GET', 'Retrieve sensor'),
    ('sensors-detail', 'PUT', 'Update sensor'),
    ('sensors-detail', 'PATCH', 'Partially update sensor'),
    ('sensors-detail', 'DELETE', 'Delete sensor'),

    # Drones
    ('drones-list', 'GET', 'List drones'),
    ('drones-list', 'POST', 'Create drone'),
    ('drones-detail', 'GET', 'Retrieve drone'),
    ('drones-detail', 'PUT', 'Update drone'),
    ('drones-detail', 'PATCH', 'Partially update drone'),
    ('drones-detail', 'DELETE', 'Delete drone'),
    
    # cc_alerts/urls.py
    ('trigger_detection', 'GET', 'Trigger detection on edge device'),
    ('device-list', 'GET', 'List all registered devices'),
    ('device-details', 'GET', 'Retrieve device details (cameras, sensors, drones)'),
    
    ('stream', 'GET', 'Proxy MJPEG camera stream'),
    ('all_live_feeds', 'GET', 'List all live camera feeds'),
    
    ('send_edge_config', 'POST', 'Send detection configuration to edge device'),
    
    # Alerts
    ('alerts-list', 'GET', 'List alerts'),
    ('alerts-detail', 'GET', 'Retrieve alert'),
    ('alerts-detail', 'PUT', 'Update alert'),
    ('alerts-detail', 'DELETE', 'Delete alert'),
    
    # Sensor Alerts
    ('sensor-alerts-list', 'GET', 'List sensor alerts'),
    ('sensor-alerts-detail', 'GET', 'Retrieve sensor alert'),
    ('sensor-alerts-detail', 'PUT', 'Update sensor alert'),
    ('sensor-alerts-detail', 'DELETE', 'Delete sensor alert'),
    ('sensor-alerts-signal-drone', 'POST', 'Signal drone for sensor alert'),
    
    ('get_alerts_by_voice', 'GET', 'Get alerts by voice command'),
    
    # Role management (admin-only)
    ('role-list', 'GET', 'List roles'),
    ('role-list', 'POST', 'Create role'),
    ('role-detail', 'GET', 'Retrieve role'),
    ('role-detail', 'PUT', 'Update role'),
    ('role-detail', 'PATCH', 'Partially update role'),
    ('role-detail', 'DELETE', 'Delete role'),

    # Permission management (admin-only)
    ('permission-list', 'GET', 'List permissions'),
    ('permission-list', 'POST', 'Create permission'),
    ('permission-detail', 'GET', 'Retrieve permission'),
    ('permission-detail', 'PUT', 'Update permission'),
    ('permission-detail', 'PATCH', 'Partially update permission'),
    ('permission-detail', 'DELETE', 'Delete permission'),

    # API Endpoint management (admin-only)
    ('api-endpoint-list', 'GET', 'List API endpoints'),
    ('api-endpoint-list', 'POST', 'Create API endpoint'),
    ('api-endpoint-detail', 'GET', 'Retrieve API endpoint'),
    ('api-endpoint-detail', 'PUT', 'Update API endpoint'),
    ('api-endpoint-detail', 'PATCH', 'Partially update API endpoint'),
    ('api-endpoint-detail', 'DELETE', 'Delete API endpoint'),
]