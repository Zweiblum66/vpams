"""
Configuration for CDN service
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Settings for CDN service"""
    
    # Service configuration
    SERVICE_NAME: str = "cdn"
    SERVICE_VERSION: str = "1.0.0"
    SERVICE_PORT: int = 8016
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Redis configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # AWS configuration
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    
    # CloudFront configuration
    ENABLE_CLOUDFRONT: bool = True
    CLOUDFRONT_DISTRIBUTION_ID: Optional[str] = None
    CLOUDFRONT_OAI: Optional[str] = None  # Origin Access Identity
    ACM_CERTIFICATE_ARN: Optional[str] = None
    WAF_WEB_ACL_ID: Optional[str] = None
    KINESIS_ROLE_ARN: Optional[str] = None
    
    # Cloudflare configuration
    ENABLE_CLOUDFLARE: bool = False
    CLOUDFLARE_ZONE_ID: Optional[str] = None
    CLOUDFLARE_API_TOKEN: Optional[str] = None
    
    # Akamai configuration
    ENABLE_AKAMAI: bool = False
    AKAMAI_HOST: Optional[str] = None
    AKAMAI_CLIENT_TOKEN: Optional[str] = None
    AKAMAI_CLIENT_SECRET: Optional[str] = None
    AKAMAI_ACCESS_TOKEN: Optional[str] = None
    
    # Fastly configuration
    ENABLE_FASTLY: bool = False
    FASTLY_API_KEY: Optional[str] = None
    FASTLY_SERVICE_ID: Optional[str] = None
    
    # Azure CDN configuration
    ENABLE_AZURE_CDN: bool = False
    AZURE_SUBSCRIPTION_ID: Optional[str] = None
    AZURE_RESOURCE_GROUP: Optional[str] = None
    AZURE_CDN_PROFILE: Optional[str] = None
    
    # Default CDN settings
    DEFAULT_CACHE_TTL: int = 86400  # 24 hours
    DEFAULT_MAX_TTL: int = 31536000  # 1 year
    DEFAULT_MIN_TTL: int = 0
    
    # Cache settings
    CACHE_STATIC_CONTENT: bool = True
    CACHE_DYNAMIC_CONTENT: bool = False
    CACHE_API_RESPONSES: bool = False
    
    # Optimization settings
    ENABLE_IMAGE_OPTIMIZATION: bool = True
    ENABLE_VIDEO_OPTIMIZATION: bool = True
    ENABLE_COMPRESSION: bool = True
    ENABLE_MINIFICATION: bool = True
    
    # Image optimization defaults
    IMAGE_QUALITY: int = 85
    IMAGE_MAX_WIDTH: int = 4096
    IMAGE_MAX_HEIGHT: int = 4096
    IMAGE_AUTO_WEBP: bool = True
    IMAGE_AUTO_AVIF: bool = False
    IMAGE_RESPONSIVE_SIZES: List[int] = [320, 640, 1024, 1920]
    
    # Video optimization defaults
    VIDEO_ADAPTIVE_BITRATE: bool = True
    VIDEO_OUTPUT_FORMATS: List[str] = ["mp4", "webm"]
    VIDEO_QUALITY_LEVELS: List[str] = ["360p", "720p", "1080p", "1440p", "2160p"]
    VIDEO_MAX_BITRATE_MBPS: float = 10.0
    
    # Security settings
    ENABLE_WAF: bool = True
    ENABLE_DDOS_PROTECTION: bool = True
    ENABLE_HOTLINK_PROTECTION: bool = True
    ALLOWED_REFERERS: List[str] = []
    BLOCKED_IPS: List[str] = []
    BLOCKED_COUNTRIES: List[str] = []
    
    # Performance settings
    CONNECTION_TIMEOUT: int = 10
    READ_TIMEOUT: int = 30
    MAX_RETRIES: int = 3
    RETRY_DELAY_SECONDS: int = 1
    
    # Monitoring
    ENABLE_REAL_TIME_LOGS: bool = True
    ENABLE_ACCESS_LOGS: bool = True
    LOG_SAMPLING_RATE: float = 1.0  # 100% sampling
    
    # Cost optimization
    ENABLE_SMART_CACHING: bool = True
    ENABLE_BANDWIDTH_THROTTLING: bool = False
    BANDWIDTH_LIMIT_MBPS: Optional[float] = None
    
    # Prefetch settings
    ENABLE_PREFETCH: bool = True
    PREFETCH_CONCURRENT_REQUESTS: int = 10
    PREFETCH_TIMEOUT_SECONDS: int = 30
    
    # Purge settings
    PURGE_BATCH_SIZE: int = 100
    PURGE_RATE_LIMIT_PER_MINUTE: int = 100
    
    # Authentication
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # Metrics
    PROMETHEUS_ENABLED: bool = True
    PROMETHEUS_PORT: int = 9090
    
    # Database URL (for tracking/analytics)
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/mams_cdn"
    
    # Feature flags
    ENABLE_EDGE_COMPUTING: bool = False
    ENABLE_SERVERLESS_FUNCTIONS: bool = False
    ENABLE_AI_OPTIMIZATION: bool = False
    ENABLE_BLOCKCHAIN_VERIFICATION: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()