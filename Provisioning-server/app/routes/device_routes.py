from flask import Blueprint
from sqlalchemy.orm import scoped_session, sessionmaker
from app.controllers import device_controller
from app.config import settings
from sqlalchemy import create_engine
from common.device import Base

engine = create_engine(settings.DATABASE_URL)
Base.metadata.create_all(engine)
Session = scoped_session(sessionmaker(bind=engine))

# Create Blueprint
device_bp = Blueprint('provision/device', __name__)

# Session factory
Session = scoped_session(sessionmaker(bind=engine))

# Register route
@device_bp.route('/provision/device/<device_id>/register', methods=['POST'])
def register(device_id):
    session = Session()
    try:
        return device_controller.register_device_with_encryption(session, device_id)
    finally:
        session.close()

# Secure encrypted payload route
@device_bp.route('/provision/device/<device_id>/api/secure', methods=['POST'])
def secure(device_id):
    session = Session()
    try:
        return device_controller.secure_endpoint(session, device_id)
    finally:
        session.close()

# Signature verification route
@device_bp.route('/provision/device/<device_id>/verify-signature', methods=['POST'])
def verify_signature(device_id):
    session = Session()
    try:
        return device_controller.verify_signature_endpoint(session, device_id)
    finally:
        session.close()

# Inventory handler (GET or PUT)
@device_bp.route('/provision/device/<device_id>/inventory', methods=['GET', 'PUT'])
def inventory(device_id):
    session = Session()
    try:
        return device_controller.inventory_handler(session, device_id)
    finally:
        session.close()

# Certificate renewal route
@device_bp.route('/provision/device/<device_id>/certificate/renew', methods=['POST'])
def renew(device_id):
    session = Session()
    try:
        return device_controller.renew_certificate(session, device_id)
    finally:
        session.close()

# Heartbeat route
@device_bp.route('/provision/device/<device_id>/heartbeat', methods=['POST'])
def heartbeat(device_id):
    session = Session()
    try:
        return device_controller.heartbeat(session, device_id)
    finally:
        session.close()

# Device deletion route
@device_bp.route('/provision/device/<device_id>', methods=['DELETE'])
def delete(device_id):
    session = Session()
    try:
        return device_controller.delete_device(session, device_id)
    finally:
        session.close()


# Heartbeat interval update API
@device_bp.route('/provision/device/<device_id>/update-heartbeat-interval', methods=['POST'])
def update_heartbeat_interval(device_id):
    session = Session()
    try:
        return device_controller.update_heartbeat_interval(session, device_id)
    finally:
        session.close()


