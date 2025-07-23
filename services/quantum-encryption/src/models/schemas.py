from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

from .quantum_key import KeyType, KeyStatus, AlgorithmType

# Enums for API
class OperationType(str, Enum):
    ENCRYPT = "encrypt"
    DECRYPT = "decrypt"
    SIGN = "sign"
    VERIFY = "verify"
    KEY_EXCHANGE = "key_exchange"

class SecurityLevel(int, Enum):
    LEVEL_1 = 1  # 128-bit classical security
    LEVEL_2 = 2  # 192-bit classical security
    LEVEL_3 = 3  # 256-bit classical security
    LEVEL_4 = 4  # 384-bit classical security
    LEVEL_5 = 5  # 512-bit classical security

# Base schemas
class QuantumKeyBase(BaseModel):
    key_type: KeyType
    algorithm: AlgorithmType
    owner_id: str
    purpose: Optional[str] = None
    security_level: SecurityLevel = SecurityLevel.LEVEL_3

class QuantumKeyCreate(QuantumKeyBase):
    enable_hybrid: bool = True
    classical_algorithm: Optional[AlgorithmType] = AlgorithmType.ECC_P384
    expiration_days: Optional[int] = 365

class QuantumKeyUpdate(BaseModel):
    purpose: Optional[str] = None
    status: Optional[KeyStatus] = None

class QuantumKeyResponse(QuantumKeyBase):
    id: uuid.UUID
    key_id: str
    key_size: int
    public_key: str
    status: KeyStatus
    classical_algorithm: Optional[AlgorithmType] = None
    classical_public_key: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    quantum_resistance_score: int
    
    class Config:
        from_attributes = True

# Operation schemas
class EncryptRequest(BaseModel):
    data: str  # Base64 encoded data
    key_id: str
    use_hybrid: bool = True
    metadata: Optional[Dict[str, Any]] = None

class EncryptResponse(BaseModel):
    encrypted_data: str  # Base64 encoded
    encryption_key_id: str
    algorithm_used: AlgorithmType
    hybrid_mode: bool
    operation_id: str
    metadata: Optional[Dict[str, Any]] = None

class DecryptRequest(BaseModel):
    encrypted_data: str  # Base64 encoded
    key_id: str
    operation_id: Optional[str] = None

class DecryptResponse(BaseModel):
    decrypted_data: str  # Base64 encoded
    operation_id: str
    verified: bool

class SignRequest(BaseModel):
    data: str  # Base64 encoded data to sign
    key_id: str
    hash_algorithm: Optional[str] = "SHA3-512"
    metadata: Optional[Dict[str, Any]] = None

class SignResponse(BaseModel):
    signature: str  # Base64 encoded signature
    key_id: str
    algorithm_used: AlgorithmType
    hash_algorithm: str
    operation_id: str

class VerifyRequest(BaseModel):
    data: str  # Base64 encoded original data
    signature: str  # Base64 encoded signature
    key_id: str
    hash_algorithm: Optional[str] = "SHA3-512"

class VerifyResponse(BaseModel):
    valid: bool
    key_id: str
    algorithm_used: AlgorithmType
    operation_id: str
    details: Optional[str] = None

# Key exchange schemas
class KeyExchangeInitRequest(BaseModel):
    party_id: str
    algorithm: AlgorithmType = AlgorithmType.KYBER1024
    security_level: SecurityLevel = SecurityLevel.LEVEL_3

class KeyExchangeInitResponse(BaseModel):
    session_id: str
    public_key: str
    algorithm: AlgorithmType
    expires_at: datetime

class KeyExchangeCompleteRequest(BaseModel):
    session_id: str
    public_key: str  # Other party's public key
    ciphertext: Optional[str] = None  # For KEM algorithms

class KeyExchangeCompleteResponse(BaseModel):
    shared_secret: str  # Base64 encoded shared secret
    session_id: str
    algorithm: AlgorithmType

# Certificate schemas
class CertificateCreateRequest(BaseModel):
    subject: str
    key_id: str
    validity_days: int = 365
    is_ca: bool = False
    extensions: Optional[Dict[str, Any]] = None

class CertificateResponse(BaseModel):
    id: uuid.UUID
    certificate_id: str
    subject: str
    issuer: str
    serial_number: str
    certificate_data: str  # Base64 encoded certificate
    not_before: datetime
    not_after: datetime
    is_ca: bool
    is_revoked: bool
    
    class Config:
        from_attributes = True

# Key rotation schemas
class KeyRotationRequest(BaseModel):
    old_key_id: str
    reason: str
    migrate_data: bool = True

class KeyRotationResponse(BaseModel):
    rotation_id: str
    old_key_id: str
    new_key_id: str
    new_public_key: str
    migration_status: str
    objects_to_migrate: int

class KeyRotationStatus(BaseModel):
    rotation_id: str
    migration_status: str
    objects_migrated: int
    objects_to_migrate: int
    progress_percentage: float
    estimated_completion: Optional[datetime] = None

# Analytics schemas
class QuantumMetrics(BaseModel):
    total_keys: int
    active_keys: int
    operations_today: int
    operations_this_month: int
    average_operation_time_ms: float
    most_used_algorithm: AlgorithmType
    quantum_resistance_average: float
    key_rotation_compliance: float

class AlgorithmStats(BaseModel):
    algorithm: AlgorithmType
    usage_count: int
    average_operation_time_ms: float
    success_rate: float
    security_level: SecurityLevel

class SecurityAssessment(BaseModel):
    overall_score: float  # 0-100
    quantum_readiness: float  # 0-100
    key_rotation_health: float  # 0-100
    algorithm_diversity: float  # 0-100
    recommendations: List[str]
    vulnerabilities: List[str]

# Batch operation schemas
class BatchEncryptRequest(BaseModel):
    items: List[EncryptRequest]
    parallel: bool = True

class BatchEncryptResponse(BaseModel):
    results: List[EncryptResponse]
    total_time_ms: int
    success_count: int
    failure_count: int

# Migration schemas
class MigrationRequest(BaseModel):
    source_algorithm: AlgorithmType
    target_algorithm: AlgorithmType
    key_pattern: Optional[str] = None  # Regex pattern to match keys
    dry_run: bool = True

class MigrationResponse(BaseModel):
    migration_id: str
    keys_to_migrate: int
    estimated_time_minutes: float
    dry_run: bool
    
# Health check schema
class HealthResponse(BaseModel):
    status: str
    service: str = "quantum-encryption"
    version: str = "1.0.0"
    quantum_ready: bool = True
    supported_algorithms: List[AlgorithmType]
    timestamp: datetime = Field(default_factory=datetime.utcnow)