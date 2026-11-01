import os
import json
import logging
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from app.config import settings
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import subprocess
import platform
import shutil
from cryptography.x509 import CertificateRevocationListBuilder, RevokedCertificateBuilder

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# DB connection
engine = create_engine(settings.DATABASE_URL)
Session = sessionmaker(bind=engine)

def load_root_ca():
    with open(settings.ROOT_CA_CERT, "rb") as f:
        root_cert = x509.load_pem_x509_certificate(f.read())
    with open(settings.ROOT_CA_KEY, "rb") as f:
        root_key = serialization.load_pem_private_key(
            f.read(), password=None
        )
    return root_cert, root_key


def generate_rsa_key(public_exponent=65537, key_size=2048):
    return rsa.generate_private_key(public_exponent=public_exponent, key_size=key_size)


def pem_encode_private(key):
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ).decode()


def revoke_cert_for_device(cert_pem: str, crl_path: str, ca_cert: x509.Certificate, ca_key):
    """
    Revoke a certificate (given in PEM) by adding its serial to the CRL at crl_path.
    Keeps existing CRL entries, signs a new CRL using ca_cert/ca_key.
    """
    # Load existing CRL if available
    crl = None
    if os.path.exists(crl_path):
        with open(crl_path, "rb") as f:
            crl = x509.load_pem_x509_crl(f.read())
        logger.info("Loaded existing CRL")

    now = datetime.utcnow()
    builder = CertificateRevocationListBuilder()

    issuer = ca_cert.subject
    if crl:
        builder = builder.issuer_name(crl.issuer) \
                         .last_update(crl.last_update) \
                         .next_update(now + timedelta(days=1))
        # Re-add existing revoked entries
        for revoked in crl:
            builder = builder.add_revoked_certificate(revoked)
        logger.info(f"Re-added {len(list(crl))} existing revoked entries")
    else:
        builder = builder.issuer_name(issuer) \
                         .last_update(now) \
                         .next_update(now + timedelta(days=1))
        logger.info("Initialized new CRL")

    cert = x509.load_pem_x509_certificate(cert_pem.encode())
    serial = cert.serial_number
    # Only add if not already revoked
    if not crl or crl.get_revoked_certificate_by_serial_number(serial) is None:
        revoked = RevokedCertificateBuilder() \
            .serial_number(serial) \
            .revocation_date(now) \
            .build()
        builder = builder.add_revoked_certificate(revoked)
        logger.info(f"Revoked certificate serial={serial}")
    else:
        logger.info(f"Certificate serial={serial} already revoked")

    new_crl = builder.sign(private_key=ca_key, algorithm=hashes.SHA256())
    with open(crl_path, "wb") as f:
        f.write(new_crl.public_bytes(serialization.Encoding.PEM))
    logger.info(f"Updated CRL written to {crl_path}")
    reload_nginx()
    logger.info("Nginx reloaded after CRL update")
    # This follows the standard pattern of reading and rebuilding CRL then adding new serial before signing :contentReference[oaicite:2]{index=2}

def reload_nginx():
    try:
        system = platform.system()

        # Try to find nginx binary in PATH
        nginx_path = shutil.which(settings.Nginx)
        if not nginx_path:
            logger.error("❌ Nginx not found in system PATH.")
            return

        logger.info(f"📍 Using Nginx at: {nginx_path}")

        cmd = [nginx_path, "-s", "reload"]

        # Use sudo on Linux/macOS
        if system in ["Linux", "Darwin"]:
            cmd.insert(0, "sudo")

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            logger.info("✅ Nginx reloaded successfully.")
        else:
            logger.error(f"❌ Nginx reload failed:\n{result.stderr}")

    except Exception as e:
        logger.exception("⚠️ Exception while reloading Nginx")


