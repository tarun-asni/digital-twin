import json
import logging
import traceback

from .. import config
from ..alert_manager import AlertManager
from ..drone_recorder import DroneRecorder
from ..camera import Camera
from ..ptz.ptz_controller import ptz_controller

logger = logging.getLogger(__name__)


def handle_control_message(message):
    try:
        payload = json.loads(message.payload.decode())
        action = payload.get("action")
        logger.info(f"[CONTROL] Received action: {action}")
        
        if action == "monitor_alert":
            
            latitude = float(payload.get("latitude", 0.0))
            longitude = float(payload.get("longitude", 0.0))
            
            ptz_controller.focus_on_location(target_lat=latitude, target_long=longitude)
            config.ALERT_ENABLED = False

        elif action == "resume_alerts":
            
            alert_data = payload.get("alert_data", {})
            ptz_controller.reset_to_initial_position()
            
            config.ALERT_ENABLED = True
            AlertManager().upload_camera_recordings(
                alert_data=alert_data, 
                start_time=alert_data.get("start_time"), 
                end_time=alert_data.get("end_time")
            )
    except Exception as e:
        logger.error(f"[CONTROL] Error handling control message: {e}")
        logger.error(traceback.format_exc())


def handle_recording_message(message):
    try:
        payload = json.loads(message.payload.decode())
        action = payload.get("action")
        logger.info(f"[RECORDING] Received action: {action}")
        
        drone_recorder = DroneRecorder(Camera())
        
        if action == "start":
            drone_recorder.start_recording()
        elif action == "stop":
            drone_recorder.stop_recording()
        else:
            logger.warning(f"[RECORDING] Unknown action: {action}")
    except Exception as e:
        logger.error(f"[RECORDING] Error handling recording message: {e}")