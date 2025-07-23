"""
Configuration settings for Metadata Service
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import List, Optional
import os


class Settings(BaseSettings):
    """
    Application settings with validation
    """
    # Service Info
    SERVICE_NAME: str = "metadata-service"
    SERVICE_PORT: int = Field(default=8005, ge=1, le=65535)
    DEBUG: bool = Field(default=False)
    LOG_LEVEL: str = Field(default="INFO")
    
    # MongoDB Configuration
    MONGODB_URL: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection URL"
    )
    MONGODB_DATABASE: str = Field(
        default="mams_metadata",
        description="MongoDB database name"
    )
    MONGODB_MAX_POOL_SIZE: int = Field(default=10, ge=1)
    MONGODB_MIN_POOL_SIZE: int = Field(default=1, ge=1)
    
    # Redis Configuration (for caching)
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    CACHE_TTL: int = Field(default=3600, description="Cache TTL in seconds")
    
    # Authentication
    JWT_SECRET_KEY: str = Field(
        default="your-secret-key-here",
        description="JWT secret key"
    )
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_EXPIRATION_MINUTES: int = Field(default=60, ge=1)
    
    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"]
    )
    
    # Storage Service Integration
    STORAGE_SERVICE_URL: str = Field(
        default="http://storage-service:8003",
        description="Storage service URL"
    )
    
    # Asset Management Service Integration
    ASSET_SERVICE_URL: str = Field(
        default="http://asset-management:8004",
        description="Asset management service URL"
    )
    
    # Search Engine Integration
    SEARCH_SERVICE_URL: str = Field(
        default="http://search-engine:8006",
        description="Search engine service URL"
    )
    
    # Metadata Extraction
    ENABLE_AUTO_EXTRACTION: bool = Field(
        default=True,
        description="Enable automatic metadata extraction"
    )
    EXTRACTION_QUEUE: str = Field(
        default="metadata_extraction",
        description="Queue name for extraction tasks"
    )
    
    # Schema Validation
    STRICT_SCHEMA_VALIDATION: bool = Field(
        default=True,
        description="Enforce strict schema validation"
    )
    MAX_SCHEMA_FIELDS: int = Field(
        default=100,
        description="Maximum number of fields in a schema"
    )
    
    # File Processing Tools
    FFPROBE_PATH: str = Field(
        default="/usr/bin/ffprobe",
        description="Path to ffprobe executable"
    )
    EXIFTOOL_PATH: str = Field(
        default="/usr/bin/exiftool",
        description="Path to exiftool executable"
    )
    
    # Performance
    MAX_BATCH_SIZE: int = Field(default=100, ge=1, le=1000)
    REQUEST_TIMEOUT: int = Field(default=30, ge=1)
    
    @field_validator("MONGODB_URL")
    def validate_mongodb_url(cls, v):
        if not v.startswith(("mongodb://", "mongodb+srv://")):
            raise ValueError("Invalid MongoDB URL format")
        return v
    
    @field_validator("REDIS_URL")
    def validate_redis_url(cls, v):
        if not v.startswith("redis://"):
            raise ValueError("Invalid Redis URL format")
        return v
    
    @field_validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {valid_levels}")
        return v.upper()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


# Create settings instance
settings = Settings()

# Ensure required directories exist
os.makedirs("/tmp/metadata-extraction", exist_ok=True)