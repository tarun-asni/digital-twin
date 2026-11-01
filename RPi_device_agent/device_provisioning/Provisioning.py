import os
import sys
import json
import re
import logging
import time
from dotenv import load_dotenv
import schedule
import threading
from requests.auth import HTTPBasicAuth
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from utils.RestUtil import RestUtil
from .payload_loader import PayloadLoader

load_dotenv()

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
CERTS_DIR = os.path.join(PROJECT_ROOT, "client_certs")
os.makedirs(CERTS_DIR, exist_ok=True)

logger = logging.getLogger(__name__)

STATUS_KEYS = ["register", "inventory", "field_unit", "heartbeat"]


class Config:
    DEVICE_ID = os.getenv("DEVICE_ID")
    DEVICE_TYPE = os.getenv("DEVICE_TYPE", "").upper()
    BASE_URL = os.getenv("PROVISION_SERVER_BASE_URL")
    COMMAND_CENTER_URL = os.getenv("COMMAND_CENTER_BASE_URL")

    USERNAME = os.getenv("APP_USERNAME")
    PASSWORD = os.getenv("APP_PASSWORD")

    HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL_MINUTES", "15"))
    RETRY_LIMIT = int(os.getenv("RETRY_LIMIT", "3"))
    RETRY_WAIT_TIMES = [
        int(x) for x in os.getenv("RETRY_WAIT_SECONDS", "10,100,300").split(",") if x.strip().isdigit()
    ]

    CPU = os.getenv("CPU_MODEL")
    RAM = os.getenv("RAM_SIZE")
    STORAGE = os.getenv("STORAGE_SIZE")
    OS_VERSION = os.getenv("OS_VERSION")
    FIRMWARE = os.getenv("FIRMWARE_VERSION")
    APPS_INSTALLED = json.loads(os.getenv("APPS_INSTALLED", "[]"))
    MESSAGE = os.getenv("MESSAGE")


class Provisioning:
    def __init__(self):
        self.config = Config()
        self.status_file = os.path.join(BASE_DIR, f"provision_status_{self.config.DEVICE_ID}.json")
        self.load_provision_status()

    # -------------------- Main Provision Flow --------------------
    
    def start_provision(self):
        if all(self.provision_status.get(k) for k in STATUS_KEYS):
            logger.info(f"Device {self.config.DEVICE_ID} is already provisioned. Skipping provisioning flow.")
            return True

        steps = [
            ("register", self.register_api_call),
            ("inventory", self.inventory_api_call),
            ("field_unit", self.fieldUnit_api_call),
            ("heartbeat", self.heartbeat_call),
        ]
        for step, func in steps:
            if not self.provision_status.get(step):
                if not func():
                    logger.error(f"Provisioning aborted: {step} API failed.")
                    return False
            else:
                logger.info(f"{step.capitalize()} already completed. Skipping.")

        logger.info("Provisioning completed successfully.")
        return True


    # -------------------- API Wrappers --------------------

    def register_api_call(self):
        payload = {
            "message": self.config.MESSAGE,
            "device_id": self.config.DEVICE_ID,
            "configured_heartbeat_interval": self.config.HEARTBEAT_INTERVAL,
        }
        url = f"{self.config.BASE_URL}/device/{self.config.DEVICE_ID}/register"
        response = self.perform_api_call("register", url, payload)

        if response and response.status_code == 201:
            self.replace_register_cert(response)
        elif response and response.status_code == 200:
            logger.info("Device already provisioned.")
        return bool(response and response.status_code in (200, 201))

    def inventory_api_call(self):
        payload = {
            "hw_data": {"cpu": self.config.CPU, "ram": self.config.RAM, "storage": self.config.STORAGE},
            "sw_data": {
                "os": self.config.OS_VERSION,
                "firmware_version": self.config.FIRMWARE,
                "apps_installed": self.config.APPS_INSTALLED,
            },
        }
        url = f"{self.config.BASE_URL}/device/{self.config.DEVICE_ID}/inventory"
        return self.perform_api_call("inventory", url, payload, method="PUT")

    def heartbeat_call(self, update_status=True):
        payload = {
            "device_id": self.config.DEVICE_ID,
            "configured_heartbeat_interval": self.config.HEARTBEAT_INTERVAL,
        }
        url = f"{self.config.BASE_URL}/device/{self.config.DEVICE_ID}/heartbeat"
        return self.perform_api_call("heartbeat", url, payload, payload_type="plain")

    def fieldUnit_api_call(self):
        if not self.config.USERNAME or not self.config.PASSWORD:
            logger.error("USERNAME or PASSWORD not set in .env")
            return False

        auth = HTTPBasicAuth(self.config.USERNAME, self.config.PASSWORD)
        headers = {"Content-Type": "application/json", "Device-Id": self.config.DEVICE_ID.encode()}

        payload, endpoint = self.build_payload(self.config.DEVICE_TYPE)
        if not payload or not endpoint:
            logger.error(f"Unsupported DEVICE_TYPE: {self.config.DEVICE_TYPE}")
            return False

        return self.perform_api_call("field_unit", endpoint, payload, headers=headers, auth=auth)

    # -------------------- Generic API Executor --------------------

    def perform_api_call(
        self, step, url, body, method="POST", payload_type="encrypted", headers=None, auth=None, success_codes=(200, 201)
    ):
        response = None
        try:
            response = RestUtil.send_data(
                url=url, body=body, method=method, payload_type=payload_type, headers=headers, auth=auth
            )
            if response.status_code not in success_codes:
                logger.warning(f"{step} failed with {response.status_code}, retrying...")
                response = self.retry_api_call(url=url, body=body, method=method, payload_type=payload_type, headers=headers, auth=auth)
            
            if response and response.status_code in success_codes:
                if(self.config.DEVICE_TYPE== "DRONE") and "drone" in url :
                    payload, endpoint = self.build_payload("CAMERA")
                    self.perform_api_call("field_unit", endpoint, payload, headers=headers, auth=auth)
                self.provision_status[step] = True
                self.save_provision_status()
                logger.info(f"{step.capitalize()} success: {response.status_code}")
                return response

            error_message = self.extract_error_message(response) if response else "No response"
            logger.error(f"{step.capitalize()} failed after retries. Status: {getattr(response, 'status_code', None)}, Error: {error_message}")
        except Exception as e:
            logger.error(f"Exception during {step} API call: {e}")
        return None

    def retry_api_call(self, *, url, body, method, payload_type, headers=None, auth=None):
        response = None
        for attempt, wait in enumerate(self.config.RETRY_WAIT_TIMES, 1):
            logger.info(f"[Retry {attempt}/{self.config.RETRY_LIMIT}] Waiting {wait}s before retry...")
            time.sleep(wait)
            try:
                response = RestUtil.send_data(url=url, body=body, method=method, payload_type=payload_type, headers=headers, auth=auth)
                if response and response.status_code in (200, 201):
                    return response
            except Exception as e:
                logger.error(f"Exception during retry attempt {attempt}: {e}")
        return response

    # -------------------- Support Methods --------------------

    def replace_register_cert(self, response):
        try:
            resp_json = response.json()
            device_id = resp_json.get("device_id")
            new_cert = resp_json.get("device_cert")
            pub_key = resp_json.get("public_key")
            cert_key = resp_json.get("cert_key")

            if device_id and new_cert and pub_key and cert_key:
                with open(os.path.join(CERTS_DIR, f"{device_id}_cert.pem"), "w") as f: f.write(new_cert)
                with open(os.path.join(CERTS_DIR, f"{device_id}_pub.pem"), "w") as f: f.write(pub_key)
                with open(os.path.join(CERTS_DIR, f"{device_id}_cert_key.pem"), "w") as f: f.write(cert_key)
                logger.info(f"Replaced cert and key for device {device_id}")
            else:
                logger.warning("Register API response missing cert/key/device_id. Skipping cert replacement.")
        except Exception as e:
            logger.error(f"Failed to replace cert/key: {e}")

    def extract_error_message(self, response):
        try:
            data = response.json()
            if isinstance(data, dict):
                messages = []
                for field, errors in data.items():
                    if isinstance(errors, list):
                        messages.extend(f"{field}: {e.get('string', e) if isinstance(e, dict) else e}" for e in errors)
                return " | ".join(messages)
            if isinstance(data, str):
                return data
        except json.JSONDecodeError:
            matches = re.findall(r"'(\w+)':\s*\[?ErrorDetail\(string='([^']+)'", response.text)
            if matches:
                return " | ".join(f"{f}: {m}" for f, m in matches)
            return f"Unknown error: {response.text}"
        return f"Failed to parse error message. Status: {response.status_code}"

    def build_payload(self, device_type: str):
        payload = PayloadLoader.load_payload(device_type)
        endpoint_map = {
            "DRONE": f"{self.config.COMMAND_CENTER_URL}/field-units/drones/",
            "CAMERA": f"{self.config.COMMAND_CENTER_URL}/field-units/cameras/",
            "SENSOR": f"{self.config.COMMAND_CENTER_URL}/field-units/sensors/",
        }
        return payload, endpoint_map.get(device_type.upper())

    # -------------------- Status Handling --------------------

    def load_provision_status(self):
        if os.path.exists(self.status_file):
            try:
                with open(self.status_file, "r") as f:
                    self.provision_status = json.load(f)
            except Exception:
                self.provision_status = {}
        else:
            self.provision_status = {}
        for key in STATUS_KEYS:
            self.provision_status.setdefault(key, False)

    def save_provision_status(self):
        try:
            with open(self.status_file, "w") as f:
                json.dump(self.provision_status, f)
            logger.info("Provision status saved.")
        except Exception as e:
            logger.error(f"Failed to save provision status: {e}")

    # -------------------- Scheduler --------------------

    def start_heartbeat_scheduler(self):
        schedule.every(self.config.HEARTBEAT_INTERVAL).minutes.do(lambda: self.heartbeat_call(update_status=False)).tag("heartbeat")

        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(1)

        t = threading.Thread(target=run_scheduler, daemon=True)
        t.start()

    def reschedule_heartbeat(self):
        try:
            schedule.clear("heartbeat")
            schedule.every(self.config.HEARTBEAT_INTERVAL).minutes.do(lambda: self.heartbeat_call(update_status=False)).tag("heartbeat")
            logger.info(f"Rescheduled heartbeat to {self.config.HEARTBEAT_INTERVAL} minutes")
        except Exception as e:
            logger.error(f"Failed to reschedule heartbeat: {e}")
