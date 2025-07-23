"""
Configuration for Storage Abstraction Service

This module handles all configuration settings for the storage service.
"""

from typing import Optional, Dict, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator
import os
from pathlib import Path


class Settings(BaseSettings):
    """Storage service configuration settings"""
    
    # Service Information
    service_name: str = Field(
        default="storage-abstraction",
        description="Service name"
    )
    service_version: str = Field(
        default="1.0.0",
        description="Service version"
    )
    
    # Environment
    environment: str = Field(
        default="development",
        description="Environment (development, staging, production)"
    )
    debug: bool = Field(
        default=False,
        description="Debug mode"
    )
    
    # API Configuration
    host: str = Field(
        default="0.0.0.0",
        description="API host"
    )
    port: int = Field(
        default=8003,
        description="API port"
    )
    api_prefix: str = Field(
        default="/api/v1",
        description="API route prefix"
    )
    
    # Database Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://mams:password@localhost:5432/mams_storage",
        description="PostgreSQL database URL"
    )
    database_pool_size: int = Field(
        default=20,
        description="Database connection pool size"
    )
    database_pool_overflow: int = Field(
        default=10,
        description="Database connection pool overflow"
    )
    
    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379/2",
        description="Redis URL for caching"
    )
    redis_pool_size: int = Field(
        default=10,
        description="Redis connection pool size"
    )
    
    # Storage Configuration
    default_storage_driver: str = Field(
        default="local",
        description="Default storage driver to use"
    )
    storage_drivers: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Storage driver configurations"
    )
    
    # Local Storage Settings
    local_storage_root: str = Field(
        default="/var/mams/storage",
        description="Root directory for local storage"
    )
    local_storage_permissions: int = Field(
        default=0o755,
        description="Default permissions for local directories"
    )
    
    # S3 Storage Settings
    s3_endpoint_url: Optional[str] = Field(
        default=None,
        description="S3 endpoint URL (for MinIO or custom S3)"
    )
    s3_access_key_id: Optional[str] = Field(
        default=None,
        description="S3 access key ID"
    )
    s3_secret_access_key: Optional[str] = Field(
        default=None,
        description="S3 secret access key"
    )
    s3_default_bucket: Optional[str] = Field(
        default=None,
        description="Default S3 bucket"
    )
    s3_region: str = Field(
        default="us-east-1",
        description="S3 region"
    )
    s3_use_ssl: bool = Field(
        default=True,
        description="Use SSL for S3 connections"
    )
    
    # Azure Blob Storage Settings
    azure_account_name: Optional[str] = Field(
        default=None,
        description="Azure storage account name"
    )
    azure_account_key: Optional[str] = Field(
        default=None,
        description="Azure storage account key"
    )
    azure_connection_string: Optional[str] = Field(
        default=None,
        description="Azure storage connection string"
    )
    azure_container_name: Optional[str] = Field(
        default=None,
        description="Azure blob container name"
    )
    azure_sas_token: Optional[str] = Field(
        default=None,
        description="Azure SAS token for authentication"
    )
    azure_endpoint_suffix: str = Field(
        default="core.windows.net",
        description="Azure endpoint suffix"
    )
    
    # Google Cloud Storage Settings
    gcs_project_id: Optional[str] = Field(
        default=None,
        description="GCS project ID"
    )
    gcs_bucket_name: Optional[str] = Field(
        default=None,
        description="GCS bucket name"
    )
    gcs_credentials_path: Optional[str] = Field(
        default=None,
        description="Path to GCS service account credentials JSON file"
    )
    gcs_credentials_json: Optional[str] = Field(
        default=None,
        description="GCS service account credentials as JSON string"
    )
    gcs_location: str = Field(
        default="US",
        description="GCS bucket location"
    )
    gcs_storage_class: str = Field(
        default="STANDARD",
        description="Default GCS storage class"
    )
    
    # Upload/Download Settings
    chunk_size: int = Field(
        default=8192,  # 8KB
        description="Default chunk size for streaming"
    )
    multipart_threshold: int = Field(
        default=100 * 1024 * 1024,  # 100MB
        description="Threshold for multipart uploads"
    )
    multipart_chunk_size: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        description="Chunk size for multipart uploads"
    )
    max_upload_size: int = Field(
        default=5 * 1024 * 1024 * 1024,  # 5GB
        description="Maximum upload size"
    )
    upload_timeout: int = Field(
        default=3600,  # 1 hour
        description="Upload timeout in seconds"
    )
    temp_directory: str = Field(
        default="/tmp/mams-storage",
        description="Directory for temporary files and resumable uploads"
    )
    
    # Presigned URL Settings
    presigned_url_expiry: int = Field(
        default=3600,  # 1 hour
        description="Default presigned URL expiry in seconds"
    )
    max_presigned_url_expiry: int = Field(
        default=604800,  # 7 days
        description="Maximum presigned URL expiry in seconds"
    )
    
    # Storage Tiering
    enable_storage_tiers: bool = Field(
        default=True,
        description="Enable storage tier management"
    )
    hot_tier_days: int = Field(
        default=30,
        description="Days before moving from hot to warm tier"
    )
    warm_tier_days: int = Field(
        default=90,
        description="Days before moving from warm to cold tier"
    )
    cold_tier_days: int = Field(
        default=365,
        description="Days before moving from cold to archive tier"
    )
    
    # Quota Management
    enable_quotas: bool = Field(
        default=True,
        description="Enable storage quota management"
    )
    default_user_quota: int = Field(
        default=100 * 1024 * 1024 * 1024,  # 100GB
        description="Default user quota in bytes"
    )
    default_project_quota: int = Field(
        default=1024 * 1024 * 1024 * 1024,  # 1TB
        description="Default project quota in bytes"
    )
    
    # Security
    enable_encryption: bool = Field(
        default=True,
        description="Enable encryption at rest"
    )
    encryption_algorithm: str = Field(
        default="AES256",
        description="Encryption algorithm"
    )
    enable_virus_scan: bool = Field(
        default=True,
        description="Enable virus scanning on uploads"
    )
    allowed_file_extensions: Optional[str] = Field(
        default=None,
        description="Comma-separated list of allowed file extensions"
    )
    blocked_file_extensions: str = Field(
        default=".exe,.bat,.cmd,.com,.scr,.vbs,.js",
        description="Comma-separated list of blocked file extensions"
    )
    
    # Performance
    enable_caching: bool = Field(
        default=True,
        description="Enable metadata caching"
    )
    cache_ttl: int = Field(
        default=300,  # 5 minutes
        description="Cache TTL in seconds"
    )
    enable_compression: bool = Field(
        default=True,
        description="Enable compression for suitable files"
    )
    compression_mime_types: str = Field(
        default="text/*,application/json,application/xml",
        description="MIME types to compress"
    )
    
    # Monitoring
    enable_metrics: bool = Field(
        default=True,
        description="Enable Prometheus metrics"
    )
    metrics_port: int = Field(
        default=9093,
        description="Prometheus metrics port"
    )
    enable_tracing: bool = Field(
        default=False,
        description="Enable OpenTelemetry tracing"
    )
    
    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    log_format: str = Field(
        default="json",
        description="Log format (json or text)"
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )
    
    @validator("storage_drivers", pre=True)
    def parse_storage_drivers(cls, v):
        """Parse storage driver configurations from environment"""
        if not v:
            # Default configurations
            return {
                "local": {
                    "type": "local",
                    "root": os.environ.get("LOCAL_STORAGE_ROOT", "/var/mams/storage")
                },
                "s3": {
                    "type": "s3",
                    "endpoint_url": os.environ.get("S3_ENDPOINT_URL"),
                    "access_key_id": os.environ.get("S3_ACCESS_KEY_ID"),
                    "secret_access_key": os.environ.get("S3_SECRET_ACCESS_KEY"),
                    "bucket": os.environ.get("S3_DEFAULT_BUCKET", "mams-storage"),
                    "region": os.environ.get("S3_REGION", "us-east-1")
                },
                "azure": {
                    "type": "azure_blob",
                    "account_name": os.environ.get("AZURE_ACCOUNT_NAME"),
                    "account_key": os.environ.get("AZURE_ACCOUNT_KEY"),
                    "connection_string": os.environ.get("AZURE_CONNECTION_STRING"),
                    "container_name": os.environ.get("AZURE_CONTAINER_NAME", "mams-storage"),
                    "sas_token": os.environ.get("AZURE_SAS_TOKEN"),
                    "endpoint_suffix": os.environ.get("AZURE_ENDPOINT_SUFFIX", "core.windows.net")
                },
                "gcs": {
                    "type": "gcs",
                    "project_id": os.environ.get("GCS_PROJECT_ID"),
                    "bucket_name": os.environ.get("GCS_BUCKET_NAME", "mams-storage"),
                    "credentials_path": os.environ.get("GCS_CREDENTIALS_PATH"),
                    "credentials_json": os.environ.get("GCS_CREDENTIALS_JSON"),
                    "location": os.environ.get("GCS_LOCATION", "US"),
                    "storage_class": os.environ.get("GCS_STORAGE_CLASS", "STANDARD")
                }
            }
        return v
    
    @validator("allowed_file_extensions", "blocked_file_extensions")
    def parse_extensions(cls, v):
        """Parse comma-separated extensions into list"""
        if v and isinstance(v, str):
            return [ext.strip() for ext in v.split(",") if ext.strip()]
        return v
    
    @validator("local_storage_root")
    def ensure_storage_root(cls, v):
        """Ensure storage root directory exists"""
        if v:
            path = Path(v)
            path.mkdir(parents=True, exist_ok=True)
        return v
    
    def get_storage_driver_config(self, driver_name: str) -> Dict[str, Any]:
        """Get configuration for a specific storage driver"""
        if driver_name not in self.storage_drivers:
            raise ValueError(f"Unknown storage driver: {driver_name}")
        
        config = self.storage_drivers[driver_name].copy()
        
        # Add common settings
        config.update({
            "chunk_size": self.chunk_size,
            "multipart_threshold": self.multipart_threshold,
            "multipart_chunk_size": self.multipart_chunk_size,
            "enable_encryption": self.enable_encryption,
            "encryption_algorithm": self.encryption_algorithm
        })
        
        return config


# Create a cached instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get cached settings instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset settings cache (useful for testing)"""
    global _settings
    _settings = None