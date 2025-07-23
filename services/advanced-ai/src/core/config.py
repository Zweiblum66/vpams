"""
Configuration for Advanced AI Service
"""

from typing import List, Dict, Optional, Any
from pydantic_settings import BaseSettings
from pydantic import Field, validator
import json


class Settings(BaseSettings):
    """Advanced AI service settings"""
    
    # Service Configuration
    SERVICE_NAME: str = "advanced-ai"
    SERVICE_PORT: int = 8019
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    # Database Configuration
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://user:pass@localhost:5432/mams_ai",
        description="Database connection URL"
    )
    
    # Redis Configuration
    REDIS_URL: str = Field(
        default="redis://localhost:6379/2",
        description="Redis connection URL"
    )
    
    # Model Configuration
    MODEL_CACHE_PATH: str = Field(
        default="/var/cache/models",
        description="Path to cache ML models"
    )
    MODEL_UPDATE_INTERVAL_HOURS: int = Field(
        default=24,
        description="How often to retrain models"
    )
    
    # Usage Prediction Configuration
    USAGE_PREDICTION_WINDOW_DAYS: int = Field(
        default=90,
        description="Historical data window for usage prediction"
    )
    USAGE_PREDICTION_HORIZON_DAYS: int = Field(
        default=30,
        description="How far ahead to predict usage"
    )
    USAGE_PREDICTION_MODELS: List[str] = Field(
        default=["prophet", "arima", "lstm", "xgboost"],
        description="Models to use for usage prediction"
    )
    
    # Storage Optimization Configuration
    STORAGE_OPTIMIZATION_ENABLED: bool = Field(
        default=True,
        description="Enable storage optimization AI"
    )
    STORAGE_TIER_THRESHOLDS: Dict[str, Dict[str, Any]] = Field(
        default={
            "hot": {"access_frequency": 10, "age_days": 7},
            "warm": {"access_frequency": 5, "age_days": 30},
            "cold": {"access_frequency": 1, "age_days": 90},
            "archive": {"access_frequency": 0, "age_days": 365}
        },
        description="Thresholds for storage tier recommendations"
    )
    
    # Content Recommendation Configuration
    RECOMMENDATION_ALGORITHM: str = Field(
        default="hybrid",
        description="Recommendation algorithm: collaborative, content, hybrid"
    )
    RECOMMENDATION_CACHE_TTL_SECONDS: int = Field(
        default=3600,
        description="How long to cache recommendations"
    )
    RECOMMENDATION_MAX_ITEMS: int = Field(
        default=50,
        description="Maximum recommendations to generate"
    )
    
    # Predictive Maintenance Configuration
    MAINTENANCE_PREDICTION_ENABLED: bool = Field(
        default=True,
        description="Enable predictive maintenance"
    )
    MAINTENANCE_ALERT_THRESHOLD_DAYS: int = Field(
        default=7,
        description="Alert when failure predicted within N days"
    )
    
    # Cost Optimization Configuration
    COST_OPTIMIZATION_ENABLED: bool = Field(
        default=True,
        description="Enable cost optimization AI"
    )
    COST_PER_GB_STORAGE: Dict[str, float] = Field(
        default={
            "hot": 0.023,
            "warm": 0.0125,
            "cold": 0.004,
            "archive": 0.00099
        },
        description="Storage cost per GB per month"
    )
    COST_PER_GB_TRANSFER: float = Field(
        default=0.09,
        description="Data transfer cost per GB"
    )
    
    # Video Summarization Configuration
    VIDEO_SUMMARIZATION_ENABLED: bool = Field(
        default=True,
        description="Enable video summarization"
    )
    VIDEO_SUMMARY_TARGET_LENGTH_PERCENT: int = Field(
        default=10,
        description="Target summary length as percentage of original"
    )
    ENABLE_TRANSCRIPTION: bool = Field(
        default=True,
        description="Enable audio transcription for video analysis"
    )
    ENABLE_TEXT_SUMMARIZATION: bool = Field(
        default=True,
        description="Enable text summarization of transcripts"
    )
    ENABLE_FACE_DETECTION: bool = Field(
        default=True,
        description="Enable face detection for importance scoring"
    )
    VIDEO_PROCESSING_MAX_RESOLUTION: str = Field(
        default="1920x1080",
        description="Maximum resolution for video processing"
    )
    SCENE_DETECTION_THRESHOLD: float = Field(
        default=30.0,
        description="Threshold for scene change detection"
    )
    
    # Auto-tagging Configuration
    AUTO_TAGGING_ENABLED: bool = Field(
        default=True,
        description="Enable improved auto-tagging"
    )
    AUTO_TAGGING_CONFIDENCE_THRESHOLD: float = Field(
        default=0.7,
        description="Minimum confidence for auto-tags"
    )
    MAX_AUTO_TAGS_PER_ASSET: int = Field(
        default=50,
        description="Maximum number of auto-tags per asset"
    )
    AUTO_TAGGING_CACHE_TTL: int = Field(
        default=3600,
        description="Auto-tagging cache TTL in seconds"
    )
    
    # Object Detection Configuration
    YOLO_MODEL_PATH: str = Field(
        default="yolov8n.pt",
        description="YOLO model file path"
    )
    OBJECT_DETECTION_CONFIDENCE: float = Field(
        default=0.6,
        description="Object detection confidence threshold"
    )
    
    # OCR Configuration
    OCR_LANGUAGES: List[str] = Field(
        default=["en", "es", "fr", "de"],
        description="OCR supported languages"
    )
    OCR_CONFIDENCE_THRESHOLD: float = Field(
        default=0.5,
        description="OCR confidence threshold"
    )
    
    # Content Moderation Configuration
    CONTENT_MODERATION_ENABLED: bool = Field(
        default=True,
        description="Enable content moderation"
    )
    MODERATION_CONFIDENCE_THRESHOLD: float = Field(
        default=0.8,
        description="Content moderation flagging threshold"
    )
    
    # Scene Classification Configuration
    SCENE_CLASSIFICATION_MODEL: str = Field(
        default="google/vit-base-patch16-224",
        description="Scene classification model"
    )
    SCENE_CLASSIFICATION_TOP_K: int = Field(
        default=5,
        description="Number of top scene predictions to return"
    )
    
    # Content Clustering Configuration
    CLUSTERING_ALGORITHM: str = Field(
        default="dbscan",
        description="Clustering algorithm: kmeans, dbscan, hierarchical"
    )
    CLUSTERING_UPDATE_INTERVAL_HOURS: int = Field(
        default=6,
        description="How often to update clusters"
    )
    
    # AI Search Configuration
    AI_SEARCH_ENABLED: bool = Field(
        default=True,
        description="Enable AI-powered search"
    )
    SEMANTIC_SEARCH_MODEL: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Model for semantic search"
    )
    
    # Training Configuration
    TRAINING_BATCH_SIZE: int = Field(default=32, description="Batch size for training")
    TRAINING_EPOCHS: int = Field(default=10, description="Number of training epochs")
    TRAINING_LEARNING_RATE: float = Field(default=0.001, description="Learning rate")
    
    # Performance Configuration
    MAX_CONCURRENT_PREDICTIONS: int = Field(
        default=10,
        description="Maximum concurrent prediction tasks"
    )
    PREDICTION_TIMEOUT_SECONDS: int = Field(
        default=300,
        description="Timeout for prediction tasks"
    )
    
    # Monitoring Configuration
    ENABLE_METRICS: bool = Field(default=True, description="Enable metrics collection")
    METRICS_INTERVAL_SECONDS: int = Field(default=60, description="Metrics collection interval")
    
    # API Configuration
    API_KEY_HEADER: str = Field(default="X-API-Key", description="API key header name")
    SECRET_KEY: str = Field(default="dev-secret-key", description="Secret key for security")
    
    @validator("USAGE_PREDICTION_MODELS", "STORAGE_TIER_THRESHOLDS", pre=True)
    def parse_json_fields(cls, v):
        """Parse JSON fields from string if needed"""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return v
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()