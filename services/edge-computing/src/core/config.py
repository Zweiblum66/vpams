"""
Configuration for Edge Computing Service
"""

from typing import List, Dict, Optional, Any
from pydantic_settings import BaseSettings
from pydantic import Field, validator
import json


class Settings(BaseSettings):
    """Edge computing service settings"""
    
    # Service Configuration
    SERVICE_NAME: str = "edge-computing"
    SERVICE_PORT: int = 8018
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    # Edge Node Configuration
    NODE_ID: str = Field(default="edge-node-001", description="Unique identifier for this edge node")
    NODE_LOCATION: str = Field(default="us-west-2", description="Geographic location of this edge node")
    NODE_TYPE: str = Field(default="standard", description="Node type: standard, gpu, specialized")
    NODE_CAPABILITIES: List[str] = Field(
        default=["transcode", "thumbnail", "analyze", "cache"],
        description="Processing capabilities of this node"
    )
    
    # Cluster Configuration
    MASTER_NODE_URL: Optional[str] = Field(
        default="http://edge-master:8018",
        description="URL of the master edge node for coordination"
    )
    IS_MASTER_NODE: bool = Field(default=False, description="Whether this is a master coordination node")
    EDGE_NODES: List[Dict[str, Any]] = Field(
        default=[],
        description="List of edge nodes in the cluster"
    )
    
    # Processing Configuration
    MAX_CONCURRENT_JOBS: int = Field(default=10, description="Maximum concurrent processing jobs")
    JOB_TIMEOUT_SECONDS: int = Field(default=3600, description="Job timeout in seconds")
    ENABLE_GPU_PROCESSING: bool = Field(default=False, description="Enable GPU acceleration")
    GPU_DEVICE_ID: int = Field(default=0, description="GPU device ID to use")
    
    # Task Types Configuration
    SUPPORTED_TASKS: List[str] = Field(
        default=[
            "video_transcode",
            "image_resize",
            "thumbnail_generation",
            "face_detection",
            "object_detection",
            "scene_analysis",
            "audio_processing",
            "metadata_extraction",
            "content_analysis"
        ],
        description="Supported processing tasks"
    )
    
    # Cache Configuration
    ENABLE_LOCAL_CACHE: bool = Field(default=True, description="Enable local edge cache")
    CACHE_SIZE_GB: int = Field(default=100, description="Local cache size in GB")
    CACHE_EVICTION_POLICY: str = Field(default="lru", description="Cache eviction policy")
    CACHE_PATH: str = Field(default="/var/cache/edge", description="Local cache directory")
    
    # Network Configuration
    BANDWIDTH_LIMIT_MBPS: Optional[int] = Field(default=None, description="Bandwidth limit in Mbps")
    ENABLE_P2P_TRANSFER: bool = Field(default=True, description="Enable P2P transfers between edge nodes")
    P2P_PORT_RANGE: str = Field(default="30000-31000", description="Port range for P2P transfers")
    
    # Media Processing Configuration
    VIDEO_CODEC: str = Field(default="h264", description="Default video codec")
    AUDIO_CODEC: str = Field(default="aac", description="Default audio codec")
    ENABLE_HARDWARE_ACCELERATION: bool = Field(default=True, description="Enable hardware acceleration")
    
    # Quality Presets
    TRANSCODE_PRESETS: Dict[str, Dict[str, Any]] = Field(
        default={
            "low": {"resolution": "640x360", "bitrate": "800k", "fps": 25},
            "medium": {"resolution": "1280x720", "bitrate": "2500k", "fps": 25},
            "high": {"resolution": "1920x1080", "bitrate": "5000k", "fps": 25},
            "4k": {"resolution": "3840x2160", "bitrate": "15000k", "fps": 25}
        },
        description="Video transcode quality presets"
    )
    
    # AI/ML Configuration
    ENABLE_AI_PROCESSING: bool = Field(default=True, description="Enable AI/ML processing")
    MODEL_CACHE_PATH: str = Field(default="/var/cache/models", description="AI model cache path")
    FACE_DETECTION_MODEL: str = Field(default="mtcnn", description="Face detection model")
    OBJECT_DETECTION_MODEL: str = Field(default="yolov5", description="Object detection model")
    
    # Monitoring Configuration
    ENABLE_METRICS: bool = Field(default=True, description="Enable metrics collection")
    METRICS_INTERVAL_SECONDS: int = Field(default=60, description="Metrics collection interval")
    HEALTH_CHECK_INTERVAL_SECONDS: int = Field(default=30, description="Health check interval")
    
    # Database Configuration
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://user:pass@localhost:5432/mams_edge",
        description="Database connection URL"
    )
    
    # Redis Configuration
    REDIS_URL: str = Field(
        default="redis://localhost:6379/1",
        description="Redis connection URL"
    )
    
    # Storage Configuration
    STORAGE_TYPE: str = Field(default="s3", description="Storage backend type")
    S3_ENDPOINT: str = Field(default="http://minio:9000", description="S3 endpoint URL")
    S3_ACCESS_KEY: str = Field(default="minioadmin", description="S3 access key")
    S3_SECRET_KEY: str = Field(default="minioadmin", description="S3 secret key")
    S3_BUCKET: str = Field(default="mams-edge", description="S3 bucket for edge storage")
    
    # Security Configuration
    SECRET_KEY: str = Field(default="dev-secret-key", description="Secret key for security")
    API_KEY_HEADER: str = Field(default="X-API-Key", description="API key header name")
    ENABLE_TLS: bool = Field(default=False, description="Enable TLS for edge communication")
    TLS_CERT_PATH: Optional[str] = Field(default=None, description="TLS certificate path")
    TLS_KEY_PATH: Optional[str] = Field(default=None, description="TLS key path")
    
    @validator("EDGE_NODES", pre=True)
    def parse_edge_nodes(cls, v):
        """Parse edge nodes from string if needed"""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return v
    
    @validator("NODE_CAPABILITIES", "SUPPORTED_TASKS", pre=True)
    def parse_list_fields(cls, v):
        """Parse list fields from string if needed"""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()