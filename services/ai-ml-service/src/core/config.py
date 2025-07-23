"""
AI/ML Service Configuration

This module contains configuration settings for the AI/ML service.
"""

from typing import List, Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings."""
    
    # Service configuration
    SERVICE_NAME: str = "ai-ml-service"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    PORT: int = 8006
    
    # Database configuration
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://mams:password@localhost:5432/mams_aiml",
        env="DATABASE_URL"
    )
    MONGODB_URL: str = Field(
        default="mongodb://localhost:27017/mams_aiml",
        env="MONGODB_URL"
    )
    REDIS_URL: str = Field(
        default="redis://localhost:6379/6",
        env="REDIS_URL"
    )
    
    # Model storage configuration
    MODEL_STORAGE_PATH: str = Field(
        default="/app/models",
        env="MODEL_STORAGE_PATH"
    )
    MODEL_CACHE_SIZE: int = Field(
        default=5,
        env="MODEL_CACHE_SIZE",
        description="Maximum number of models to keep in memory"
    )
    
    # ML Model configurations
    OBJECT_DETECTION_MODEL: str = Field(
        default="yolov8n",
        env="OBJECT_DETECTION_MODEL"
    )
    FACE_DETECTION_MODEL: str = Field(
        default="mtcnn",
        env="FACE_DETECTION_MODEL"
    )
    SCENE_DETECTION_MODEL: str = Field(
        default="mobilenetv2",
        env="SCENE_DETECTION_MODEL"
    )
    
    # Speech-to-text configuration
    STT_MODEL: str = Field(
        default="openai/whisper-base",
        env="STT_MODEL"
    )
    STT_DEVICE: str = Field(
        default="cpu",
        env="STT_DEVICE",
        description="Device to use for STT (cpu, cuda, mps)"
    )
    
    # Content moderation configuration
    CONTENT_MODERATION_MODEL: str = Field(
        default="unitary/toxic-bert",
        env="CONTENT_MODERATION_MODEL"
    )
    
    # External API keys
    OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        env="OPENAI_API_KEY"
    )
    AZURE_COGNITIVE_KEY: Optional[str] = Field(
        default=None,
        env="AZURE_COGNITIVE_KEY"
    )
    AZURE_COGNITIVE_ENDPOINT: Optional[str] = Field(
        default=None,
        env="AZURE_COGNITIVE_ENDPOINT"
    )
    GOOGLE_CLOUD_KEY: Optional[str] = Field(
        default=None,
        env="GOOGLE_CLOUD_KEY"
    )
    
    # Generative AI API keys
    ANTHROPIC_API_KEY: Optional[str] = Field(
        default=None,
        env="ANTHROPIC_API_KEY"
    )
    STABILITY_API_KEY: Optional[str] = Field(
        default=None,
        env="STABILITY_API_KEY"
    )
    REPLICATE_API_TOKEN: Optional[str] = Field(
        default=None,
        env="REPLICATE_API_TOKEN"
    )
    HUGGINGFACE_API_TOKEN: Optional[str] = Field(
        default=None,
        env="HUGGINGFACE_API_TOKEN"
    )
    
    # Processing configuration
    MAX_CONCURRENT_REQUESTS: int = Field(
        default=10,
        env="MAX_CONCURRENT_REQUESTS"
    )
    REQUEST_TIMEOUT: int = Field(
        default=300,
        env="REQUEST_TIMEOUT",
        description="Request timeout in seconds"
    )
    
    # Image processing configuration
    MAX_IMAGE_SIZE: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        env="MAX_IMAGE_SIZE"
    )
    MAX_VIDEO_SIZE: int = Field(
        default=1024 * 1024 * 1024,  # 1GB
        env="MAX_VIDEO_SIZE"
    )
    MAX_AUDIO_SIZE: int = Field(
        default=100 * 1024 * 1024,  # 100MB
        env="MAX_AUDIO_SIZE"
    )
    
    # Batch processing configuration
    BATCH_SIZE: int = Field(
        default=32,
        env="BATCH_SIZE"
    )
    BATCH_TIMEOUT: int = Field(
        default=30,
        env="BATCH_TIMEOUT",
        description="Batch timeout in seconds"
    )
    
    # Queue configuration
    QUEUE_URL: str = Field(
        default="redis://localhost:6379/7",
        env="QUEUE_URL"
    )
    QUEUE_MAX_RETRIES: int = Field(
        default=3,
        env="QUEUE_MAX_RETRIES"
    )
    
    # Caching configuration
    CACHE_TTL: int = Field(
        default=3600,
        env="CACHE_TTL",
        description="Cache TTL in seconds"
    )
    
    # Security configuration
    SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production",
        env="SECRET_KEY"
    )
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="ALLOWED_ORIGINS"
    )
    
    # Logging configuration
    LOG_LEVEL: str = Field(
        default="INFO",
        env="LOG_LEVEL"
    )
    
    # Feature flags
    ENABLE_OBJECT_DETECTION: bool = Field(
        default=True,
        env="ENABLE_OBJECT_DETECTION"
    )
    ENABLE_FACE_DETECTION: bool = Field(
        default=True,
        env="ENABLE_FACE_DETECTION"
    )
    ENABLE_SCENE_DETECTION: bool = Field(
        default=True,
        env="ENABLE_SCENE_DETECTION"
    )
    ENABLE_CONTENT_MODERATION: bool = Field(
        default=True,
        env="ENABLE_CONTENT_MODERATION"
    )
    ENABLE_SPEECH_TO_TEXT: bool = Field(
        default=True,
        env="ENABLE_SPEECH_TO_TEXT"
    )
    ENABLE_SENTIMENT_ANALYSIS: bool = Field(
        default=True,
        env="ENABLE_SENTIMENT_ANALYSIS"
    )
    ENABLE_ENTITY_RECOGNITION: bool = Field(
        default=True,
        env="ENABLE_ENTITY_RECOGNITION"
    )
    ENABLE_LANGUAGE_DETECTION: bool = Field(
        default=True,
        env="ENABLE_LANGUAGE_DETECTION"
    )
    ENABLE_SPEAKER_DIARIZATION: bool = Field(
        default=True,
        env="ENABLE_SPEAKER_DIARIZATION"
    )
    ENABLE_KEYWORD_EXTRACTION: bool = Field(
        default=True,
        env="ENABLE_KEYWORD_EXTRACTION"
    )
    
    # Generative AI configuration
    ENABLE_GENERATIVE_AI: bool = Field(
        default=True,
        env="ENABLE_GENERATIVE_AI"
    )
    DEFAULT_TEXT_PROVIDER: str = Field(
        default="openai",
        env="DEFAULT_TEXT_PROVIDER"
    )
    DEFAULT_IMAGE_PROVIDER: str = Field(
        default="openai",
        env="DEFAULT_IMAGE_PROVIDER"
    )
    DEFAULT_VIDEO_PROVIDER: str = Field(
        default="replicate",
        env="DEFAULT_VIDEO_PROVIDER"
    )
    DEFAULT_AUDIO_PROVIDER: str = Field(
        default="openai",
        env="DEFAULT_AUDIO_PROVIDER"
    )
    ENABLE_LOCAL_MODELS: bool = Field(
        default=False,
        env="ENABLE_LOCAL_MODELS"
    )
    GENERATIVE_MODEL_CACHE_PATH: str = Field(
        default="/app/generative_models",
        env="GENERATIVE_MODEL_CACHE_PATH"
    )
    MAX_GENERATION_TOKENS: int = Field(
        default=4000,
        env="MAX_GENERATION_TOKENS"
    )
    GENERATION_TIMEOUT: int = Field(
        default=600,
        env="GENERATION_TIMEOUT"
    )
    
    # Performance monitoring
    ENABLE_METRICS: bool = Field(
        default=True,
        env="ENABLE_METRICS"
    )
    METRICS_PORT: int = Field(
        default=8007,
        env="METRICS_PORT"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()