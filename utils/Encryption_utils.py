import os
import json
import base64
import logging
from dotenv import load_dotenv
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

current_script_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT_DIR = os.path.dirname(current_script_dir)
dotenv_path = os.path.join(PROJECT_ROOT_DIR, "RPi_device_agent", ".env")

load_dotenv(dotenv_path)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR) 
CERTS_DIR = os.path.join(PROJECT_ROOT, "RPi_device_agent","client_certs")
os.makedirs(CERTS_DIR, exist_ok=True)

DEVICE_ID = os.getenv("DEVICE_ID")
PUBLIC_KEY_PATH = os.path.join(CERTS_DIR, f"{DEVICE_ID}_pub.pem")
logger = logging.getLogger(__name__)
class Encryption_utils:
    
    @staticmethod
    def load_public_key(path=None):
        if path is None:
            path = PUBLIC_KEY_PATH
        with open(path, "rb") as f:
            return serialization.load_pem_public_key(f.read(), backend=default_backend())
        
    @staticmethod
    def generate_aes_key():
        
        aes_key = AESGCM.generate_key(bit_length=256)
        aesgcm = AESGCM(aes_key)
        
        return aes_key, aesgcm
    
    @staticmethod
    def encrypt(data: dict) -> dict:
        """
        Encryption:
        - AES-GCM for payload
        - RSA for AES key
        Returns JSON-safe dict with `enc_key` and `enc_payload`
        """
        # Step 1: Serialize input JSON
        json_data = json.dumps(data).encode('utf-8')

        # Step 2: Generate AES key and encrypt data
        public_key = Encryption_utils.load_public_key()
        aes_key, aesgcm = Encryption_utils.generate_aes_key()
        
        nonce = os.urandom(12)  # 96-bit nonce for AES-GCM
        encrypted_data = aesgcm.encrypt(nonce, json_data, None)

        # Step 3: Encrypt AES key using RSA public key
        encrypted_key = public_key.encrypt(
            aes_key,
            padding.OAEP(
                mgf=padding.MGF1(hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        # Step 4: Return dict (both base64-encoded)
        result = {
            "enc_key": base64.b64encode(encrypted_key).decode('utf-8'),
            "enc_payload": base64.b64encode(nonce + encrypted_data).decode('utf-8'),
        }
        return result
    
    @staticmethod
    def process_and_encrypt_data(bytes, aes_key, aesgcm: AESGCM) -> bytes | None:
        
        try:
            public_key = Encryption_utils.load_public_key()
            encrypted_key = public_key.encrypt(
            aes_key,
            padding.OAEP(
                mgf=padding.MGF1(hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
                )
            )
            
            nonce = os.urandom(12)
            ct = aesgcm.encrypt(nonce, bytes, None)
            payload = base64.b64encode(nonce + ct)
            
            return payload, base64.b64encode(encrypted_key)
        except Exception as exc:
            logger.error("Failed to process or encrypt data: %s", exc)
        return None
    
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--pub-key-path", required=True)
    parser.add_argument("--message", required=True)
    args = parser.parse_args()

    pub_key = Encryption_utils.load_public_key(args.pub_key_path)
    message_dict = {"message": args.message}
    encrypted_result = Encryption_utils.encrypt(message_dict, pub_key)
    print(json.dumps(encrypted_result, indent=2)) 
   