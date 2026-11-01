import os
import argparse
import logging
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from cryptography.x509 import Name, NameAttribute,SubjectAlternativeName,DNSName,IPAddress
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from app.config import settings

import ipaddress



# Logging config
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_root_ca(country, org, cn, key_size, public_exponent, valid_days):
    os.makedirs(settings.CERT_DIR, exist_ok=True)

    logger.info("🔐 Generating Root CA private key...")
    private_key = rsa.generate_private_key(
        public_exponent=public_exponent,
        key_size=key_size
    )

    key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()  # No password
    )

    logger.info("📜 Creating X.509 Root CA certificate...")
    subject = issuer = Name([
        NameAttribute(NameOID.COUNTRY_NAME, country),
        NameAttribute(NameOID.ORGANIZATION_NAME, org),
        NameAttribute(NameOID.COMMON_NAME, cn)
    ])

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=valid_days))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(private_key, hashes.SHA256())
    )

    cert_pem = cert.public_bytes(serialization.Encoding.PEM)

    # Save to files
    with open(settings.ROOT_CA_KEY, "wb") as f:
        f.write(key_pem)
        logger.info(f"✅ Root CA private key saved to: {settings.ROOT_CA_KEY}")

    with open(settings.ROOT_CA_CERT, "wb") as f:
        f.write(cert_pem)
        logger.info(f"✅ Root CA certificate saved to: {settings.ROOT_CA_CERT}")
def load_root_ca():
    with open(settings.ROOT_CA_CERT, "rb") as f:
        root_cert = x509.load_pem_x509_certificate(f.read())
    with open(settings.ROOT_CA_KEY, "rb") as f:
        root_key = serialization.load_pem_private_key(
            f.read(), password=None
        )
    return root_cert, root_key    
def generate_servert_cert(hostname,ip) -> str:
    """Generate signed certificate for server mtls."""
    issuer_cert, issuer_key = load_root_ca()
    cert_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    cert_private_key_pem = cert_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ).decode()
    subject = Name([NameAttribute(NameOID.COMMON_NAME, hostname)])
    cert_builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer_cert.subject)
        .public_key(cert_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=365))
        .add_extension(
                SubjectAlternativeName([
                DNSName(hostname),  # hostname
                # IPAddress(ipaddress.IPv4Address(ip)),  # server IP
            ]),critical=False)
    )
    cert = cert_builder.sign(private_key=issuer_key, algorithm=hashes.SHA256())
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
    # Save to files
    with open(f"{settings.CERT_DIR}/{hostname}_cert.pem", "w") as f:
        f.write(cert_pem)
        logger.info(f"✅ Server cert  saved to: {settings.ROOT_CA_KEY}/{hostname}_cert.pem")
    with open(f"{settings.CERT_DIR}/{hostname}_cert_key.pem", "w") as f:
        f.write(cert_private_key_pem)
        logger.info(f"✅ Server cert private key saved to: {settings.ROOT_CA_KEY}/{hostname}_cert_key.pem")
    return cert.public_bytes(serialization.Encoding.PEM).decode(), cert_private_key_pem

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a Root CA certificate or Server mTLS certificate"
    )
    parser.add_argument(
        "--type",
        choices=["root", "server"],
        help="Type of certificate to generate: 'root' for Root CA, 'server' for Server mTLS cert"
    )

    # Root CA arguments
    parser.add_argument("--country", help="Country Name (e.g., IN)")
    parser.add_argument("--org", help="Organization Name (e.g., MyOrg)")
    parser.add_argument("--cn", help="Common Name (e.g., MyRootCA)")
    parser.add_argument("--key-size", type=int, help="Key size in bits (default: 4096)")
    parser.add_argument("--public-exponent", type=int, help="Public exponent (default: 65537)")
    parser.add_argument("--days", type=int, help="Certificate validity in days (default: 3650)")

    # Server cert arguments
    parser.add_argument("--hostname", help="Hostname for server")
    parser.add_argument("--ip", help="Server IP address")

    args = parser.parse_args()

    # Ask for cert type if not provided
    if not args.type:
        while True:
            user_choice = input("Do you want to generate a Root CA cert or a Server mTLS cert? [root/server]: ").strip().lower()
            if user_choice in ["root", "server"]:
                args.type = user_choice
                break
            else:
                logger.info("❌ Invalid choice. Please enter 'root' or 'server'.")

    if args.type == "root":
        # Prompt for Root CA fields if missing
        country = args.country or input("Enter Country Name (default: IN): ") or "IN"
        org = args.org or input("Enter Organization Name (default: MyOrg): ") or "MyOrg"
        cn = args.cn or input("Enter Common Name (default: MyRootCA): ") or "MyRootCA"
        key_size = args.key_size or int(input("Enter Key Size in bits (default: 4096): ") or 4096)
        public_exponent = args.public_exponent or int(input("Enter Public Exponent (default: 65537): ") or 65537)
        valid_days = args.days or int(input("Enter Validity in days (default: 3650): ") or 3650)

        generate_root_ca(
            country=country,
            org=org,
            cn=cn,
            key_size=key_size,
            public_exponent=public_exponent,
            valid_days=valid_days
        )

    elif args.type == "server":
        # Prompt for Server fields if missing
        hostname = args.hostname or input("Enter Hostname for server: ")
        ip = args.ip or input("Enter Server IP address: ")

        if not hostname or not ip:
            logger.info("❌ Hostname and IP are required for Server certificate.")
            exit(1)

        generate_servert_cert(
            ip=ip,
            hostname=hostname
        )
