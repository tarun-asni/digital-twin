
import os
import sys
import time
import shutil
import logging
import platform
import cpuinfo
import requests
import subprocess

from datetime import datetime
from .rpi_utils.file_utils import find_recording_files
from .config import (
    RECORDINGS_DIR, DEVICE_ID, STORAGE_THRESHOLD, TIMESTAMP_FORMAT
)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from utils.RestUtil import RestUtil


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s")
logger = logging.getLogger("video_processor_utils")


def check_storage_and_cleanup():
        try:
            total, used, _ = shutil.disk_usage(RECORDINGS_DIR)
            used_percent = (used / total) * 100
            if used_percent < STORAGE_THRESHOLD:
                logger.info(f"Disk usage {used_percent:.2f}% is below threshold {STORAGE_THRESHOLD}%.")
                return

            logger.warning(f"Disk usage {used_percent:.2f}% exceeds threshold {STORAGE_THRESHOLD}%. Initiating cleanup.")
            files = sorted(
                [os.path.join(RECORDINGS_DIR, f) for f in os.listdir(RECORDINGS_DIR) if f.endswith(".mp4")],
                key=os.path.getctime
            )
            for f in files:
                os.remove(f)
                logger.info(f"[Cleanup] Deleted: {f}")
                total, used, _ = shutil.disk_usage(RECORDINGS_DIR)
                used_percent = (used / total) * 100
                if used_percent < STORAGE_THRESHOLD:
                    logger.info(f"[Cleanup] Disk usage {used_percent:.2f}% now below threshold.")
                    break
        except Exception as e:
            logger.error(f"Error during storage check and cleanup: {e}")


def convert_to_h264(input_path):
    temp_output = input_path.replace(".mp4", "_temp.mp4")

    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", input_path,
            "-loglevel", "error", 
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            temp_output
        ], check=True)

        os.replace(temp_output, input_path)

        logger.debug(f"Converted {input_path} to H.264 successfully")
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg conversion failed: {e}")
        if os.path.exists(temp_output):
            os.remove(temp_output)


async def handle_alert_async(alert_type, video_path, timestamp: datetime, message=None, severity=None, confidence=None):
        
    data = {
        "message": message if message else (
        "A person has entered a restricted area without authorization." 
        if alert_type == "restricted_zone" 
        else "A worker was detected without proper safety gear (helmet, mask, or vest)."),
        "severity": severity if severity else ("high" if alert_type == "restricted_zone" else "medium"),
        "detection_class": alert_type,
        "confidence": confidence if confidence is not None else 1.0,
        "camera_id":  DEVICE_ID,
        "serial_number": os.getenv('SERIAL_NUMBER', 0),
        "latitude": os.getenv('LATITUDE', 0.0),
        "longitude": os.getenv('LONGITUDE', 0.0),
        "timestamp": timestamp.isoformat() 
    }
    
    CC_BASE_URL = os.getenv('COMMAND_CENTER_BASE_URL')
    ALERT_ENDPOINT = f"{CC_BASE_URL}/cc-alerts/alerts/"
    logger.info(f"ALERT_ENDPOINT , {ALERT_ENDPOINT}")

    # POST alert call
    try:
        response=RestUtil.send_data(
            url=f"{ALERT_ENDPOINT}",
            body=data, 
            method="POST",
            payload_type="plain" 
        )            
        response.raise_for_status() 

        if response.status_code == 201:
            alert_id = response.json().get("id", "N/A")
            logger.info(f"ALERT SENT: Alert ID: {alert_id} for type: {alert_type}")
        else:
            logger.warning(f"Alert sent, but received status code {response.status_code}: {response.text}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send alert to {ALERT_ENDPOINT}: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while handling alert: {e}")
        
    time.sleep(30)
    
    if isinstance(timestamp, str):
        timestamp = datetime.strptime(timestamp, TIMESTAMP_FORMAT)
    else:
        timestamp = timestamp.replace(microsecond=0)
    
    files = find_recording_files(timestamp, 30)
    
    with open(files[0], 'rb') as f:
        file_payload = {
            'alert_file': (os.path.basename(files[0]), f, 'video/mp4'),
        }

        # PATCH alert call
        try:                
            response=RestUtil.send_data(
                url=f'{ALERT_ENDPOINT}{alert_id}/',
                files=file_payload, 
                method="PATCH",
                payload_type="plain"
            )  
            if response.status_code == 200:
                logger.info(f"Alert updated successfully with video file: {files[0]}")
            else:
                logger.error(f"Failed to update alert with video file. Status code: {response.status_code}, Response: {response.text}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send PATCH alert to {ALERT_ENDPOINT}: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred while handling alert: {e}")


def is_raspberry_pi():
    try:
        with open("/proc/device-tree/model", "r") as f:
            model = f.read().lower()
            return "raspberry pi" in model
    except FileNotFoundError:
        return False
    

def load_yolo_model(model_path):
    import torch
    from ultralytics import YOLO

    try:
        if torch.cuda.is_available():
            model = YOLO(model_path).to('cuda')
            logger.info("YOLO model initialized on CUDA (NVIDIA GPU).")

        elif torch.backends.mps.is_available() and torch.backends.mps.is_built():
            model = YOLO(model_path).to('mps')
            logger.info("YOLO model initialized on MPS (Apple Silicon GPU).")

        else:
            system = platform.system().lower()
            distro = " ".join(platform.version().lower().split())
            cpu = cpuinfo.get_cpu_info().get("brand_raw", "").lower()

            if "intel" in cpu and "linux" in system and "ubuntu" in distro:
                try:
                    openvino_path = model_path.replace(".pt", "_openvino_model")
                    model = YOLO(openvino_path)
                    logger.info(f"YOLO model initialized with OpenVINO (Intel + Ubuntu): {openvino_path}")
                except Exception as ov_err:
                    logger.warning(f"OpenVINO load failed: {ov_err}. Falling back to CPU.")
                    model = YOLO(model_path)
                    logger.warning("YOLO model initialized on CPU. Expect slower performance.")
            else:
                model = YOLO(model_path)
                logger.info("YOLO model initialized on CPU (OpenVINO skipped).")

    except Exception as e:
        logger.error(f"Error initializing YOLO model: {e}. Falling back to CPU.")
        model = YOLO(model_path)

    return model