"""
Configuration settings for the Proxy Generation Service
"""

from pydantic_settings import BaseSettings
from typing import Optional, List
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Service Information
    service_name: str = "proxy-generation-service"
    service_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = True
    service_port: int = 8008
    
    # Database
    database_url: str = "postgresql+asyncpg://mams:dev_password@postgres:5432/mams_proxy"
    redis_url: str = "redis://redis:6379/0"
    
    # Message Queue
    rabbitmq_url: str = "amqp://mams:dev_password@rabbitmq:5672/"
    proxy_queue_name: str = "proxy_generation_queue"
    max_concurrent_jobs: int = 4
    
    # Storage
    storage_backend: str = "s3"
    s3_endpoint: str = "http://minio:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_name: str = "mams-proxies"
    s3_region: str = "us-east-1"
    
    # Local storage fallback
    local_storage_path: str = "/app/storage/proxies"
    
    # FFmpeg Configuration
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"
    ffmpeg_threads: int = 0  # 0 = auto-detect
    enable_gpu_acceleration: bool = False
    gpu_device: Optional[str] = None
    
    # Proxy Presets
    proxy_formats: List[str] = ["mp4", "webm"]
    default_video_codec: str = "libx264"
    default_audio_codec: str = "aac"
    
    # Video Quality Presets
    video_presets: dict = {
        "low": {
            "width": 640,
            "height": 360,
            "video_bitrate": "500k",
            "audio_bitrate": "64k",
            "framerate": 25,
            "preset": "fast",
            "gpu_preset": "p4",  # NVIDIA preset
            "max_bitrate": "750k",
            "buffer_size": "1M"
        },
        "medium": {
            "width": 1280,
            "height": 720,
            "video_bitrate": "1500k",
            "audio_bitrate": "128k",
            "framerate": 25,
            "preset": "fast",
            "gpu_preset": "p4",
            "max_bitrate": "2250k",
            "buffer_size": "3M"
        },
        "high": {
            "width": 1920,
            "height": 1080,
            "video_bitrate": "3000k",
            "audio_bitrate": "192k",
            "framerate": 25,
            "preset": "fast",
            "gpu_preset": "p5",
            "max_bitrate": "4500k",
            "buffer_size": "6M"
        },
        "edit": {
            "width": None,  # Keep original
            "height": None,
            "video_codec": "prores",
            "video_bitrate": "40000k",
            "audio_bitrate": "320k",
            "framerate": None,  # Keep original
            "preset": "fast",
            "gpu_preset": "p7",  # Highest quality for edit
            "max_bitrate": "60000k",
            "buffer_size": "80M"
        }
    }
    
    # Image Processing
    thumbnail_sizes: List[dict] = [
        {"name": "small", "width": 320, "height": 180},
        {"name": "medium", "width": 640, "height": 360},
        {"name": "large", "width": 1280, "height": 720}
    ]
    thumbnail_format: str = "jpg"
    thumbnail_quality: int = 85
    contact_sheet_columns: int = 4
    contact_sheet_rows: int = 4
    
    # Audio Processing
    waveform_width: int = 1920
    waveform_height: int = 256
    waveform_colors: dict = {
        "background": "#ffffff",
        "waveform": "#0066cc",
        "axis": "#333333"
    }
    
    # Processing Limits
    max_file_size: int = 50 * 1024 * 1024 * 1024  # 50GB
    processing_timeout: int = 3600  # 1 hour
    max_retries: int = 3
    retry_delay: int = 60  # seconds
    
    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090
    
    # JWT Settings (for API authentication)
    jwt_secret_key: str = "your-secret-key-here"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60
    
    class Config:
        env_prefix = "PROXY_"
        case_sensitive = False
        
        # Load from .env file if exists
        env_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            ".env"
        )


# Create settings instance
settings = Settings()