import os
import sys
import json
import logging

from datetime import datetime

from camera_stream.config import TIMESTAMP_FORMAT
from camera_stream.rpi_utils.file_utils import find_recording_files
from camera_stream.alert_manager import AlertManager
from camera_stream.rpi_utils.time_converter import time_converter

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from utils.RestUtil import RestUtil

logger = logging.getLogger(__name__)

COMMAND_CENTER_URL = os.getenv("COMMAND_CENTER_BASE_URL")


def handle_clip_request(msg):
    try:
        payload = json.loads(msg.payload.decode())
        start = payload.get("start")
        duration = payload.get("duration")
        alert_id = payload.get("alert_id")
        camera_id = msg.topic.split("/")[1]  # Extract camera_id from topic

        if not start or not duration:
                logger.error("Missing 'start' or 'duration' in MQTT payload")
                return

        start = time_converter.from_iso_format(start)
        start = time_converter.utc_to_local(start, naive=True)
        
        try:
            start_time = datetime.strptime(start, TIMESTAMP_FORMAT)
        except ValueError:
                logger.error(f"Invalid timestamp format. Expected {TIMESTAMP_FORMAT}")
                return

        logger.info(f"[ClipHandler] Clip requested for camera {camera_id}: start={start}, duration={duration}")

        # logic to find/send the clip
        matching_files = find_recording_files(start_time, int(duration))
        if not matching_files:
                logger.error("No recordings found in the specified time range.")
                send_clip_to_command_center(None, start, duration, camera_id, alert_id)
        else:
                logger.info(f"Found file: {matching_files[0]}")
                logger.info(f"[ClipHandler] Found {len( matching_files)} matching clips.")
                send_clip_to_command_center(matching_files[0], start, duration, camera_id, alert_id)
    except Exception as e:
        logger.error(f"[ClipHandler] Failed to handle clip request: {str(e)}")

def send_clip_to_command_center(video_path, start, duration, camera_id, alert_id):
    
    data = {
                "camera_id": camera_id,
                "start": start,
                "duration": duration,
                "alert_id": alert_id
            }
    
    url = COMMAND_CENTER_URL + "/cc-alerts/clip-upload/"
    
    if video_path is None:
        return RestUtil.send_data(url, body=data, method="POST")
    
    try:
        with open(video_path, "rb") as video_file:
            files = {
                "file": (os.path.basename(video_path), video_file, "video/mp4")
            }
            
            logger.info(f"Sending clip {video_path} to command center...")
            response = RestUtil.send_data(url, body=data, files=files, method="POST")

            if response.status_code == 200:
                logger.info(f"Clip uploaded successfully. For alert: {str(alert_id)}")
            else:
                logger.error(f"Failed to upload clip: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Failed to send video to command center: {e}", exc_info=True)

def upload_full_clip(msg):

    try:
        payload = json.loads(msg.payload.decode())
        alert_data = payload.get("alert_data", {})
        start_time = alert_data.get("start_time")
        end_time = alert_data.get("end_time")
        
        AlertManager().upload_camera_recordings(alert_data=alert_data, start_time=start_time, end_time=end_time)
    except Exception as e:
        logger.error(f"Failed to upload full clip: {e}", exc_info=True)
