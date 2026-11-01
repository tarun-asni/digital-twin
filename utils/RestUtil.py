import os
import logging
import requests
import json
from dotenv import load_dotenv
from .Encryption_utils import Encryption_utils

current_script_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT_DIR = os.path.dirname(current_script_dir)
dotenv_path = os.path.join(PROJECT_ROOT_DIR, "RPi_device_agent", ".env")

load_dotenv(dotenv_path)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR) 
CERTS_DIR = os.path.join(PROJECT_ROOT,"RPi_device_agent", "client_certs")
os.makedirs(CERTS_DIR, exist_ok=True)

# Explicitly point to the .env inside RPi_device_agent
env_path = os.path.join(PROJECT_ROOT, "RPi_device_agent", ".env")
load_dotenv(dotenv_path=env_path)
DEVICE_ID = os.getenv("DEVICE_ID")
if not DEVICE_ID:
    raise ValueError("DEVICE_ID not found. Check if .env exists and contains DEVICE_ID.")

# Derive mTLS cert paths automatically
CLIENT_CERT = os.path.join(CERTS_DIR, f"{DEVICE_ID}_cert.pem")
CLIENT_KEY  = os.path.join(CERTS_DIR, f"{DEVICE_ID}_cert_key.pem")
CA_PUBLIC_CERT_PATH = os.path.join(CERTS_DIR, "rootCA.pem")

logger = logging.getLogger(__name__)

class RestUtil:
    
    @staticmethod
    def _format_body_for_log(b):
        if b is None:
            return "None"
        try:
            if isinstance(b, dict):
                return "\n" + "\n".join(f"    {k}: {v}" for k, v in b.items())
            elif isinstance(b, str):
                parsed = json.loads(b)
                return "\n" + "\n".join(f"    {k}: {v}" for k, v in parsed.items())
            else:
                return str(b)
        except Exception:
            return str(b)

    @staticmethod
    def send_data(url, body=None, method="POST", payload_type="plain", headers = {"Content-Type": "application/json"}, auth=None, files=None):
        """
        Always uses mTLS.
        payload_type:
          - 'plain': send JSON as-is
          - 'encrypted': encrypt body before sending
        """
       
        logger.info(f"send_data() called url : {url}, body : {body}")
        logger.info("---- API CALL ----")
        logger.info(f"URL: {url}")
        logger.info(f"Method: {method}")
        response=""
        if payload_type == "encrypted":
            # Always load the right public key

            data = Encryption_utils.encrypt(body)

            # Use returned encrypted result directly
            payload = {
                "enc_key": data["enc_key"],
                "enc_payload": data["enc_payload"]
            }

        else:
            payload = body
        if files:
            # Let requests set the correct Content-Type for multipart/form-data
            response= requests.request(
                method=method,
                url=url,
                data=payload,
                files=files,
                cert=(CLIENT_CERT, CLIENT_KEY),
                verify=CA_PUBLIC_CERT_PATH,
                auth=auth
            )
        else:
            logger.info(f"Payload: {json.dumps(payload)}")
            response = requests.request(
                method=method,
                url=url,
                json=payload ,
                headers=headers,
                cert=(CLIENT_CERT, CLIENT_KEY),
                verify=CA_PUBLIC_CERT_PATH,
                auth=auth
            )

        logger.info(f"Status: {response.status_code}")
        try:
            formatted_body = RestUtil._format_body_for_log(response.text)
            logger.info(f"Response: {formatted_body}")
        except Exception:
            logger.error(f"Response Status: {response.status_code}, Reason: {response.reason}")
        logger.info("------------------")

        return response

    