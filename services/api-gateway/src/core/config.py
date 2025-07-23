"""
API Gateway Configuration

Centralized configuration management using Pydantic settings.
Environment variables override defaults.
"""

import os
from typing import List, Optional, Dict, Any
from pydantic import validator, Field
from pydantic_settings import BaseSettings
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """API Gateway settings"""
    
    # Application settings
    app_name: str = "MAMS API Gateway"
    version: str = "1.0.0"
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Server settings
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # Security settings
    secret_key: str = Field(..., env="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_minutes: int = Field(default=60, env="JWT_EXPIRATION_MINUTES")
    refresh_token_expiration_days: int = Field(default=30, env="REFRESH_TOKEN_EXPIRATION_DAYS")
    
    # CORS settings
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001"],
        env="CORS_ORIGINS"
    )
    cors_origin_patterns: List[str] = Field(
        default=[],
        env="CORS_ORIGIN_PATTERNS"
    )
    cors_allow_credentials: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")
    cors_allowed_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
        env="CORS_ALLOWED_METHODS"
    )
    cors_allowed_headers: List[str] = Field(
        default=["*"],
        env="CORS_ALLOWED_HEADERS"
    )
    cors_exposed_headers: List[str] = Field(
        default=[],
        env="CORS_EXPOSED_HEADERS"
    )
    cors_max_age: int = Field(default=86400, env="CORS_MAX_AGE")  # 24 hours
    allowed_hosts: Optional[List[str]] = Field(default=None, env="ALLOWED_HOSTS")
    
    # Rate limiting
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, env="RATE_LIMIT_WINDOW")  # seconds
    rate_limit_burst: int = Field(default=20, env="RATE_LIMIT_BURST")
    
    # Redis configuration
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_pool_size: int = Field(default=20, env="REDIS_POOL_SIZE")
    
    # Database settings (for gateway metadata)
    database_url: str = Field(
        default="postgresql://mams_app:mams_dev_password@localhost:5432/mams_gateway",
        env="DATABASE_URL"
    )
    
    # Service discovery
    service_discovery_url: str = Field(
        default="http://localhost:8500",
        env="SERVICE_DISCOVERY_URL"
    )
    
    # Downstream services
    services: Dict[str, str] = Field(
        default={
            "user-management": "http://localhost:8001",
            "asset-management": "http://localhost:8002",
            "metadata-service": "http://localhost:8003",
            "search-engine": "http://localhost:8004",
            "storage-abstraction": "http://localhost:8005",
            "ingest-service": "http://localhost:8006",
            "proxy-generation": "http://localhost:8007",
            "workflow-engine": "http://localhost:8008",
            "ai-ml-service": "http://localhost:8009",
            "rights-management": "http://localhost:8010",
            "monitoring-logging": "http://localhost:8011",
            "integration-service": "http://localhost:8012"
        },
        env="SERVICES"
    )
    
    # Logging configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    
    # Monitoring and observability
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    jaeger_endpoint: Optional[str] = Field(default=None, env="JAEGER_ENDPOINT")
    
    # API versioning
    api_v1_prefix: str = Field(default="/api/v1", env="API_V1_PREFIX")
    current_api_version: str = Field(default="v1", env="CURRENT_API_VERSION")
    
    # OpenAPI/Swagger configuration
    openapi_enabled: bool = Field(default=True, env="OPENAPI_ENABLED")
    openapi_url: str = Field(default="/openapi.json", env="OPENAPI_URL")
    docs_url: str = Field(default="/docs", env="DOCS_URL")
    redoc_url: str = Field(default="/redoc", env="REDOC_URL")
    
    # Request/Response limits
    max_request_size: int = Field(default=10485760, env="MAX_REQUEST_SIZE")  # 10MB
    request_timeout: int = Field(default=30, env="REQUEST_TIMEOUT")  # seconds
    
    # Health check settings
    health_check_timeout: int = Field(default=5, env="HEALTH_CHECK_TIMEOUT")
    health_check_interval: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")
    
    # Circuit breaker settings
    circuit_breaker_failure_threshold: int = Field(default=5, env="CIRCUIT_BREAKER_FAILURE_THRESHOLD")
    circuit_breaker_recovery_timeout: int = Field(default=60, env="CIRCUIT_BREAKER_RECOVERY_TIMEOUT")
    circuit_breaker_expected_exception: str = Field(
        default="requests.exceptions.RequestException",
        env="CIRCUIT_BREAKER_EXPECTED_EXCEPTION"
    )
    
    # Authentication settings
    auth_header_name: str = Field(default="Authorization", env="AUTH_HEADER_NAME")
    auth_header_prefix: str = Field(default="Bearer", env="AUTH_HEADER_PREFIX")
    api_key_header_name: str = Field(default="X-API-Key", env="API_KEY_HEADER_NAME")
    
    # Service mesh settings
    service_mesh_enabled: bool = Field(default=False, env="SERVICE_MESH_ENABLED")
    service_mesh_namespace: str = Field(default="mams", env="SERVICE_MESH_NAMESPACE")
    
    # IP Whitelist settings
    ip_whitelist_enabled: bool = Field(default=False, env="IP_WHITELIST_ENABLED")
    ip_whitelist_mode: str = Field(default="whitelist", env="IP_WHITELIST_MODE")
    ip_whitelist_allowed_ips: List[str] = Field(default_factory=list, env="IP_WHITELIST_ALLOWED_IPS")
    ip_whitelist_blocked_ips: List[str] = Field(default_factory=list, env="IP_WHITELIST_BLOCKED_IPS")
    ip_whitelist_admin_ips: List[str] = Field(default_factory=list, env="IP_WHITELIST_ADMIN_IPS")
    ip_whitelist_trust_proxy_headers: bool = Field(default=True, env="IP_WHITELIST_TRUST_PROXY_HEADERS")
    ip_whitelist_enable_rate_limiting: bool = Field(default=True, env="IP_WHITELIST_ENABLE_RATE_LIMITING")
    ip_whitelist_rate_limit_requests: int = Field(default=1000, env="IP_WHITELIST_RATE_LIMIT_REQUESTS")
    ip_whitelist_rate_limit_window: int = Field(default=3600, env="IP_WHITELIST_RATE_LIMIT_WINDOW")
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("cors_origin_patterns", pre=True)
    def parse_cors_patterns(cls, v):
        """Parse CORS origin patterns from comma-separated string"""
        if isinstance(v, str) and v:
            return [pattern.strip() for pattern in v.split(",")]
        return v
    
    @validator("cors_allowed_methods", pre=True)
    def parse_cors_methods(cls, v):
        """Parse CORS allowed methods from comma-separated string"""
        if isinstance(v, str):
            return [method.strip().upper() for method in v.split(",")]
        return v
    
    @validator("cors_allowed_headers", pre=True)
    def parse_cors_headers(cls, v):
        """Parse CORS allowed headers from comma-separated string"""
        if isinstance(v, str) and v != "*":
            return [header.strip() for header in v.split(",")]
        return v
    
    @validator("cors_exposed_headers", pre=True)
    def parse_cors_exposed_headers(cls, v):
        """Parse CORS exposed headers from comma-separated string"""
        if isinstance(v, str) and v:
            return [header.strip() for header in v.split(",")]
        return v
    
    @validator("allowed_hosts", pre=True)
    def parse_allowed_hosts(cls, v):
        """Parse allowed hosts from comma-separated string"""
        if isinstance(v, str) and v:
            return [host.strip() for host in v.split(",")]
        return v
    
    @validator("services", pre=True)
    def parse_services(cls, v):
        """Parse services from JSON string or dict"""
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON for services config, using defaults")
                return {}
        return v
    
    @validator("secret_key")
    def validate_secret_key(cls, v):
        """Validate secret key is not empty"""
        if not v or len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v
    
    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment value"""
        allowed_envs = ["development", "staging", "production"]
        if v not in allowed_envs:
            raise ValueError(f"Environment must be one of {allowed_envs}")
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level"""
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed_levels:
            raise ValueError(f"Log level must be one of {allowed_levels}")
        return v.upper()
    
    @validator("ip_whitelist_allowed_ips", "ip_whitelist_blocked_ips", "ip_whitelist_admin_ips", pre=True)
    def parse_ip_list(cls, v):
        """Parse IP list from comma-separated string"""
        if isinstance(v, str) and v:
            return [ip.strip() for ip in v.split(",")]
        return v
    
    @validator("ip_whitelist_mode")
    def validate_ip_whitelist_mode(cls, v):
        """Validate IP whitelist mode"""
        allowed_modes = ["whitelist", "blacklist"]
        if v not in allowed_modes:
            raise ValueError(f"IP whitelist mode must be one of {allowed_modes}")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        @classmethod
        def customise_sources(
            cls,
            init_settings,
            env_settings,
            file_secret_settings,
        ):
            return (
                init_settings,
                env_settings,
                file_secret_settings,
            )


# Development settings
class DevelopmentSettings(Settings):
    """Development environment settings"""
    debug: bool = True
    log_level: str = "DEBUG"
    cors_origins: List[str] = ["*"]
    
    class Config:
        env_prefix = "DEV_"


# Staging settings
class StagingSettings(Settings):
    """Staging environment settings"""
    debug: bool = False
    log_level: str = "INFO"
    
    class Config:
        env_prefix = "STAGING_"


# Production settings
class ProductionSettings(Settings):
    """Production environment settings"""
    debug: bool = False
    log_level: str = "WARNING"
    
    class Config:
        env_prefix = "PROD_"


@lru_cache()
def get_settings() -> Settings:
    """Get application settings (cached)"""
    environment = os.getenv("ENVIRONMENT", "development").lower()
    
    if environment == "development":
        return DevelopmentSettings()
    elif environment == "staging":
        return StagingSettings()
    elif environment == "production":
        return ProductionSettings()
    else:
        return Settings()


# Export commonly used settings
settings = get_settings()