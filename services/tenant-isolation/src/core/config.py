"""Configuration settings for Tenant Isolation Service."""

from pydantic import Field
from pydantic_settings import BaseSettings
from typing import List, Optional, Dict, Any
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""
    
    # Service configuration
    service_name: str = Field(default="tenant-isolation", env="SERVICE_NAME")
    service_port: int = Field(default=8027, env="SERVICE_PORT")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Database configuration
    database_url: str = Field(env="DATABASE_URL")
    
    # Redis configuration
    redis_url: str = Field(default="redis://localhost:6379/9", env="REDIS_URL")
    
    # Isolation settings
    isolation_enabled: bool = Field(default=True, env="ISOLATION_ENABLED")
    isolation_mode: str = Field(default="strict", env="ISOLATION_MODE")  # strict, moderate, minimal
    
    # Database isolation
    db_isolation_enabled: bool = Field(default=True, env="DB_ISOLATION_ENABLED")
    row_level_security_enabled: bool = Field(default=True, env="ROW_LEVEL_SECURITY_ENABLED")
    schema_isolation_enabled: bool = Field(default=True, env="SCHEMA_ISOLATION_ENABLED")
    connection_pool_isolation: bool = Field(default=True, env="CONNECTION_POOL_ISOLATION")
    
    # Storage isolation
    storage_isolation_enabled: bool = Field(default=True, env="STORAGE_ISOLATION_ENABLED")
    storage_path_isolation: bool = Field(default=True, env="STORAGE_PATH_ISOLATION")
    storage_encryption_per_tenant: bool = Field(default=True, env="STORAGE_ENCRYPTION_PER_TENANT")
    
    # Network isolation
    network_isolation_enabled: bool = Field(default=True, env="NETWORK_ISOLATION_ENABLED")
    api_namespace_isolation: bool = Field(default=True, env="API_NAMESPACE_ISOLATION")
    rate_limit_per_tenant: bool = Field(default=True, env="RATE_LIMIT_PER_TENANT")
    
    # Cache isolation
    cache_isolation_enabled: bool = Field(default=True, env="CACHE_ISOLATION_ENABLED")
    cache_key_prefix_per_tenant: bool = Field(default=True, env="CACHE_KEY_PREFIX_PER_TENANT")
    
    # Message queue isolation
    queue_isolation_enabled: bool = Field(default=True, env="QUEUE_ISOLATION_ENABLED")
    queue_prefix_per_tenant: bool = Field(default=True, env="QUEUE_PREFIX_PER_TENANT")
    
    # Security policies
    enforce_data_residency: bool = Field(default=True, env="ENFORCE_DATA_RESIDENCY")
    cross_tenant_access_allowed: bool = Field(default=False, env="CROSS_TENANT_ACCESS_ALLOWED")
    audit_cross_tenant_access: bool = Field(default=True, env="AUDIT_CROSS_TENANT_ACCESS")
    
    # Encryption settings
    tenant_encryption_enabled: bool = Field(default=True, env="TENANT_ENCRYPTION_ENABLED")
    encryption_key_per_tenant: bool = Field(default=True, env="ENCRYPTION_KEY_PER_TENANT")
    key_rotation_days: int = Field(default=90, env="KEY_ROTATION_DAYS")
    
    # Access control
    tenant_api_keys_enabled: bool = Field(default=True, env="TENANT_API_KEYS_ENABLED")
    tenant_jwt_validation: bool = Field(default=True, env="TENANT_JWT_VALIDATION")
    ip_whitelist_per_tenant: bool = Field(default=True, env="IP_WHITELIST_PER_TENANT")
    
    # Resource isolation
    cpu_quota_per_tenant: bool = Field(default=True, env="CPU_QUOTA_PER_TENANT")
    memory_quota_per_tenant: bool = Field(default=True, env="MEMORY_QUOTA_PER_TENANT")
    io_quota_per_tenant: bool = Field(default=True, env="IO_QUOTA_PER_TENANT")
    
    # Monitoring and logging
    tenant_specific_logging: bool = Field(default=True, env="TENANT_SPECIFIC_LOGGING")
    log_segregation_enabled: bool = Field(default=True, env="LOG_SEGREGATION_ENABLED")
    metrics_per_tenant: bool = Field(default=True, env="METRICS_PER_TENANT")
    
    # Compliance settings
    compliance_mode: Optional[str] = Field(default=None, env="COMPLIANCE_MODE")  # hipaa, gdpr, sox
    data_classification_enabled: bool = Field(default=True, env="DATA_CLASSIFICATION_ENABLED")
    pii_detection_enabled: bool = Field(default=True, env="PII_DETECTION_ENABLED")
    
    # Backup and recovery
    tenant_backup_isolation: bool = Field(default=True, env="TENANT_BACKUP_ISOLATION")
    backup_encryption_per_tenant: bool = Field(default=True, env="BACKUP_ENCRYPTION_PER_TENANT")
    
    # Performance optimization
    query_optimization_per_tenant: bool = Field(default=True, env="QUERY_OPTIMIZATION_PER_TENANT")
    index_per_tenant: bool = Field(default=True, env="INDEX_PER_TENANT")
    
    # Tenant context
    tenant_context_propagation: bool = Field(default=True, env="TENANT_CONTEXT_PROPAGATION")
    context_header_name: str = Field(default="X-Tenant-ID", env="CONTEXT_HEADER_NAME")
    
    # Validation settings
    strict_tenant_validation: bool = Field(default=True, env="STRICT_TENANT_VALIDATION")
    validate_all_requests: bool = Field(default=True, env="VALIDATE_ALL_REQUESTS")
    
    # Error handling
    mask_tenant_errors: bool = Field(default=True, env="MASK_TENANT_ERRORS")
    generic_error_messages: bool = Field(default=True, env="GENERIC_ERROR_MESSAGES")
    
    # Development settings
    bypass_isolation_for_admin: bool = Field(default=False, env="BYPASS_ISOLATION_FOR_ADMIN")
    debug_isolation_rules: bool = Field(default=False, env="DEBUG_ISOLATION_RULES")
    
    # Integration settings
    multi_tenant_service_url: str = Field(
        default="http://multi-tenant:8026",
        env="MULTI_TENANT_SERVICE_URL"
    )
    
    # Security settings
    allowed_origins: List[str] = Field(default=["http://localhost:3000"], env="ALLOWED_ORIGINS")
    api_key_header: str = Field(default="X-API-Key", env="API_KEY_HEADER")
    require_auth: bool = Field(default=True, env="REQUIRE_AUTH")
    
    # JWT settings
    jwt_secret_key: str = Field(env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_minutes: int = Field(default=60, env="JWT_EXPIRATION_MINUTES")
    
    # Rate limiting
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    requests_per_minute: int = Field(default=100, env="REQUESTS_PER_MINUTE")
    
    # Audit settings
    audit_enabled: bool = Field(default=True, env="AUDIT_ENABLED")
    audit_retention_days: int = Field(default=2555, env="AUDIT_RETENTION_DAYS")  # 7 years
    
    # Performance settings
    max_concurrent_operations: int = Field(default=100, env="MAX_CONCURRENT_OPERATIONS")
    operation_timeout: int = Field(default=30, env="OPERATION_TIMEOUT")  # seconds
    
    # Cache settings
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")  # seconds
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()