import os
import sys
import json
import logging
from requests.auth import HTTPBasicAuth
from .. import config


logger = logging.getLogger(__name__)

COMMAND_CENTER_URL = os.getenv("COMMAND_CENTER_BASE_URL")

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from utils.RestUtil import RestUtil

username = os.getenv("APP_USERNAME")
password = os.getenv("APP_PASSWORD")

def handle_detection_trigger(msg):
    try:
        logger.info("entered subscription of detection-trigger")
        payload = json.loads(msg.payload.decode())
        camera_id = msg.topic.split("/")[1]
        logger.info(f"camera_id : {camera_id}")
        state = payload.get("state", "false").lower()
        config.IS_RESTRICTED = (state == "true")

        logger.info(f"[MQTT] Detection state for {camera_id} set to {config.IS_RESTRICTED}")

        # Send response back to command center
        data = {
            "status": "success",
            "device_id": camera_id,
            "state": state
        }
        auth = HTTPBasicAuth(username, password)
        
        response = RestUtil.send_data(
            url=COMMAND_CENTER_URL + f"/field-units/{camera_id}/trigger-response/", 
            body=data, 
            method="POST",
            auth=auth
        )
        if response.status_code == 200:
                logger.info("Detection state updated and send to command center")
        else:
                logger.error(f"Failed to send updated state: {response.status_code} - {response.text}")

    except Exception as e:
        logger.error(f"[ERROR] Failed to handle trigger-detection message: {e}")