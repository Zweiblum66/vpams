"""
Configuration settings for the Search Engine Service
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    # Service configuration
    service_name: str = Field(default="search-engine", env="SERVICE_NAME")
    service_port: int = Field(default=8006, env="SERVICE_PORT")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # OpenSearch configuration
    opensearch_host: str = Field(default="localhost", env="OPENSEARCH_HOST")
    opensearch_port: int = Field(default=9200, env="OPENSEARCH_PORT")
    opensearch_scheme: str = Field(default="http", env="OPENSEARCH_SCHEME")
    opensearch_username: Optional[str] = Field(default=None, env="OPENSEARCH_USERNAME")
    opensearch_password: Optional[str] = Field(default=None, env="OPENSEARCH_PASSWORD")
    opensearch_ssl_verify: bool = Field(default=False, env="OPENSEARCH_SSL_VERIFY")
    opensearch_ssl_cert_path: Optional[str] = Field(default=None, env="OPENSEARCH_SSL_CERT_PATH")
    opensearch_timeout: int = Field(default=30, env="OPENSEARCH_TIMEOUT")
    opensearch_max_retries: int = Field(default=3, env="OPENSEARCH_MAX_RETRIES")
    
    # Index configuration
    assets_index_name: str = Field(default="mams_assets", env="ASSETS_INDEX_NAME")
    metadata_index_name: str = Field(default="mams_metadata", env="METADATA_INDEX_NAME")
    content_index_name: str = Field(default="mams_content", env="CONTENT_INDEX_NAME")
    logs_index_name: str = Field(default="mams_search_logs", env="LOGS_INDEX_NAME")
    
    # Search configuration
    default_search_size: int = Field(default=20, env="DEFAULT_SEARCH_SIZE")
    max_search_size: int = Field(default=1000, env="MAX_SEARCH_SIZE")
    search_timeout: int = Field(default=30, env="SEARCH_TIMEOUT")
    enable_search_suggestions: bool = Field(default=True, env="ENABLE_SEARCH_SUGGESTIONS")
    enable_search_analytics: bool = Field(default=True, env="ENABLE_SEARCH_ANALYTICS")
    
    # Feature flags
    enable_semantic_search: bool = Field(default=False, env="ENABLE_SEMANTIC_SEARCH")
    enable_ml_ranking: bool = Field(default=False, env="ENABLE_ML_RANKING")
    enable_auto_complete: bool = Field(default=True, env="ENABLE_AUTO_COMPLETE")
    enable_ai_search: bool = Field(default=True, env="ENABLE_AI_SEARCH")
    enable_personalization: bool = Field(default=False, env="ENABLE_PERSONALIZATION")
    
    # AI Search configuration
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    semantic_model_name: str = Field(default="all-MiniLM-L6-v2", env="SEMANTIC_MODEL_NAME")
    embedding_dimension: int = Field(default=384, env="EMBEDDING_DIMENSION")
    ai_search_timeout: int = Field(default=60, env="AI_SEARCH_TIMEOUT")
    max_query_enhancement_length: int = Field(default=500, env="MAX_QUERY_ENHANCEMENT_LENGTH")
    embedding_cache_size: int = Field(default=10000, env="EMBEDDING_CACHE_SIZE")
    
    # Redis configuration for AI search caching
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_ttl: int = Field(default=3600, env="REDIS_TTL")
    
    # OpenSearch index for AI features
    opensearch_index: str = Field(default="mams_assets", env="OPENSEARCH_INDEX")
    opensearch_user: Optional[str] = Field(default=None, env="OPENSEARCH_USER")
    
    # AI Search scoring weights
    semantic_weight: float = Field(default=0.4, env="SEMANTIC_WEIGHT")
    fulltext_weight: float = Field(default=0.3, env="FULLTEXT_WEIGHT")
    entity_weight: float = Field(default=0.2, env="ENTITY_WEIGHT")
    temporal_weight: float = Field(default=0.1, env="TEMPORAL_WEIGHT")
    
    # Performance settings
    bulk_index_size: int = Field(default=100, env="BULK_INDEX_SIZE")
    refresh_interval: str = Field(default="1s", env="REFRESH_INTERVAL")
    number_of_shards: int = Field(default=1, env="NUMBER_OF_SHARDS")
    number_of_replicas: int = Field(default=0, env="NUMBER_OF_REPLICAS")
    
    # Security
    api_key_header: str = Field(default="X-API-Key", env="API_KEY_HEADER")
    allowed_origins: List[str] = Field(default=["*"], env="ALLOWED_ORIGINS")
    
    # Monitoring
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    
    # MongoDB configuration
    mongodb_url: str = Field(default="mongodb://localhost:27017", env="MONGODB_URL")
    mongodb_database_name: str = Field(default="mams_search", env="MONGODB_DATABASE_NAME")
    mongodb_max_pool_size: int = Field(default=10, env="MONGODB_MAX_POOL_SIZE")
    mongodb_min_pool_size: int = Field(default=1, env="MONGODB_MIN_POOL_SIZE")
    
    @property
    def opensearch_url(self) -> str:
        """Construct OpenSearch URL"""
        return f"{self.opensearch_scheme}://{self.opensearch_host}:{self.opensearch_port}"
    
    @property
    def opensearch_auth(self) -> Optional[tuple]:
        """Get OpenSearch authentication tuple"""
        if self.opensearch_username and self.opensearch_password:
            return (self.opensearch_username, self.opensearch_password)
        return None

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()