import os
import json
import base64
import urllib.parse

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import scoped_session, sessionmaker
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env") 

# Database connection setup
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
encoded = urllib.parse.quote_plus(DB_PASSWORD)
DATABASE_URL = f"postgresql://{DB_USER}:{encoded}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)
db_session = scoped_session(sessionmaker(bind=engine))

# Fetch private key from DB
def _get_private_key_from_db(device_id, db):
    try:
        metadata = MetaData()
        key_table = Table('keys', metadata, autoload_with=db.bind)
        query = key_table.select().where(key_table.c.device_id == device_id)
        result = db.execute(query).first()
        if result and result.private_key:
            private_key = serialization.load_pem_private_key(
                result.private_key.encode(),
                password=None,
                backend=default_backend()
            )
            return private_key
    except Exception as e:
        print(f"Error loading private key from DB: {e}")
    return None


def decrypt_payload(enc_key_b64, enc_payload_b64, device_id):
    db = db_session()
    private_key = _get_private_key_from_db(device_id, db)
    if not private_key:
        raise ValueError(f"Private key not found for device_id: {device_id}")

    enc_key = base64.b64decode(enc_key_b64)
    enc_payload = base64.b64decode(enc_payload_b64)

    # Step 1: Decrypt AES key
    aes_key = private_key.decrypt(
        enc_key,
        padding.OAEP(
            mgf=padding.MGF1(hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    # Step 2: Decrypt AES payload
    nonce = enc_payload[:12]
    ciphertext = enc_payload[12:]
    aesgcm = AESGCM(aes_key)
    decrypted = aesgcm.decrypt(nonce, ciphertext, None)
    return json.loads(decrypted.decode('utf-8'))
