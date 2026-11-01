import os, json
from pathlib import Path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR) 
field_unit_payloads = os.path.join(PROJECT_ROOT, "field_unit_payloads")
class PayloadLoader:

    @staticmethod
    def load_payload(device_type: str):
        """Load payload JSON file and inject DEVICE_ID from .env""" 
        device_type = device_type.lower()     
        
        path = os.path.join(field_unit_payloads, f"{device_type}.json")

        #if not path.exists():
           # raise ValueError(f"Payload template not found for {device_type}")

        with open(path, "r") as f:
            payload = json.load(f)

        # Always override id from .env
        payload["id"] = os.getenv("DEVICE_ID")
        return payload
    
