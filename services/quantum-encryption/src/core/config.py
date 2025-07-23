from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Service configuration
    service_name: str = "quantum-encryption"
    service_port: int = 8020
    debug: bool = False
    log_level: str = "INFO"
    
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/quantum_encryption"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # JWT
    jwt_secret_key: str = "your-secret-key-here"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60
    
    # Quantum Encryption Settings
    quantum_key_size: int = 256  # bits
    enable_hybrid_mode: bool = True  # Use both classical and quantum-resistant algorithms
    key_rotation_days: int = 90
    max_key_age_days: int = 365
    
    # Algorithm Selection
    default_kem_algorithm: str = "kyber1024"  # Key Encapsulation Mechanism
    default_signature_algorithm: str = "dilithium5"  # Digital Signatures
    default_hash_algorithm: str = "sphincs256"  # Hash-based signatures
    
    # Performance Settings
    enable_key_caching: bool = True
    cache_ttl_seconds: int = 3600
    max_concurrent_operations: int = 100
    
    # Security Settings
    enable_key_escrow: bool = False
    require_multi_signature: bool = False
    min_signature_threshold: int = 2
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()