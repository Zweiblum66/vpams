"""
Configuration settings for the Ingest Service
"""

from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List, Optional, Dict, Any
import os


class IngestServiceSettings(BaseSettings):
    """Ingest Service configuration settings"""
    
    # Service Info
    service_name: str = "ingest-service"
    service_version: str = "1.0.0"
    service_port: int = Field(default=8002, env="SERVICE_PORT")
    
    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    
    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    mongodb_url: str = Field(..., env="MONGODB_URL")
    redis_url: str = Field(..., env="REDIS_URL")
    
    # Message Queue (RabbitMQ)
    rabbitmq_url: str = Field(..., env="RABBITMQ_URL")
    rabbitmq_exchange: str = Field(default="mams.ingest", env="RABBITMQ_EXCHANGE")
    rabbitmq_queue_prefix: str = Field(default="ingest", env="RABBITMQ_QUEUE_PREFIX")
    
    # Storage Configuration
    storage_service_url: str = Field(..., env="STORAGE_SERVICE_URL")
    storage_service_api_key: str = Field(..., env="STORAGE_SERVICE_API_KEY")
    temp_storage_path: str = Field(default="/tmp/ingest", env="TEMP_STORAGE_PATH")
    max_file_size: int = Field(default=10737418240, env="MAX_FILE_SIZE")  # 10GB
    
    # Watch Folders
    watch_folders: List[str] = Field(default_factory=list, env="WATCH_FOLDERS")
    hot_folders: List[str] = Field(default_factory=list, env="HOT_FOLDERS")
    
    # Processing Settings
    max_concurrent_ingests: int = Field(default=5, env="MAX_CONCURRENT_INGESTS")
    chunk_size: int = Field(default=8192, env="CHUNK_SIZE")  # 8KB chunks
    worker_pool_size: int = Field(default=4, env="WORKER_POOL_SIZE")
    
    # File Validation
    allowed_video_formats: List[str] = Field(
        default=[
            "mp4", "mov", "avi", "mkv", "mxf", "prores", "dnxhd", "dnxhr",
            "r3d", "braw", "arri", "dng", "dpx", "exr", "tiff", "tif"
        ],
        env="ALLOWED_VIDEO_FORMATS"
    )
    allowed_audio_formats: List[str] = Field(
        default=[
            "wav", "aiff", "flac", "mp3", "aac", "ogg", "m4a", "wma"
        ],
        env="ALLOWED_AUDIO_FORMATS"
    )
    allowed_image_formats: List[str] = Field(
        default=[
            "jpg", "jpeg", "png", "tiff", "tif", "bmp", "gif", "webp",
            "raw", "cr2", "nef", "arw", "dng", "raf", "orf", "rw2"
        ],
        env="ALLOWED_IMAGE_FORMATS"
    )
    allowed_document_formats: List[str] = Field(
        default=[
            "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt",
            "rtf", "odt", "ods", "odp"
        ],
        env="ALLOWED_DOCUMENT_FORMATS"
    )
    
    # Camera Card Support
    supported_camera_cards: List[str] = Field(
        default=["p2", "xdcam", "sxs", "cfexpress", "sdxc", "microsd"],
        env="SUPPORTED_CAMERA_CARDS"
    )
    
    # Virus Scanning
    enable_virus_scanning: bool = Field(default=True, env="ENABLE_VIRUS_SCANNING")
    clamav_host: str = Field(default="localhost", env="CLAMAV_HOST")
    clamav_port: int = Field(default=3310, env="CLAMAV_PORT")
    
    # Metadata Extraction
    extract_technical_metadata: bool = Field(default=True, env="EXTRACT_TECHNICAL_METADATA")
    extract_embedded_metadata: bool = Field(default=True, env="EXTRACT_EMBEDDED_METADATA")
    preserve_original_metadata: bool = Field(default=True, env="PRESERVE_ORIGINAL_METADATA")
    
    # Checksum Verification
    enable_checksum_verification: bool = Field(default=True, env="ENABLE_CHECKSUM_VERIFICATION")
    checksum_algorithms: List[str] = Field(
        default=["md5", "sha1", "sha256"],
        env="CHECKSUM_ALGORITHMS"
    )
    
    # Live Ingest
    enable_live_ingest: bool = Field(default=False, env="ENABLE_LIVE_INGEST")
    growing_file_timeout: int = Field(default=300, env="GROWING_FILE_TIMEOUT")  # 5 minutes
    growing_file_check_interval: int = Field(default=10, env="GROWING_FILE_CHECK_INTERVAL")  # 10 seconds
    
    # Proxy Generation
    auto_generate_proxies: bool = Field(default=True, env="AUTO_GENERATE_PROXIES")
    proxy_service_url: str = Field(default="", env="PROXY_SERVICE_URL")
    
    # Scheduling
    enable_scheduled_ingest: bool = Field(default=False, env="ENABLE_SCHEDULED_INGEST")
    scheduler_interval: int = Field(default=60, env="SCHEDULER_INTERVAL")  # 1 minute
    
    # Notifications
    enable_notifications: bool = Field(default=True, env="ENABLE_NOTIFICATIONS")
    notification_topics: List[str] = Field(
        default=["ingest.started", "ingest.completed", "ingest.failed", "ingest.error"],
        env="NOTIFICATION_TOPICS"
    )
    
    # External Services
    asset_service_url: str = Field(..., env="ASSET_SERVICE_URL")
    metadata_service_url: str = Field(..., env="METADATA_SERVICE_URL")
    search_service_url: str = Field(..., env="SEARCH_SERVICE_URL")
    
    # Security
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    api_key_header: str = Field(default="X-API-Key", env="API_KEY_HEADER")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    enable_structured_logging: bool = Field(default=True, env="ENABLE_STRUCTURED_LOGGING")
    
    # Performance
    enable_performance_monitoring: bool = Field(default=True, env="ENABLE_PERFORMANCE_MONITORING")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    
    @validator("watch_folders", "hot_folders", pre=True)
    def parse_folder_list(cls, v):
        if isinstance(v, str):
            return [folder.strip() for folder in v.split(",") if folder.strip()]
        return v or []
    
    @validator("allowed_video_formats", "allowed_audio_formats", "allowed_image_formats", 
              "allowed_document_formats", "supported_camera_cards", "checksum_algorithms",
              "notification_topics", pre=True)
    def parse_string_list(cls, v):
        if isinstance(v, str):
            return [item.strip().lower() for item in v.split(",") if item.strip()]
        return [item.lower() for item in v] if v else []
    
    @validator("temp_storage_path")
    def validate_temp_path(cls, v):
        # Ensure the temp path exists
        os.makedirs(v, exist_ok=True)
        return v
    
    @property
    def all_allowed_formats(self) -> List[str]:
        """Get all allowed file formats"""
        return (
            self.allowed_video_formats +
            self.allowed_audio_formats +
            self.allowed_image_formats +
            self.allowed_document_formats
        )
    
    @property
    def rabbitmq_queues(self) -> Dict[str, str]:
        """Get RabbitMQ queue names"""
        return {
            "ingest": f"{self.rabbitmq_queue_prefix}.ingest",
            "validation": f"{self.rabbitmq_queue_prefix}.validation",
            "processing": f"{self.rabbitmq_queue_prefix}.processing",
            "metadata": f"{self.rabbitmq_queue_prefix}.metadata",
            "notifications": f"{self.rabbitmq_queue_prefix}.notifications",
            "retry": f"{self.rabbitmq_queue_prefix}.retry",
            "dead_letter": f"{self.rabbitmq_queue_prefix}.dead_letter"
        }
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = IngestServiceSettings()