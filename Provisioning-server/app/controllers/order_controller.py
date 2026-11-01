import base64
import os
from uuid import uuid4
from flask import jsonify
from datetime import datetime, timedelta, timezone
import ipaddress
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.x509 import (
    CertificateBuilder, Name, NameAttribute, SubjectAlternativeName, DNSName, random_serial_number, IPAddress
)
from cryptography.x509.oid import NameOID
from flask import jsonify, request
from common.device import Device, Key, Certificate, DeviceStatus   
from app.services.cert_service import load_root_ca  # Reuse existing!
from app.config import settings
import io
import zipfile
from flask import send_file
import json
import shutil
def generate_random_aes_key(length=32):
    return base64.b64encode(os.urandom(length)).decode()


def add_directory_to_zip(zip_file, source_dir, arcname=None):
    """
    Add a directory and all its contents to a zip file
    """
    if arcname is None:
        arcname = os.path.basename(source_dir)

    for root, dirs, files in os.walk(source_dir):
        for file in files:
            file_path = os.path.join(root, file)
            arc_path = os.path.join(arcname, os.path.relpath(file_path, source_dir))
            zip_file.write(file_path, arc_path)


def create_device_order(session):
    """
    POST /device_order
    Generate UUID device, keys, signed cert,
    save to DB & certs folder.
    """
    # 1. Generate UUID
    device_id = str(uuid4())
    data = request.json
    if not data or not data.get("name") or not data.get("type"):
        return jsonify({"error": "Device name or tupe is missing"}), 404

    device_name = data.get("name").strip()

    # Check if device name already exists
    existing_device = session.query(Device).filter(Device.name == device_name).first()
    if existing_device:
        return (
            jsonify({
                "error": f"Device with name '{device_name}' already exists",
                "device_id": str(existing_device.id),
                "status": existing_device.status
            }),
            409,
        )

    # 2. Load Root CA
    root_cert, root_key = load_root_ca()

    # 3. Generate encryption key pair
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

    aes_key = generate_random_aes_key()

    # 4. Build certificate
    cert_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    cert_private_key_pem = cert_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ).decode()
    subject = Name([NameAttribute(NameOID.COMMON_NAME, device_id)])

    cert = (
        CertificateBuilder()
            .subject_name(subject)
            .issuer_name(root_cert.subject)
            .public_key(cert_key.public_key())
            .serial_number(random_serial_number())
            .not_valid_before(datetime.now(timezone.utc))
            .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
            .sign(root_key, hashes.SHA256())
        )   
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()

    # 5. Save to DB
    device = Device(id=device_id,name=data.get("name"), type=data.get("type"), status=DeviceStatus.CREATED.value,created_at=datetime.now(timezone.utc),
    updated_at=datetime.now(timezone.utc))
    session.add(device)
    session.flush()

    key_obj = Key(
        device_id=device.id,
        public_key=public_key_pem,
        private_key=private_key_pem,
        aes_key=aes_key
    )

    cert_obj = Certificate(
        device_id=device.id,
        cert_data=cert_pem,
        key_data=cert_private_key_pem,  # ✅ FIXED
        aes_key=aes_key
    )

    session.add_all([key_obj, cert_obj])
    session.commit()

    # 6. Save certs to disk in setup folder with naming pattern <type>_<number>_device
    device_type = data.get("type")
    device_number = device_id.split('-')[0]  # Use first part of UUID as number
    cert_folder_name = f"{device_type}_{device_number}_device"

    # Create certificate folder in setup directory
    setup_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "setup")
    cert_folder_path = os.path.join(setup_dir, cert_folder_name)
    os.makedirs(cert_folder_path, exist_ok=True)

    # Also save to original certs directory for backward compatibility
    os.makedirs(settings.CERT_DIR, exist_ok=True)
    with open(f"{settings.CERT_DIR}/{device_id}.key", "w") as f:
        f.write(private_key_pem)
    with open(f"{settings.CERT_DIR}/{device_id}_pub.pem", "w") as f:
        f.write(public_key_pem)
    with open(f"{settings.CERT_DIR}/{device_id}_cert.pem", "w") as f:
        f.write(cert_pem)
    with open(f"{settings.CERT_DIR}/{device_id}_cert_key.pem", "w") as f:
        f.write(cert_private_key_pem)

    # Save certificates to the new certificate folder
    with open(f"{cert_folder_path}/{device_id}.key", "w") as f:
        f.write(private_key_pem)
    with open(f"{cert_folder_path}/{device_id}_pub.pem", "w") as f:
        f.write(public_key_pem)
    with open(f"{cert_folder_path}/{device_id}_cert.pem", "w") as f:
        f.write(cert_pem)
    with open(f"{cert_folder_path}/{device_id}_cert_key.pem", "w") as f:
        f.write(cert_private_key_pem)

    root_ca = root_cert.public_bytes(serialization.Encoding.PEM).decode()

    # 7. Create ZIP in memory with device code and certificates
    metadata = {
        "device_id": device_id,
        "name": data.get("name"),
        "type": data.get("type"),
        "public_key": public_key_pem,
        "device_cert": cert_pem,
        "device_cert_key": cert_private_key_pem,
        "root_ca": root_ca
    }

    mem_zip = io.BytesIO()
    with zipfile.ZipFile(mem_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add certificates to the certificate folder
        zf.writestr(f"{cert_folder_name}/{device_id}_pub.pem", public_key_pem)
        zf.writestr(f"{cert_folder_name}/{device_id}_cert.pem", cert_pem)
        zf.writestr(f"{cert_folder_name}/{device_id}_cert_key.pem", cert_private_key_pem)
        zf.writestr(f"{cert_folder_name}/rootCA.pem", root_ca)
        zf.writestr(f"{cert_folder_name}/metadata.json", json.dumps(metadata, indent=2))

        # Add RPi_device_agent folder from setup directory
        rpi_agent_path = os.path.join(setup_dir, "RPi_device_agent")
        if os.path.exists(rpi_agent_path):
            add_directory_to_zip(zf, rpi_agent_path, "RPi_device_agent")

        # Add utils folder from setup directory
        utils_path = os.path.join(setup_dir, "utils")
        if os.path.exists(utils_path):
            add_directory_to_zip(zf, utils_path, "utils")

        # Add setup.sh file from setup directory
        setup_script_path = os.path.join(setup_dir, "setup.sh")
        if os.path.exists(setup_script_path):
            with open(setup_script_path, 'r', encoding='utf-8') as f:
                setup_content = f.read()
            zf.writestr("setup.sh", setup_content)

    mem_zip.seek(0)
    return send_file(
        mem_zip,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"{device_id}_device_package.zip"
    )