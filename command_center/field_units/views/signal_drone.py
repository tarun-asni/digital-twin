import ast
import logging

from rest_framework.response import Response        
from rest_framework import  status, views

from cc_alerts.tasks import (
    decrypt_aes_session_key, get_private_key, decrypt_payload_data
    )

logger = logging.getLogger(__name__)


class SignalDrone(views.APIView):
    
    permission_classes = []
    
    def post(self, request, device_id):
        '''
        POST command-center/field-units/<str:device_id>/signal-drone/
        '''
        logger.info('Received post data')
        data = request.data
        enc_aes_key = data.get('enc_aes_key')
        payload = data.get('payload')
        
        logger.info(f"encrypted payload: {payload}")
        
        logger.info('Decrypting payload...')
        
        private_key = get_private_key(device_id=device_id)
        aesgcm = decrypt_aes_session_key(encrypted_key_b64=enc_aes_key, private_key=private_key)
        payload = decrypt_payload_data(aesgcm=aesgcm, payload_b64=payload).decode()
        
        payload = ast.literal_eval(payload)
        
        sensor_id = payload.get('sensor_id')
        latitude = payload.get('latitude')
        longitude = payload.get('longitude')
        
        if not sensor_id or not latitude or not longitude:
            logger.error("Missing sensor_ID or latitude or longitude in decrypted payload.")
            return Response({"error": "Coordinates are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        logger.info(f"\nSensor_ID: {sensor_id}\nLatitude: {latitude}\nLongitude: {longitude}")
        
        # Signal drone to the requested location
        return Response({
            "status": "success",
            "message": f"Drone signaled to latitude {latitude}, longitude {longitude}"
        }, status=status.HTTP_200_OK)
