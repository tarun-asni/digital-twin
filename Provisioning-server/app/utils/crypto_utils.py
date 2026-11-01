import os
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.x509 import Name, NameAttribute, SubjectAlternativeName, DNSName
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.backends import default_backend
import base64
from common.device import Key
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# =============================
# 🔐 RSA Key Generation & Serialization
# =============================

def generate_key_pair(public_exponent: int = 65537, key_size: int = 2048):
    """Generate RSA key pair."""
    private_key = rsa.generate_private_key(public_exponent=public_exponent, key_size=key_size)
    return private_key, private_key.public_key()

def serialize_keys(private_key, public_key):
    """Serialize private and public keys to PEM format."""
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ).decode()

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()

    return private_pem, public_pem

def pem_encode_public(pub_key):
    """
    Convert a public key object to a PEM-encoded string.
    """
    return pub_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode("utf-8")

def pem_encode_private(private_key):
    """Convert private key object to PEM-encoded string without encryption."""
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ).decode("utf-8")

# =============================
# 🔓 Decryption / CN Extraction / Signature Validation
# =============================

def load_pem_private_key(pem_str: str, password: str = None):
    """Load a private key from PEM string."""
    if isinstance(pem_str, str):
        pem_bytes = pem_str.encode()
    else:
        pem_bytes = pem_str 

    return serialization.load_pem_private_key(
        pem_bytes,
        password=password.encode() if password and isinstance(password, str) else None
    )

def decrypt_payload(private_key, ciphertext: bytes) -> str:
    """Decrypt encrypted payload with private key."""
    try:
        print("[DEBUG] Attempting decryption...")
        decrypted_bytes = private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        decrypted_text = decrypted_bytes.decode()
        print("[DEBUG] Decryption successful:", decrypted_text)
        return decrypted_text
    except Exception as e:
        print("[ERROR] Decryption failed:", str(e))
        raise


def get_cert_cn(cert_pem: str) -> str:
    """Extract Common Name (CN) from certificate."""
    cert = x509.load_pem_x509_certificate(cert_pem.encode(), default_backend())
    return cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value

def verify_signature(public_key_pem: str, message: str, signature_b64: str) -> bool:
    """
    Verify base64-encoded RSA signature against a message using PEM public key.
    """
    try:
        public_key = load_pem_public_key(public_key_pem.encode())
        signature = base64.b64decode(signature_b64)
        public_key.verify(
            signature,
            message.encode(),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return True
    except InvalidSignature:
        return False
    except Exception as e:
        raise RuntimeError(f"Signature verification error: {e}")

# =============================
# 📜 Certificate Utilities
# =============================

def build_subject_name(country: str, organization: str, common_name: str) -> Name:
    """Create X.509 subject name."""
    return Name([
        NameAttribute(NameOID.COUNTRY_NAME, country),
        NameAttribute(NameOID.ORGANIZATION_NAME, organization),
        NameAttribute(NameOID.COMMON_NAME, common_name),
    ])

def build_certificate(subject, issuer, public_key, issuer_private_key, valid_days: int = 365) -> str:
    """Build and sign X.509 certificate, returning PEM."""
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(public_key)
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=valid_days))
        .add_extension(SubjectAlternativeName([DNSName("localhost")]), critical=False)
        .sign(private_key=issuer_private_key, algorithm=hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode()

def generate_cert(device_id: str, issuer_cert, issuer_key) -> str:
    """Generate signed certificate from device public key and issuer info."""
    cert_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    cert_private_key_pem = cert_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ).decode()
    subject = Name([NameAttribute(NameOID.COMMON_NAME, device_id)])
    cert_builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer_cert.subject)
        .public_key(cert_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=365))
    )
    cert = cert_builder.sign(private_key=issuer_key, algorithm=hashes.SHA256())
    return cert.public_bytes(serialization.Encoding.PEM).decode(), cert_private_key_pem
    
    
def load_private_key_for_device(device_id: str):
    """
    Load the PEM-encoded private key for a given device.
    Looks for a file named certs/{device_id}_priv.pem
    """
    key_path = os.path.join("certs", f"{device_id}_priv.pem")
    if not os.path.exists(key_path):
        raise FileNotFoundError(f"Private key not found for device '{device_id}' at {key_path}")
    
    with open(key_path, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None  # Add password support here if needed
        )
    
    return private_key

def load_device_public_key(session, device_id: str):
    key = session.query(Key).filter_by(device_id=device_id).first()
    if not key or not key.public_key:
        raise Exception(f"Public key not found for device ID: {device_id}")
    
    return load_pem_public_key(key.public_key.encode())

def decrypt_payload_with_private_key(private_key_pem: str, enc_key_b64: str, enc_payload_b64: str) -> str:
    """
    Decrypt encrypted payload using RSA + AES-GCM.

    Args:
        private_key_pem (str): PEM-formatted RSA private key (string).
        enc_key_b64 (str): Base64-encoded RSA-encrypted AES key.
        enc_payload_b64 (str): Base64-encoded payload (nonce + AES-GCM ciphertext).

    Returns:
        str: Decrypted plaintext.
    """
    private_key = load_pem_private_key(private_key_pem, password=None)

    # Decrypt AES key with RSA private key
    encrypted_key = base64.b64decode(enc_key_b64)
    aes_key = private_key.decrypt(
        encrypted_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    # Decode payload and separate nonce and ciphertext
    enc_payload = base64.b64decode(enc_payload_b64)
    nonce = enc_payload[:12]
    ciphertext = enc_payload[12:]

    # Decrypt with AESGCM
    aesgcm = AESGCM(aes_key)
    decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, None)

    return decrypted_bytes.decode('utf-8')
