import json
import base64
import traceback
from datetime import datetime, timedelta, timezone
from flask import jsonify, request
from sqlalchemy.orm import scoped_session
from common.device import Device, Key, Certificate, Inventory, DeviceStatus
from app.services.cert_service import (load_root_ca, revoke_cert_for_device)
from app.utils.crypto_utils import ( load_pem_private_key, decrypt_payload, verify_signature,load_device_public_key,generate_cert, 
                                     decrypt_payload_with_private_key)
from app.config import settings
import os
import json
from sqlalchemy.orm import scoped_session
from cryptography import x509
from cryptography.x509 import NameOID, Name, NameAttribute, SubjectAlternativeName, DNSName
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_random_aes_key(length=32):
    return base64.b64encode(os.urandom(length)).decode()


def register_device_with_encryption(session: scoped_session, device_id):
    data = request.json
    enc_key = data.get("enc_key")
    enc_payload = data.get("enc_payload")

    if not all([device_id, enc_payload]):
        return jsonify({"error": "Missing fields"}), 400

    logger.info(f"Registering device {device_id} with encrypted payload")

    # Step 1: Get Device
    device = session.query(Device).filter_by(id=device_id).first()
    if not device:
        return jsonify({"error": "Device not found"}), 404
    if device.status == DeviceStatus.ACTIVE.value or device.status == DeviceStatus.INACTIVE.value:
        logger.info(f"Device already Registered : {device_id}")
        return jsonify({"data": "Device already registered"}), 200
    # Step 2: Get Keypair for Decryption
    keypair = (session.query(Key) .filter_by(device_id=device.id) .order_by(Key.created_at.asc()).first())
    if not keypair:
        return jsonify({"error": "Keypair not found"}), 404

    # Step 3: Decrypt incoming data
    try:
        decrypted_msg = decrypt_payload_with_private_key(keypair.private_key, enc_key, enc_payload)
        decrypted_json = json.loads(decrypted_msg) 
        logger.info(f"Decryption successful for device {device_id}")
        encoded_reply = base64.b64encode(f"Welcome {device_id}".encode()).decode()
    except Exception as e:
        logger.exception("Decryption failed")
        return jsonify({"error": "Decryption failed", "details": str(e)}), 400

    logger.info(f"Decrypted message: {decrypted_msg}")
    
    configured_heartbeat_interval = decrypted_json.get("configured_heartbeat_interval")
    if configured_heartbeat_interval:
        device.configured_heartbeat_interval = configured_heartbeat_interval
        logger.info(f"Set configured_heartbeat_interval for device {device_id} to {configured_heartbeat_interval} minutes.")


    # Step 4: Generate new certificate and cert private key
    root_cert, root_key = load_root_ca()
    cert_pem, cert_key_pem = generate_cert(device_id, root_cert, root_key)
    logger.info(f"Generated new certificate for device {device_id}")

    # Step 5: Generate random AES key
    aes_key = generate_random_aes_key()
    logger.info(f"Generated AES key for device {device_id}")
    enc_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_key_pem = enc_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ).decode()
    public_key_pem = enc_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    # Step 6: Create new Certificate record
    new_cert = Certificate(
        device_id=device.id,
        cert_data=cert_pem,
        key_data=cert_key_pem,
        aes_key=aes_key,
        updated_at = datetime.utcnow()
    )
    key_obj = Key(
        device_id=device.id,
        public_key=public_key_pem,
        private_key=private_key_pem,
        aes_key=aes_key,
        updated_at = datetime.utcnow()
    )
    session.add(key_obj)
    session.add(new_cert)
    logger.info(f"New certificSate record created for device {device_id}")

    device.status = DeviceStatus.REGISTERED.value
    logger.info(f"Keypair updated for device {device_id}")

    # Step 8: Commit changes
    session.commit()
    logger.info(f"Device {device_id} registered. Cert saved. Keypair rotated.")

    # Step 9: Respond
    return jsonify({
        "device_id": device_id,
        "status": DeviceStatus.REGISTERED.value,
        "device_cert": cert_pem,
        "public_key": public_key_pem,
        "cert_key": cert_key_pem,
        "reply": encoded_reply
    }), 201



def secure_endpoint(session: scoped_session, device_id):
    data = request.json or {}
    encrypted_payload = data.get('encrypted_payload')

    if not device_id or not encrypted_payload:
        return jsonify({'error': 'Missing device_id or encrypted_payload'}), 400

    # ✅ Fetch the device object by id
    logger.info(f"Fetching device {device_id} for secure endpoint")
    device = session.query(Device).filter_by(id=device_id).first()
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    logger.info(f"Found device {device_id} with ID {device.id}")
    # ✅ Fetch keypair associated with device
    keypair = session.query(Key).filter_by(device_id=device.id).first()
    if not keypair:
        return jsonify({'error': 'Keypair not found'}), 404

    try:
        logger.info(f"Loading private key for device {device_id}")
        ciphertext = base64.b64decode(encrypted_payload, validate=True)
    except Exception:
        return jsonify({'error': 'Bad base64'}), 400

    try:
        logger.info(f"Decrypting payload for device {device_id}")
        # Load the private key from PEM format
        private_key = load_pem_private_key(keypair.private_key)
        logger.info(f"Private key loaded successfully for device {device_id}")
        plaintext = decrypt_payload(private_key, ciphertext)
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'Decryption failed', 'details': str(e)}), 400

    return jsonify({'message': plaintext}), 200



def verify_signature_endpoint(session: scoped_session, device_id):
    data = request.json
    payload = data.get('payload')
    signature = data.get('signature')
    logger.info(f"Verifying signature for device {device_id}")
    if not payload or not signature:
        return jsonify({'error': 'Missing fields'}), 400
    logger.info(f"Payload: {payload}, Signature: {signature}")
    # ✅ Fetch device by id (device_id is the device name)
    device = session.query(Device).filter_by(id=device_id).first()
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    logger.info(f"Found device {device_id} with ID {device.id}")    
    # ✅ Get keypair for the device
    keypair = session.query(Key).filter_by(device_id=device.id).first()
    if not keypair:
        return jsonify({'error': 'Keypair not found'}), 404
    logger.info(f"Found keypair for device {device_id}")
    # ✅ Verify signature using stored public key
    is_valid = verify_signature(keypair.public_key, payload, signature)
    return jsonify({'verified': is_valid})


def inventory_handler(session: scoped_session, device_id):
    logger.info(f"Handling inventory for device {device_id}")

    # Step 1: Get Device
    device = session.query(Device).filter_by(id=device_id).first()
    if not device:
        return jsonify({'error': 'Device not found'}), 404

    device_id = device.id
    # Step 2: Handle GET request
    if request.method == 'GET':
        inventory_record = session.query(Inventory).filter_by(device_id=device_id).first()
        if inventory_record:
            return jsonify({
                'hw_data': inventory_record.hw_data or {},
                'sw_data': inventory_record.sw_data or {}
            })
        return jsonify({'hw_data': {}, 'sw_data': {}})

    # Step 3: Handle POST/PUT request with encrypted payload
    try:
        
        inventory = session.query(Inventory).filter_by(device_id=device_id).first()
        if inventory:
            return jsonify({"message": "Inventory already exists for this device"}), 200
        
        logger.info(f"Receiving encrypted payload for device {device_id}")
        data = request.json
        enc_key = data.get("enc_key")
        enc_payload = data.get("enc_payload")
        
        if not enc_payload:
            return jsonify({'error': 'Missing encrypted data in "data" field'}), 400

        # Step 4: Fetch device private key as PEM
        keypair = session.query(Key).filter_by(device_id=device.id).order_by(Key.created_at.desc()).first()
        if not keypair:
            return jsonify({'error': 'Keypair not found'}), 404

        decrypted_str = decrypt_payload_with_private_key(keypair.private_key, enc_key, enc_payload)
        decrypted_json = json.loads(decrypted_str)
        logger.info(f"Decrypted payload: {decrypted_json}")

        # Step 5: Extract and store inventory
        hw_data = decrypted_json.get('hw_data', {})
        sw_data = decrypted_json.get('sw_data', {})

        inventory_record = session.query(Inventory).filter_by(device_id=device_id).first()
        if inventory_record:
            inventory_record.hw_data = hw_data
            inventory_record.sw_data = sw_data
            inventory_record.updated_at = datetime.utcnow()
        else:
            new_inventory = Inventory(
                device_id=device_id,
                hw_data=hw_data,
                sw_data=sw_data,
                updated_at=datetime.utcnow()
            )
            session.add(new_inventory)
        device.status = DeviceStatus.ACTIVE.value
        
        session.query(Key).filter(Key.device_id == device_id, Key.id != keypair.id).delete(synchronize_session=False)
        latest_certificate = session.query(Certificate).filter_by(device_id=device_id).order_by(Certificate.created_at.desc()).first()
        if latest_certificate:
            session.query(Certificate).filter(Certificate.device_id == device_id, Certificate.id != latest_certificate.id).delete(synchronize_session=False)
        session.commit()

        return jsonify({
            'status': DeviceStatus.SUCCESS.value
        })

    except Exception as e:
        logger.exception("Failed to decrypt and store inventory")
        return jsonify({'error': 'Decryption failed', 'details': str(e)}), 500



def renew_certificate(session: scoped_session, device_id):
    logger.info(f"Renewing certificate for device {device_id}")
    # ✅ Get device by id (device_id is the name, not UUID)
    device = session.query(Device).filter_by(id=device_id).first()
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    logger.info(f"Found device {device_id} with ID {device.id}")    
    # ✅ Get keypair using device.id (foreign key relationship)
    keypair = session.query(Key).filter_by(device_id=device.id).first()
    if not keypair:
        return jsonify({'error': 'Keypair not found'}), 404
    logger.info(f"Found keypair for device {device_id}")
    # ✅ Update expiry field
    keypair.expiry = datetime.utcnow() + timedelta(days=365)
    session.commit()

    return jsonify({'renewed': True, 'new_expiry': keypair.expiry.isoformat()})


def heartbeat(session: scoped_session, device_id):
    logger.info(f"Heartbeat received from device {device_id}")
    # 🔍 Lookup device using its id (device_id is stored in the `name` field)
    device = session.query(Device).filter_by(id=device_id).first()
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    logger.info(f"Found device {device_id} with ID {device.id}")  
    
    
    # Extract incoming payload
    try:
        data = request.json or {}
        incoming_interval = data.get("configured_heartbeat_interval")
        if incoming_interval is not None:
            # Convert to int (just in case)
            try:
                incoming_interval = int(incoming_interval)
            except ValueError:
                logger.error(f"Ignoring invalid heartbeat interval from device {device_id}: {incoming_interval}")
                incoming_interval = None

            # Update configured interval if different
            if incoming_interval is not None and device.configured_heartbeat_interval != incoming_interval:
                logger.info(f"Updating configured_interval for {device_id} from {device.configured_heartbeat_interval} to {incoming_interval}")
                device.configured_heartbeat_interval = incoming_interval
    except Exception as e:
        logger.error(f"Failed to process heartbeat payload for {device_id}: {e}")

    
    # Update heartbeat_time in the devices table
    device.heartbeat_time = datetime.now(timezone.utc)
    device.status = DeviceStatus.ACTIVE.value
    logger.info(f"Updated heartbeat_time for device {device_id} to {device.heartbeat_time}")

      
    # 🔄 Update status in inventory (create if doesn't exist)
    inventory = session.query(Inventory).filter_by(device_id=device.id).first()
    if inventory:
        hw_data = inventory.hw_data or {}
        hw_data["status"] = device.status
        inventory.hw_data = hw_data
    else:
        inventory = Inventory(
            device_id=device.id,
            hw_data={"status": device.status},
            sw_data={}
        )
        session.add(inventory)
    logger.info(f"Updated inventory for device {device_id}") 
    # 🧹 Delete old cert/key files
    cert_prefix = os.path.join(settings.CERT_DIR, device_id)
    files_to_delete = [
        f"{cert_prefix}.key",
        f"{cert_prefix}_pub.pem",
        f"{cert_prefix}_cert.pem"
    ]
    for path in files_to_delete:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            # Optional: log warning
            logger.error(f"⚠️ Failed to delete {path}: {e}")
    logger.info(f"Deleted old cert/key files for device {device_id}")
    # Commit DB changes
    session.commit()

    return jsonify({'status': device.status}), 200



def delete_device(session: scoped_session, device_id):
    logger.info(f"Deleting device {device_id}")
    device = session.query(Device).filter_by(id=device_id).first()
    if not device:
        return jsonify({'error': 'Device not found'}), 404

    cert_record = (session.query(Certificate)
                   .filter_by(device_id=device.id)
                   .order_by(Certificate.updated_at.desc())
                   .first())

    if cert_record:
        revoke_cert_for_device(
            cert_pem=cert_record.cert_data,
            crl_path=settings.CRL_PATH,
            ca_cert=load_root_ca()[0],
            ca_key=load_root_ca()[1]
        )
    else:
        logger.info("No certificate found to revoke")

    cert_prefix = os.path.join(settings.CERT_DIR, device_id)
    for suffix in [".key", "_pub.pem", "_cert.pem", "_cert_key.pem"]:
        path = cert_prefix + suffix
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            logger.error(f"Failed to delete {path}: {e}")
    logger.info(f"Deleted cert/key files for device {device_id}")

    device.status = DeviceStatus.INACTIVE.value
    session.commit()
    logger.info(f"Device {device_id} marked INACTIVE")

    return jsonify({'deleted': True}), 200


def update_heartbeat_interval(session: scoped_session, device_id):
    logger.info(f"Received request to update heartbeat interval for device {device_id}")
    data = request.get_json()

    if not data or "configured_heartbeat_interval" not in data:
        return jsonify({"error": "Missing 'configured_heartbeat_interval' in request body"}), 400

    try:
        interval = int(data["configured_heartbeat_interval"])
        if interval <= 0:
            raise ValueError("Interval must be positive")
    except ValueError as e:
        return jsonify({"error": f"Invalid interval: {str(e)}"}), 400

    device = session.query(Device).filter_by(id=device_id).first()
    if not device:
        return jsonify({"error": "Device not found"}), 404

    old_interval = device.configured_heartbeat_interval
    device.configured_heartbeat_interval = interval
    session.commit()
    logger.info(f"Updated heartbeat interval for {device_id} from {old_interval} to {interval} minutes.")

    return jsonify({
        "device_id": device_id,
        "old_interval": old_interval,
        "new_interval": interval,
        "status": "updated"
    }), 200
    
