import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)

class AlertUpdateConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("alert_updates", self.channel_name)
        await self.accept()
        logger.info("WebSocket connection established")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("alert_updates", self.channel_name)
        logger.info("WebSocket connection closed")

    async def _send_alert_message(self, event, message_type):
        """
        Generic helper to send alert-related WebSocket messages.
        
        :param event: The event dict from the channel group (must contain 'message')
        :param message_type: String identifying the alert message type (e.g., 'alert.update')
        """
        message = event['message']
        await self.send(text_data=json.dumps({
            'type': message_type,
            'message': message
        }))
        logger.info(f"WebSocket alert message sent. Action: {message_type}")

    async def alert_update(self, event):
        await self._send_alert_message(event, 'alert.update')

    async def alert_complete(self, event):
        await self._send_alert_message(event, 'alert.complete')
        
    async def drone_alert(self, event):
        await self._send_alert_message(event, 'drone.alert')
    
    async def drone_complete(self, event):
        await self._send_alert_message(event, 'drone.complete')
    
    async def sensor_alert(self, event):
        await self._send_alert_message(event, 'sensor.alert')
    
    async def sensor_complete(self, event):
        await self._send_alert_message(event, 'sensor.complete')

    async def drone_mission(self, event):    
        await self._send_alert_message(event, 'drone.mission')
        
    async def alert_verify(self, event):
        await self._send_alert_message(event, 'alert.verify')