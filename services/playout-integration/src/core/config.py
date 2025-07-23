"""Configuration settings for Playout Integration Service"""

from typing import Optional, Dict, Any, List
from pydantic_settings import BaseSettings
from pydantic import Field, validator
import os


class Settings(BaseSettings):
    """Service configuration settings"""
    
    # Service info
    service_name: str = Field(default="playout-integration", description="Service name")
    service_version: str = Field(default="1.0.0", description="Service version")
    service_port: int = Field(default=8013, description="Service port")
    
    # Environment
    environment: str = Field(default="development", description="Environment name")
    debug: bool = Field(default=False, description="Debug mode")
    
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/playout",
        description="PostgreSQL connection URL"
    )
    database_pool_size: int = Field(default=20, description="Database connection pool size")
    database_max_overflow: int = Field(default=10, description="Maximum overflow connections")
    
    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/2",
        description="Redis connection URL"
    )
    redis_pool_size: int = Field(default=10, description="Redis connection pool size")
    
    # Default Playout Configuration
    default_playout_system: str = Field(default="generic", description="Default playout system type")
    default_playout_protocol: str = Field(default="vdcp", description="Default control protocol")
    playout_config_file: str = Field(
        default="config/playout_systems.yaml",
        description="Playout systems configuration file"
    )
    
    # File Transfer Settings
    transfer_max_concurrent: int = Field(default=5, description="Maximum concurrent transfers")
    transfer_chunk_size: int = Field(default=10485760, description="Transfer chunk size in bytes")
    transfer_timeout_seconds: int = Field(default=3600, description="Transfer timeout in seconds")
    transfer_retry_count: int = Field(default=3, description="Number of retry attempts")
    transfer_retry_delay: int = Field(default=60, description="Delay between retries in seconds")
    
    # Schedule Settings
    schedule_lookahead_days: int = Field(default=7, description="Days to look ahead for scheduling")
    schedule_validation_enabled: bool = Field(default=True, description="Enable schedule validation")
    schedule_auto_gap_fill: bool = Field(default=True, description="Automatically fill schedule gaps")
    schedule_timezone: str = Field(default="UTC", description="Schedule timezone")
    schedule_default_duration: int = Field(default=30, description="Default item duration in seconds")
    
    # Content Preparation
    content_validation_enabled: bool = Field(default=True, description="Enable content validation")
    content_normalize_audio: bool = Field(default=True, description="Normalize audio levels")
    content_target_loudness: float = Field(default=-23.0, description="Target loudness in LUFS")
    content_max_true_peak: float = Field(default=-1.0, description="Maximum true peak in dBFS")
    content_default_video_codec: str = Field(default="h264", description="Default video codec")
    content_default_audio_codec: str = Field(default="aac", description="Default audio codec")
    
    # Monitoring
    monitor_interval_seconds: int = Field(default=30, description="Monitoring interval in seconds")
    monitor_timeout_seconds: int = Field(default=10, description="Monitor timeout in seconds")
    asrun_retention_days: int = Field(default=90, description="As-run log retention in days")
    metrics_enabled: bool = Field(default=True, description="Enable metrics collection")
    alert_enabled: bool = Field(default=True, description="Enable alerting")
    
    # Device Control
    device_control_timeout: int = Field(default=30, description="Device control timeout in seconds")
    device_heartbeat_interval: int = Field(default=60, description="Device heartbeat interval")
    device_reconnect_delay: int = Field(default=5, description="Device reconnection delay in seconds")
    device_max_reconnect_attempts: int = Field(default=10, description="Maximum reconnection attempts")
    
    # Storage Paths
    temp_storage_path: str = Field(default="/tmp/playout-temp", description="Temporary storage path")
    content_storage_path: str = Field(default="/media/playout", description="Content storage path")
    log_storage_path: str = Field(default="/var/log/playout", description="Log storage path")
    
    # Security
    jwt_secret_key: str = Field(default="your-secret-key-here", description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_minutes: int = Field(default=60, description="JWT expiration in minutes")
    
    api_key_header: str = Field(default="X-API-Key", description="API key header name")
    cors_origins: List[str] = Field(default=["*"], description="CORS allowed origins")
    
    # External Systems
    traffic_system_enabled: bool = Field(default=False, description="Enable traffic system integration")
    traffic_system_url: Optional[str] = Field(default=None, description="Traffic system URL")
    traffic_system_api_key: Optional[str] = Field(default=None, description="Traffic system API key")
    
    automation_system_enabled: bool = Field(default=False, description="Enable automation integration")
    automation_system_url: Optional[str] = Field(default=None, description="Automation system URL")
    automation_system_api_key: Optional[str] = Field(default=None, description="Automation API key")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json or text)")
    log_file: Optional[str] = Field(default=None, description="Log file path")
    
    # Performance
    max_schedule_items: int = Field(default=10000, description="Maximum items in a schedule")
    max_transfer_queue_size: int = Field(default=1000, description="Maximum transfer queue size")
    cache_ttl: int = Field(default=300, description="Default cache TTL in seconds")
    
    # Feature Flags
    feature_redundancy: bool = Field(default=True, description="Enable redundancy features")
    feature_failover: bool = Field(default=True, description="Enable automatic failover")
    feature_qc: bool = Field(default=True, description="Enable quality control")
    feature_graphics_overlay: bool = Field(default=True, description="Enable graphics overlay")
    feature_live_events: bool = Field(default=True, description="Enable live event support")
    
    @validator("database_url")
    def validate_database_url(cls, v: str) -> str:
        """Ensure database URL uses async driver"""
        if "postgresql://" in v and "+asyncpg" not in v:
            return v.replace("postgresql://", "postgresql+asyncpg://")
        return v
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v: Any) -> List[str]:
        """Parse CORS origins from string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("temp_storage_path", "content_storage_path", "log_storage_path")
    def create_directories(cls, v: str) -> str:
        """Create directories if they don't exist"""
        os.makedirs(v, exist_ok=True)
        return v
    
    def get_playout_config(self) -> Dict[str, Any]:
        """Get playout system configuration"""
        return {
            "default_system": self.default_playout_system,
            "default_protocol": self.default_playout_protocol,
            "config_file": self.playout_config_file,
            "device_control": {
                "timeout": self.device_control_timeout,
                "heartbeat_interval": self.device_heartbeat_interval,
                "reconnect_delay": self.device_reconnect_delay,
                "max_reconnect_attempts": self.device_max_reconnect_attempts
            }
        }
    
    def get_transfer_config(self) -> Dict[str, Any]:
        """Get transfer configuration"""
        return {
            "max_concurrent": self.transfer_max_concurrent,
            "chunk_size": self.transfer_chunk_size,
            "timeout": self.transfer_timeout_seconds,
            "retry_count": self.transfer_retry_count,
            "retry_delay": self.transfer_retry_delay,
            "paths": {
                "temp": self.temp_storage_path,
                "content": self.content_storage_path
            }
        }
    
    def get_schedule_config(self) -> Dict[str, Any]:
        """Get schedule configuration"""
        return {
            "lookahead_days": self.schedule_lookahead_days,
            "validation_enabled": self.schedule_validation_enabled,
            "auto_gap_fill": self.schedule_auto_gap_fill,
            "timezone": self.schedule_timezone,
            "default_duration": self.schedule_default_duration,
            "max_items": self.max_schedule_items
        }
    
    def get_content_config(self) -> Dict[str, Any]:
        """Get content preparation configuration"""
        return {
            "validation_enabled": self.content_validation_enabled,
            "normalize_audio": self.content_normalize_audio,
            "audio": {
                "target_loudness": self.content_target_loudness,
                "max_true_peak": self.content_max_true_peak
            },
            "codecs": {
                "video": self.content_default_video_codec,
                "audio": self.content_default_audio_codec
            }
        }
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration"""
        return {
            "interval": self.monitor_interval_seconds,
            "timeout": self.monitor_timeout_seconds,
            "asrun_retention_days": self.asrun_retention_days,
            "metrics_enabled": self.metrics_enabled,
            "alert_enabled": self.alert_enabled
        }
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Create settings instance
settings = Settings()