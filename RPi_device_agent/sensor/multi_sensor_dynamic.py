import os
import sys
import time
import logging
import RPi.GPIO as GPIO
from dotenv import load_dotenv
 
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from utils.RestUtil import RestUtil
 
# ====================== LOGGING SETUP ======================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s"
)
logger = logging.getLogger(__name__)

current_script_dir = os.path.dirname(os.path.abspath(__file__)) # /sensor

PROJECT_ROOT_DIR = os.path.dirname(current_script_dir) # /RPi_device_agent


dotenv_path = os.path.join(PROJECT_ROOT_DIR, '.env')
logger.info(f"Attempting to load .env from: {dotenv_path}")

if not os.path.exists(dotenv_path):
    logger.error(f"Error: .env file not found at {dotenv_path}. Please ensure it exists in the project root.")
else:
    load_dotenv(dotenv_path)
    logger.info(".env file loaded successfully.")

DEVICE_ID = os.getenv("DEVICE_ID")
COMMAND_CENTER_BASE_URL = os.getenv("COMMAND_CENTER_BASE_URL")

if DEVICE_ID is None:
    raise ValueError("DEVICE_ID is not set! Check .env file content at " + dotenv_path)
if COMMAND_CENTER_BASE_URL is None:
    raise ValueError("COMMAND_CENTER_BASE_URL is not set in the .env file at " + dotenv_path)

logger.info(f"Loaded DEVICE_ID: {DEVICE_ID}")
logger.info(f"Loaded COMMAND_CENTER_BASE_URL: {COMMAND_CENTER_BASE_URL}")

# ========== Logger Setup ==========
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ========== Load .env ==========
SIGNAL_DRONE_URL = f"{COMMAND_CENTER_BASE_URL}/cc-alerts/sensor-alerts/{DEVICE_ID}/signal-drone/"
SEND_INTERVAL = int(os.getenv("SEND_INTERVAL", 10))

# Sensor configuration
MOTION_PINS = list(map(int, os.getenv("MOTION_PINS", "").split(",")))
SENSOR_IDS = os.getenv("SENSOR_IDS", "").split(",")
coords_raw = os.getenv("PRESET_COORDINATES", "")
PRESET_COORDINATES = []

# ========== Validate ==========
if len(SENSOR_IDS) != len(MOTION_PINS):
    logger.critical("Mismatch: SENSOR_IDS and MOTION_PINS count must match.")
    exit(1)

try:
    for pair in coords_raw.split(";"):
        if pair.strip():
            lat, lon, alt = map(float, pair.split(","))
            PRESET_COORDINATES.append({"latitude": lat, "longitude": lon, "altitude": alt})
    if len(PRESET_COORDINATES) != len(SENSOR_IDS):
        raise ValueError("Mismatch between coordinates and sensor count.")
except Exception as e:
    logger.critical(f"Failed to parse coordinates: {e}")
    exit(1)



# ====================== GPIO CONFIG ======================
GPIO.setmode(GPIO.BCM)
for pin in MOTION_PINS:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
# ====================== FUNCTIONS ======================
def send_sensor_data(sensor_id, latitude, longitude, altitude):    
    raw_data = {
        "sensor_id": sensor_id,
        "latitude": latitude,
        "longitude": longitude,
        "altitude": altitude
    }    
    try:
        response=RestUtil.send_data(
                url=f"{SIGNAL_DRONE_URL}",
                body=raw_data, 
                method="POST",
                payload_type="encrypted" 
            )
        response.raise_for_status()
        logger.info(f"? Sent data for {sensor_id}")
    except Exception as e:
        logger.error(f"? Failed to send data for {sensor_id}: {e}")



# ====================== MAIN LOOP ======================
def main():
    logger.info("Starting multi-sensor monitoring loop...")

    try:
        while True:
            for idx, pin in enumerate(MOTION_PINS):
                sensor_id = SENSOR_IDS[idx]
                coords = PRESET_COORDINATES[idx]
                motion = GPIO.input(pin)

                if motion == GPIO.HIGH:
                  time.sleep(0.2)
                  if GPIO.input(pin) == GPIO.HIGH:
                    logger.info(f"?? Motion detected on {sensor_id} (GPIO {pin})")
                    send_sensor_data(sensor_id, coords["latitude"], coords["longitude"], coords["altitude"])
                    time.sleep(1)

            time.sleep(0.5)
    except KeyboardInterrupt:
        logger.info("Stopping sensor loop.")
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()