"""Configuration settings for MOS Integration Service"""

from typing import List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """MOS Integration Service configuration"""
    
    # Service Configuration
    service_name: str = "mos-integration"
    service_version: str = "1.0.0"
    debug: bool = False
    
    # Database Configuration
    database_url: str = Field(..., env="DATABASE_URL")
    redis_url: str = Field(..., env="REDIS_URL")
    
    # MOS Protocol Configuration
    mos_server_id: str = Field("mos01.mams.local", env="MOS_SERVER_ID")
    mos_listen_port: int = Field(10540, env="MOS_LISTEN_PORT")
    mos_upper_port: int = Field(10541, env="MOS_UPPER_PORT")
    mos_query_port: int = Field(10542, env="MOS_QUERY_PORT")
    mos_heartbeat_interval: int = Field(30, env="MOS_HEARTBEAT_INTERVAL")
    mos_timeout: int = Field(60, env="MOS_TIMEOUT")
    
    # NRCS (Newsroom Computer System) Configuration
    allowed_nrcs_systems: List[str] = Field(
        default_factory=lambda: ["ENPS", "ROSS", "AVID", "OCTOPUS"],
        env="ALLOWED_NRCS_SYSTEMS"
    )
    
    # Security Configuration
    mos_authentication_enabled: bool = Field(True, env="MOS_AUTH_ENABLED")
    mos_shared_secret: Optional[str] = Field(None, env="MOS_SHARED_SECRET")
    
    # Logging Configuration
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_format: str = "json"
    
    # Monitoring Configuration
    metrics_enabled: bool = True
    health_check_interval: int = 30
    
    # Message Processing Configuration
    max_concurrent_messages: int = Field(100, env="MOS_MAX_CONCURRENT_MESSAGES")
    message_timeout: int = Field(30, env="MOS_MESSAGE_TIMEOUT")
    retry_attempts: int = Field(3, env="MOS_RETRY_ATTEMPTS")
    
    # File Storage Configuration
    temp_storage_path: str = Field("/tmp/mos", env="MOS_TEMP_STORAGE")
    max_file_size_mb: int = Field(500, env="MOS_MAX_FILE_SIZE_MB")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @validator("mos_listen_port", "mos_upper_port", "mos_query_port")
    def validate_ports(cls, v):
        if not 1024 <= v <= 65535:
            raise ValueError("Port must be between 1024 and 65535")
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()
    
    @validator("mos_heartbeat_interval", "mos_timeout")
    def validate_timeouts(cls, v):
        if v <= 0:
            raise ValueError("Timeout values must be positive")
        return v


# Global settings instance
settings = Settings()