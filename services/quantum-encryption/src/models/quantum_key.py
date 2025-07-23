from sqlalchemy import Column, String, DateTime, Boolean, Integer, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from datetime import datetime
from enum import Enum
from ..db.base import Base

class KeyType(str, Enum):
    KEM = "kem"  # Key Encapsulation Mechanism
    SIGNATURE = "signature"
    HYBRID = "hybrid"
    SYMMETRIC = "symmetric"

class KeyStatus(str, Enum):
    ACTIVE = "active"
    ROTATED = "rotated"
    REVOKED = "revoked"
    EXPIRED = "expired"
    COMPROMISED = "compromised"

class AlgorithmType(str, Enum):
    # KEMs (Key Encapsulation Mechanisms)
    KYBER512 = "kyber512"
    KYBER768 = "kyber768"
    KYBER1024 = "kyber1024"
    NTRU_HPS2048509 = "ntru_hps2048509"
    NTRU_HPS2048677 = "ntru_hps2048677"
    NTRU_HPS4096821 = "ntru_hps4096821"
    SABER_LIGHT = "saber_light"
    SABER = "saber"
    SABER_FIRE = "saber_fire"
    
    # Digital Signatures
    DILITHIUM2 = "dilithium2"
    DILITHIUM3 = "dilithium3"
    DILITHIUM5 = "dilithium5"
    FALCON512 = "falcon512"
    FALCON1024 = "falcon1024"
    SPHINCS_SHA256_128F = "sphincs_sha256_128f"
    SPHINCS_SHA256_192F = "sphincs_sha256_192f"
    SPHINCS_SHA256_256F = "sphincs_sha256_256f"
    
    # Classical (for hybrid mode)
    RSA2048 = "rsa2048"
    RSA4096 = "rsa4096"
    ECC_P256 = "ecc_p256"
    ECC_P384 = "ecc_p384"
    ECC_P521 = "ecc_p521"
    AES256 = "aes256"

class QuantumKey(Base):
    __tablename__ = "quantum_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key_id = Column(String(255), unique=True, index=True, nullable=False)
    key_type = Column(SQLEnum(KeyType), nullable=False)
    algorithm = Column(SQLEnum(AlgorithmType), nullable=False)
    key_size = Column(Integer, nullable=False)
    
    # Key material (encrypted at rest)
    public_key = Column(String, nullable=False)
    private_key_encrypted = Column(String, nullable=True)  # Null for public-only keys
    
    # Hybrid mode fields
    classical_algorithm = Column(SQLEnum(AlgorithmType), nullable=True)
    classical_public_key = Column(String, nullable=True)
    classical_private_key_encrypted = Column(String, nullable=True)
    
    # Metadata
    owner_id = Column(String(255), index=True, nullable=False)
    purpose = Column(String(255), nullable=True)
    status = Column(SQLEnum(KeyStatus), default=KeyStatus.ACTIVE, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    rotated_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Security metadata
    security_level = Column(Integer, default=1)  # NIST security level (1-5)
    quantum_resistance_score = Column(Integer, default=100)  # 0-100
    
    # Relationships
    operations = relationship("QuantumOperation", back_populates="key")
    rotations = relationship("KeyRotation", back_populates="old_key", foreign_keys="KeyRotation.old_key_id")

class QuantumOperation(Base):
    __tablename__ = "quantum_operations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operation_id = Column(String(255), unique=True, index=True, nullable=False)
    operation_type = Column(String(50), nullable=False)  # encrypt, decrypt, sign, verify
    
    key_id = Column(UUID(as_uuid=True), ForeignKey("quantum_keys.id"), nullable=False)
    user_id = Column(String(255), index=True, nullable=False)
    
    # Operation details
    input_size = Column(Integer, nullable=True)
    output_size = Column(Integer, nullable=True)
    algorithm_used = Column(SQLEnum(AlgorithmType), nullable=False)
    
    # Performance metrics
    operation_time_ms = Column(Integer, nullable=True)
    cpu_usage_percent = Column(Integer, nullable=True)
    memory_usage_mb = Column(Integer, nullable=True)
    
    # Results
    success = Column(Boolean, default=True)
    error_message = Column(String, nullable=True)
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    key = relationship("QuantumKey", back_populates="operations")

class KeyRotation(Base):
    __tablename__ = "key_rotations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rotation_id = Column(String(255), unique=True, index=True, nullable=False)
    
    old_key_id = Column(UUID(as_uuid=True), ForeignKey("quantum_keys.id"), nullable=False)
    new_key_id = Column(UUID(as_uuid=True), ForeignKey("quantum_keys.id"), nullable=False)
    
    reason = Column(String(255), nullable=False)
    initiated_by = Column(String(255), nullable=False)
    
    # Migration status
    migration_status = Column(String(50), default="pending")  # pending, in_progress, completed, failed
    objects_to_migrate = Column(Integer, default=0)
    objects_migrated = Column(Integer, default=0)
    
    # Timestamps
    initiated_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    old_key = relationship("QuantumKey", foreign_keys=[old_key_id])
    new_key = relationship("QuantumKey", foreign_keys=[new_key_id])

class QuantumCertificate(Base):
    __tablename__ = "quantum_certificates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    certificate_id = Column(String(255), unique=True, index=True, nullable=False)
    
    # Certificate details
    subject = Column(String(500), nullable=False)
    issuer = Column(String(500), nullable=False)
    serial_number = Column(String(255), unique=True, nullable=False)
    
    # Quantum-safe signature
    signature_algorithm = Column(SQLEnum(AlgorithmType), nullable=False)
    signature = Column(String, nullable=False)
    
    # Certificate content
    certificate_data = Column(String, nullable=False)  # Base64 encoded
    public_key_id = Column(UUID(as_uuid=True), ForeignKey("quantum_keys.id"), nullable=False)
    
    # Validity
    not_before = Column(DateTime(timezone=True), nullable=False)
    not_after = Column(DateTime(timezone=True), nullable=False)
    
    # Status
    is_ca = Column(Boolean, default=False)
    is_revoked = Column(Boolean, default=False)
    revocation_date = Column(DateTime(timezone=True), nullable=True)
    revocation_reason = Column(String(255), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    public_key = relationship("QuantumKey")

class EncryptedData(Base):
    __tablename__ = "encrypted_data"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    data_id = Column(String(255), unique=True, index=True, nullable=False)
    
    # Encryption details
    key_id = Column(UUID(as_uuid=True), ForeignKey("quantum_keys.id"), nullable=False)
    algorithm_used = Column(SQLEnum(AlgorithmType), nullable=False)
    
    # Data references
    data_type = Column(String(50), nullable=False)  # file, database_field, message, etc.
    data_reference = Column(String(500), nullable=False)  # Path, table.column, etc.
    
    # Encryption metadata
    original_size = Column(Integer, nullable=True)
    encrypted_size = Column(Integer, nullable=True)
    encryption_mode = Column(String(50), nullable=True)  # CBC, GCM, etc.
    
    # Access control
    owner_id = Column(String(255), index=True, nullable=False)
    access_policy = Column(JSON, nullable=True)
    
    # Timestamps
    encrypted_at = Column(DateTime(timezone=True), server_default=func.now())
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationship
    key = relationship("QuantumKey")