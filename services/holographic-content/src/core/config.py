"""Configuration for Holographic Content Service"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Service configuration"""
    
    # Service settings
    SERVICE_NAME: str = "holographic-content"
    SERVICE_PORT: int = 8023
    DEBUG: bool = Field(default=False, env="DEBUG")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/holographic_content",
        env="DATABASE_URL"
    )
    
    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL"
    )
    
    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="CORS_ORIGINS"
    )
    
    # Security
    JWT_SECRET_KEY: str = Field(
        default="your-secret-key-here",
        env="JWT_SECRET_KEY"
    )
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_EXPIRATION_MINUTES: int = Field(default=60, env="JWT_EXPIRATION_MINUTES")
    
    # Holographic capture devices
    AZURE_KINECT_ENABLED: bool = Field(default=True, env="AZURE_KINECT_ENABLED")
    INTEL_REALSENSE_ENABLED: bool = Field(default=True, env="INTEL_REALSENSE_ENABLED")
    DEPTHKIT_ENABLED: bool = Field(default=False, env="DEPTHKIT_ENABLED")
    EVERCOAST_URL: Optional[str] = Field(default=None, env="EVERCOAST_URL")
    SCATTER_SDK_KEY: Optional[str] = Field(default=None, env="SCATTER_SDK_KEY")
    
    # Light field displays
    LOOKING_GLASS_ENABLED: bool = Field(default=True, env="LOOKING_GLASS_ENABLED")
    LOOKING_GLASS_SDK_PATH: Optional[str] = Field(default=None, env="LOOKING_GLASS_SDK_PATH")
    LEIA_SDK_ENABLED: bool = Field(default=False, env="LEIA_SDK_ENABLED")
    HOLOXICA_ENABLED: bool = Field(default=False, env="HOLOXICA_ENABLED")
    
    # Holographic projectors
    MICROSOFT_HOLOLENS_ENABLED: bool = Field(default=True, env="MICROSOFT_HOLOLENS_ENABLED")
    MAGIC_LEAP_ENABLED: bool = Field(default=True, env="MAGIC_LEAP_ENABLED")
    REALFICTION_DREAMOC_ENABLED: bool = Field(default=False, env="REALFICTION_DREAMOC_ENABLED")
    MDH_HOLOGRAM_ENABLED: bool = Field(default=False, env="MDH_HOLOGRAM_ENABLED")
    
    # Neural processing
    NVIDIA_INSTANT_NGP_ENABLED: bool = Field(default=True, env="NVIDIA_INSTANT_NGP_ENABLED")
    NEURAL_RADIANCE_FIELDS: bool = Field(default=True, env="NEURAL_RADIANCE_FIELDS")
    GAUSSIAN_SPLATTING_ENABLED: bool = Field(default=True, env="GAUSSIAN_SPLATTING_ENABLED")
    
    # Processing settings
    MAX_POINT_CLOUD_SIZE: int = Field(default=100_000_000, env="MAX_POINT_CLOUD_SIZE")  # 100M points
    MAX_VOXEL_RESOLUTION: int = Field(default=1024, env="MAX_VOXEL_RESOLUTION")
    MAX_MESH_VERTICES: int = Field(default=10_000_000, env="MAX_MESH_VERTICES")
    GPU_ACCELERATION: bool = Field(default=True, env="GPU_ACCELERATION")
    CUDA_DEVICE_ID: int = Field(default=0, env="CUDA_DEVICE_ID")
    
    # Storage
    HOLOGRAM_STORAGE_PATH: str = Field(default="/storage/holograms", env="HOLOGRAM_STORAGE_PATH")
    TEMP_PROCESSING_PATH: str = Field(default="/tmp/hologram_processing", env="TEMP_PROCESSING_PATH")
    S3_BUCKET_NAME: Optional[str] = Field(default=None, env="S3_BUCKET_NAME")
    
    # Streaming
    WEBRTC_ENABLED: bool = Field(default=True, env="WEBRTC_ENABLED")
    PIXEL_STREAMING_URL: Optional[str] = Field(default=None, env="PIXEL_STREAMING_URL")
    LOW_LATENCY_MODE: bool = Field(default=True, env="LOW_LATENCY_MODE")
    MAX_STREAMING_BITRATE: int = Field(default=50_000_000, env="MAX_STREAMING_BITRATE")  # 50 Mbps
    
    # AI/ML models
    DEPTH_ESTIMATION_MODEL: str = Field(default="midas_v3", env="DEPTH_ESTIMATION_MODEL")
    SEGMENTATION_MODEL: str = Field(default="mask2former", env="SEGMENTATION_MODEL")
    SUPER_RESOLUTION_MODEL: str = Field(default="real_esrgan", env="SUPER_RESOLUTION_MODEL")
    
    # External services
    AI_SERVICE_URL: str = Field(default="http://ai-ml-service:8003", env="AI_SERVICE_URL")
    ASSET_SERVICE_URL: str = Field(default="http://asset-management:8001", env="ASSET_SERVICE_URL")
    STORAGE_SERVICE_URL: str = Field(default="http://storage-abstraction:8002", env="STORAGE_SERVICE_URL")
    
    # Feature flags
    ENABLE_VOLUMETRIC_CAPTURE: bool = Field(default=True, env="ENABLE_VOLUMETRIC_CAPTURE")
    ENABLE_LIGHT_FIELD_DISPLAY: bool = Field(default=True, env="ENABLE_LIGHT_FIELD_DISPLAY")
    ENABLE_HOLOGRAPHIC_PROJECTION: bool = Field(default=True, env="ENABLE_HOLOGRAPHIC_PROJECTION")
    ENABLE_NEURAL_RENDERING: bool = Field(default=True, env="ENABLE_NEURAL_RENDERING")
    ENABLE_REAL_TIME_STREAMING: bool = Field(default=True, env="ENABLE_REAL_TIME_STREAMING")
    ENABLE_HAPTIC_FEEDBACK: bool = Field(default=False, env="ENABLE_HAPTIC_FEEDBACK")
    
    # Performance settings
    MAX_CONCURRENT_CAPTURES: int = Field(default=3, env="MAX_CONCURRENT_CAPTURES")
    MAX_CONCURRENT_RENDERS: int = Field(default=5, env="MAX_CONCURRENT_RENDERS")
    PROCESSING_QUEUE_SIZE: int = Field(default=100, env="PROCESSING_QUEUE_SIZE")
    CACHE_TTL_SECONDS: int = Field(default=3600, env="CACHE_TTL_SECONDS")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()