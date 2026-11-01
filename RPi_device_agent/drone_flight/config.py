import os
import logging
from dotenv import load_dotenv
from cryptography.hazmat.primitives import serialization

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

current_script_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT_DIR = os.path.dirname(current_script_dir)
dotenv_path = os.path.join(PROJECT_ROOT_DIR, '.env')
load_dotenv(dotenv_path)
logger.info(f"Loaded environment variables from {dotenv_path}")

DEVICE_ID = os.getenv("DEVICE_ID", "drone-rpi-001").replace(" ", "")
public_key_filename = f"{DEVICE_ID}_pub.pem"
CLIENT_CERTS_DIR = os.path.join(PROJECT_ROOT_DIR, 'client_certs')
public_key_path = os.path.join(CLIENT_CERTS_DIR, public_key_filename)
CLIENT_CERT = os.path.join(CLIENT_CERTS_DIR, f"{DEVICE_ID}_cert.pem")
CLIENT_KEY  = os.path.join(CLIENT_CERTS_DIR, f"{DEVICE_ID}_cert_key.pem")
CA_PUBLIC_CERT_PATH = os.path.join(CLIENT_CERTS_DIR, "rootCA.pem")
def load_public_key():
    try:
        with open(public_key_path, "rb") as f:
            logger.info(f"Loading public key from {public_key_path}")
            return serialization.load_pem_public_key(f.read())
    except Exception as e:
        logger.error(f"Failed to load public key from {public_key_path}: {e}")
        return None

PUBLIC_KEY = load_public_key()

SERIAL_PORT = os.getenv("SERIAL_PORT", "/dev/serial0")
BAUD_RATE = int(os.getenv("BAUD_RATE", "921600"))
HOVER_DURATION = int(os.getenv("HOVER_DURATION", "60"))
TIMESTAMP_FORMAT = "%Y-%m-%d_%H-%M-%S"
COMMAND_CENTER_BASE_URL = os.getenv("COMMAND_CENTER_BASE_URL", "http://localhost:5000/command-center")
COMMAND_CENTER_URL = f"{COMMAND_CENTER_BASE_URL.rstrip('/')}/api/drone"
logger.info(f"Command center URL set to: {COMMAND_CENTER_URL}")

IS_RESTRICTED = False

#-------------------MQTT-----------------#
CERTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "mosquitto", "certs")
)
CA_CERT = CA_PUBLIC_CERT_PATH
SERVER_CERT = CLIENT_CERT
SERVER_KEY = CLIENT_KEY

MQTT_HOST = os.getenv("MQTT_HOST") 
MQTT_PORT = int(os.getenv("MQTT_PORT"))
