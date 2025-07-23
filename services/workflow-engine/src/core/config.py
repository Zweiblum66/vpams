"""
Configuration settings for Workflow Engine Service
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    # Service Info
    SERVICE_NAME: str = "workflow-engine"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    PORT: int = 8088
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://mams:mams@postgres:5432/workflow_engine"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    # MongoDB for workflow definitions
    MONGODB_URL: str = "mongodb://mongo:27017/workflow_engine"
    MONGODB_DATABASE: str = "workflow_engine"
    
    # Redis for workflow state and queues
    REDIS_URL: str = "redis://redis:6379/0"
    REDIS_STATE_PREFIX: str = "workflow:state:"
    REDIS_QUEUE_PREFIX: str = "workflow:queue:"
    REDIS_LOCK_PREFIX: str = "workflow:lock:"
    
    # RabbitMQ for task distribution
    RABBITMQ_URL: str = "amqp://mams:mams@rabbitmq:5672/"
    WORKFLOW_EXCHANGE: str = "workflow_events"
    TASK_QUEUE: str = "workflow_tasks"
    
    # Security
    JWT_SECRET_KEY: str = "your-secret-key-here"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # Workflow Engine Settings
    MAX_WORKFLOW_RETRIES: int = 3
    DEFAULT_WORKFLOW_TIMEOUT: int = 3600  # 1 hour
    TASK_EXECUTION_TIMEOUT: int = 300  # 5 minutes
    WORKFLOW_HISTORY_RETENTION_DAYS: int = 90
    MAX_CONCURRENT_WORKFLOWS: int = 100
    MAX_WORKFLOW_DEPTH: int = 10  # Maximum nesting level
    
    # Task Queue Settings
    TASK_QUEUE_MAX_SIZE: int = 10000
    TASK_RETRY_DELAY: int = 60  # seconds
    TASK_MAX_RETRIES: int = 3
    
    # Workflow Templates
    TEMPLATE_DIRECTORY: str = "/app/templates"
    CUSTOM_TEMPLATE_DIRECTORY: str = "/app/custom_templates"
    
    # Integration Settings
    ASSET_SERVICE_URL: str = "http://asset-management:8003"
    METADATA_SERVICE_URL: str = "http://metadata-service:8005"
    PROXY_SERVICE_URL: str = "http://proxy-generation:8007"
    NOTIFICATION_SERVICE_URL: str = "http://notification-service:8010"
    
    # Monitoring
    ENABLE_METRICS: bool = True
    METRICS_PREFIX: str = "mams_workflow_"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()