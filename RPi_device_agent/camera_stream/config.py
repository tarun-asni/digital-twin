import os
import sys
from dotenv import load_dotenv
from cryptography.hazmat.primitives import serialization

from datetime import datetime

load_dotenv()

current_script_dir = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT_DIR = os.path.dirname(current_script_dir)
sys.path.append(os.path.join(PROJECT_ROOT_DIR, '..'))
dotenv_path = os.path.join(PROJECT_ROOT_DIR, '.env')
load_dotenv(dotenv_path)

DEVICE_ID = os.getenv("DEVICE_ID")
DEVICE_TYPE = os.getenv("DEVICE_TYPE","")
public_key_filename = f"{DEVICE_ID}_pub.pem"

CLIENT_CERTS_DIR = os.path.join(PROJECT_ROOT_DIR, 'client_certs')
public_key_path = os.path.join(CLIENT_CERTS_DIR, public_key_filename)

APP_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
video_path = os.path.join(APP_BASE_DIR, "videos", "construction.mp4")


def load_public_key():
    try:
        with open(public_key_path, "rb") as f:
            return serialization.load_pem_public_key(f.read())
    except Exception as e:
        print(f"[ERROR] Failed to load public key from {public_key_path}: {e}")
        return None

PUBLIC_KEY = load_public_key()

RECORDINGS_DIR = os.path.join(PROJECT_ROOT_DIR, 'recordings')
os.makedirs(RECORDINGS_DIR, exist_ok=True)

STORAGE_THRESHOLD = 80


MODELS_DIR = os.path.join(BASE_DIR, 'models')

CAMERA_FPS = int(os.getenv("CAMERA_FPS"))
RECORD_DURATION = 30
ALERT_MIN_DURATION = 10
BUFFER_SIZE = 150
ALERT_VIDEO_DURATION = 12
MIN_VIDEO_SIZE_KB = 500

TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"

USE_GPU = False
IS_RESTRICTED = False
SERVER_PORT = 5001

#--------------Alert--------------
COMMAND_CENTER_BASE_URL = os.getenv('COMMAND_CENTER_BASE_URL', '')
ALERT_URL = f'{COMMAND_CENTER_BASE_URL}/cc-alerts/alerts/'
DETECTION_CLASSES = ["NO-Hardhat", "NO-Safety Vest", "NO-Mask"]
ALERT_ENABLED = True

#--------------Camera Type--------------
# Camera type: 'PTZ' or 'FIXED'
CAMERA_TYPE = os.getenv("CAMERA_TYPE", "FIXED")

CAMERA_LAT = float(os.getenv("CAMERA_LAT", "0.0"))
CAMERA_LONG = float(os.getenv("CAMERA_LONG", "0.0"))
CAMERA_ALT = float(os.getenv("CAMERA_ALT", "0.0"))

#------------PTZ capabilities--------------
HAS_PAN = os.getenv("HAS_PAN", "false").lower() == "true"
HAS_TILT = os.getenv("HAS_TILT", "false").lower() == "true"
HAS_ZOOM = os.getenv("HAS_ZOOM", "false").lower() == "true"

INITIAL_PAN = float(os.getenv("INITIAL_PAN", "0"))
INITIAL_TILT = float(os.getenv("INITIAL_TILT", "0"))
INITIAL_ZOOM = float(os.getenv("INITIAL_ZOOM", "0"))

PAN_MIN = float(os.getenv("PAN_MIN", "0"))
PAN_MAX = float(os.getenv("PAN_MAX", "180"))
TILT_MIN = float(os.getenv("TILT_MIN", "-45"))
TILT_MAX = float(os.getenv("TILT_MAX", "45"))
CAMERA_FACING_AZIMUTH = float(os.getenv("CAMERA_FACING_AZIMUTH", "0"))


def is_alert_enabled():
    """
    Check if alert creation is enabled.
    """
    return ALERT_ENABLED

def check_object_detection():
    """
    Check if object detection is enabled.
    This can be modified to include more complex logic if needed.
    """
    return IS_RESTRICTED

def get_detection_classes():
    
    return DETECTION_CLASSES


def device_alive():
    """
    Send initial signal to command center that the device is alive
    """
    
    from utils.RestUtil import RestUtil
    
    COMMAND_CENTER_URL = os.getenv("COMMAND_CENTER_BASE_URL") + f"/device-config/{DEVICE_ID}/active/"
    
    RestUtil.send_data(url=COMMAND_CENTER_URL, method="GET")

def get_time_zone():
    
    now_naive = datetime.now()
    
    local_now_aware = now_naive.astimezone()
    
    local_tzinfo = local_now_aware.tzinfo
    
    local_tzname = local_tzinfo.tzname(local_now_aware)
    
    return local_tzname