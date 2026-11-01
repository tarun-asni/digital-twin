import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, DateTime, 
    Text, ForeignKey, Integer
)
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from enum import Enum  # Assuming this is defined in a separate file
from sqlalchemy import Enum as SqlEnum

Base = declarative_base()

# Device Status Enum
class DeviceStatus(str, Enum):
    CREATED = "CREATED"
    REGISTERED = "REGISTERED"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUCCESS = "SUCCESS"
    STREAMING = "STREAMING"
    FAIL_TO_STREAM = "FAIL_TO_STREAM"

class Device(Base):
    __tablename__ = 'devices'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)
    status = Column(
    SqlEnum(DeviceStatus, values_callable=lambda enum: [e.value for e in enum]),
    default=DeviceStatus.CREATED.value  # will now be "created"
)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    heartbeat_time = Column(DateTime(timezone=True), nullable=True) # To store the last heartbeat timestamp
    configured_heartbeat_interval = Column(Integer, nullable=True) # To store the configured interval in minutes


    certificates = relationship("Certificate", back_populates="device", cascade="all, delete-orphan")
    keys = relationship("Key", back_populates="device", cascade="all, delete-orphan")
    inventories = relationship("Inventory", back_populates="device", cascade="all, delete-orphan")


class Certificate(Base):
    __tablename__ = 'certificates'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False)
    cert_data = Column(Text, nullable=False)
    key_data = Column(Text, nullable=False)
    aes_key = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    device = relationship("Device", back_populates="certificates")


class Key(Base):
    __tablename__ = 'keys'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False)
    public_key = Column(Text, nullable=False)
    private_key = Column(Text, nullable=False)
    aes_key = Column(String, nullable=True)
    device = relationship("Device", back_populates="keys")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Inventory(Base):
    __tablename__ = 'inventories'

    id = Column(Integer, primary_key=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey('devices.id', ondelete='CASCADE'))
    hw_data = Column(JSONB)
    sw_data = Column(JSONB)
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))

    device = relationship("Device", back_populates="inventories")
