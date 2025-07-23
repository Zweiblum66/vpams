"""
Configuration for Asset Management Service

This module handles all configuration settings using Pydantic Settings.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Optional, List, Dict, Any
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Service Information
    service_name: str = "asset-management"
    service_version: str = "1.0.0"
    service_port: int = Field(default=8003, env="SERVICE_PORT")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8003, env="PORT")
    
    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://mams:mams@localhost:5432/mams_assets",
        env="DATABASE_URL"
    )
    db_pool_size: int = Field(default=10, env="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW")
    
    # Storage Service
    storage_service_url: str = Field(
        default="http://localhost:8002",
        env="STORAGE_SERVICE_URL"
    )
    storage_service_timeout: int = Field(default=30, env="STORAGE_SERVICE_TIMEOUT")
    default_storage_driver: str = Field(default="local", env="DEFAULT_STORAGE_DRIVER")
    
    # User Management Service
    user_service_url: str = Field(
        default="http://localhost:8001",
        env="USER_SERVICE_URL"
    )
    
    # File Processing
    max_upload_size: int = Field(
        default=10 * 1024 * 1024 * 1024,  # 10GB
        env="MAX_UPLOAD_SIZE"
    )
    allowed_mime_types: List[str] = Field(
        default=[
            # Video
            "video/mp4", "video/quicktime", "video/x-msvideo", "video/x-matroska",
            "video/webm", "video/mpeg", "video/x-ms-wmv", "video/x-flv",
            # Audio
            "audio/mpeg", "audio/wav", "audio/x-wav", "audio/aac", "audio/ogg",
            "audio/flac", "audio/x-m4a", "audio/mp4",
            # Image
            "image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp",
            "image/tiff", "image/svg+xml", "image/x-icon",
            # Document
            "application/pdf", "text/plain", "text/html", "text/xml",
            "application/json", "application/xml",
            # Subtitle
            "text/vtt", "application/x-subrip", "text/plain",
        ],
        env="ALLOWED_MIME_TYPES"
    )
    chunk_size: int = Field(default=5 * 1024 * 1024, env="CHUNK_SIZE")  # 5MB
    
    # Asset Processing
    enable_virus_scan: bool = Field(default=True, env="ENABLE_VIRUS_SCAN")
    enable_duplicate_detection: bool = Field(default=True, env="ENABLE_DUPLICATE_DETECTION")
    auto_generate_thumbnails: bool = Field(default=True, env="AUTO_GENERATE_THUMBNAILS")
    auto_extract_metadata: bool = Field(default=True, env="AUTO_EXTRACT_METADATA")
    
    # Versioning
    max_versions_per_asset: int = Field(default=10, env="MAX_VERSIONS_PER_ASSET")
    auto_archive_old_versions: bool = Field(default=True, env="AUTO_ARCHIVE_OLD_VERSIONS")
    
    # Security
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_minutes: int = Field(default=60, env="JWT_EXPIRATION_MINUTES")
    
    # API Settings
    api_prefix: str = Field(default="/api/v1", env="API_PREFIX")
    docs_url: Optional[str] = Field(default="/docs", env="DOCS_URL")
    redoc_url: Optional[str] = Field(default="/redoc", env="REDOC_URL")
    openapi_url: Optional[str] = Field(default="/openapi.json", env="OPENAPI_URL")
    
    # Pagination
    default_page_size: int = Field(default=20, env="DEFAULT_PAGE_SIZE")
    max_page_size: int = Field(default=100, env="MAX_PAGE_SIZE")
    
    # Caching
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    cache_ttl: int = Field(default=300, env="CACHE_TTL")  # 5 minutes
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")  # json or text
    
    # CORS
    cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    
    # Monitoring
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    
    # External Services
    virus_scan_api_url: Optional[str] = Field(default=None, env="VIRUS_SCAN_API_URL")
    virus_scan_api_key: Optional[str] = Field(default=None, env="VIRUS_SCAN_API_KEY")
    
    # Storage Tiers
    storage_tiers: Dict[str, Dict[str, Any]] = Field(
        default={
            "hot": {
                "drivers": ["local", "s3"],
                "retention_days": 30,
                "auto_migrate": True
            },
            "warm": {
                "drivers": ["s3"],
                "retention_days": 90,
                "auto_migrate": True
            },
            "cold": {
                "drivers": ["s3", "azure"],
                "retention_days": 365,
                "auto_migrate": True
            },
            "archive": {
                "drivers": ["s3", "azure"],
                "retention_days": None,
                "auto_migrate": False
            }
        },
        env="STORAGE_TIERS"
    )
    
    @validator("database_url")
    def validate_database_url(cls, v):
        """Ensure database URL uses asyncpg for async support"""
        if "postgresql://" in v and "+asyncpg" not in v:
            return v.replace("postgresql://", "postgresql+asyncpg://")
        return v
    
    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment name"""
        allowed = ["development", "staging", "production", "testing"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of: {', '.join(allowed)}")
        return v
    
    @validator("docs_url", "redoc_url", "openapi_url")
    def disable_docs_in_production(cls, v, values):
        """Disable API docs in production"""
        if values.get("environment") == "production" and v is not None:
            return None
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance
    
    Returns:
        Settings: Application settings
    """
    return Settings()