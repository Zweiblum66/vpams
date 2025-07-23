"""
Dependencies for Advanced AI Service
"""

from typing import AsyncGenerator, Optional
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from aioredis import Redis
import httpx

from .config import settings
from ..db.base import AsyncSessionLocal
from ..services.usage_predictor import UsagePredictor
from ..services.storage_optimizer import StorageOptimizer
from ..services.recommendation_engine import RecommendationEngine
from ..services.maintenance_predictor import MaintenancePredictor
from ..services.video_summarizer import VideoSummarizer


# Database dependency
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session"""
    async with AsyncSessionLocal() as session:
        yield session


# Redis dependency
_redis_client: Optional[Redis] = None


async def get_redis() -> Redis:
    """Get Redis client"""
    global _redis_client
    if _redis_client is None:
        from aioredis import from_url
        _redis_client = await from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


# Service dependencies
_usage_predictor: Optional[UsagePredictor] = None


async def get_usage_predictor(
    db: AsyncSession = Depends(get_db)
) -> UsagePredictor:
    """Get usage predictor instance"""
    global _usage_predictor
    if _usage_predictor is None:
        _usage_predictor = UsagePredictor(db=db)
        await _usage_predictor.initialize()
    return _usage_predictor


_storage_optimizer: Optional[StorageOptimizer] = None


async def get_storage_optimizer(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
) -> StorageOptimizer:
    """Get storage optimizer instance"""
    global _storage_optimizer
    if _storage_optimizer is None:
        _storage_optimizer = StorageOptimizer(db=db, redis=redis)
        await _storage_optimizer.initialize()
    return _storage_optimizer


_recommendation_engine: Optional[RecommendationEngine] = None


async def get_recommendation_engine(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
) -> RecommendationEngine:
    """Get recommendation engine instance"""
    global _recommendation_engine
    if _recommendation_engine is None:
        _recommendation_engine = RecommendationEngine(db=db, redis=redis)
        await _recommendation_engine.initialize()
    return _recommendation_engine


_maintenance_predictor: Optional[MaintenancePredictor] = None


async def get_maintenance_predictor(
    db: AsyncSession = Depends(get_db)
) -> MaintenancePredictor:
    """Get maintenance predictor instance"""
    global _maintenance_predictor
    if _maintenance_predictor is None:
        _maintenance_predictor = MaintenancePredictor(db=db)
        await _maintenance_predictor.initialize()
    return _maintenance_predictor


_video_summarizer: Optional[VideoSummarizer] = None


async def get_video_summarizer(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
) -> VideoSummarizer:
    """Get video summarizer instance"""
    global _video_summarizer
    if _video_summarizer is None:
        _video_summarizer = VideoSummarizer(db=db, redis=redis)
        await _video_summarizer.initialize()
    return _video_summarizer


# API Key authentication
async def verify_api_key(
    api_key: Optional[str] = Header(None, alias=settings.API_KEY_HEADER)
) -> bool:
    """Verify API key"""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    
    # In production, verify against stored API keys
    # For now, just check if it's provided
    return True


# User authentication (placeholder)
class User:
    """Placeholder user class"""
    def __init__(self, id: str, username: str):
        self.id = id
        self.username = username


async def get_current_user() -> User:
    """Get current authenticated user"""
    # In production, implement proper JWT authentication
    # For now, return a dummy user
    return User(id="ai-user", username="ai-operator")


# HTTP client for external services
_http_client: Optional[httpx.AsyncClient] = None


async def get_http_client() -> httpx.AsyncClient:
    """Get HTTP client for external API calls"""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=100)
        )
    return _http_client


# Cleanup function
async def cleanup_dependencies():
    """Cleanup all dependencies"""
    global _redis_client, _usage_predictor, _storage_optimizer
    global _recommendation_engine, _maintenance_predictor, _video_summarizer, _http_client
    
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
    
    if _http_client:
        await _http_client.aclose()
        _http_client = None
    
    # Services don't need explicit cleanup but reset them
    _usage_predictor = None
    _storage_optimizer = None
    _recommendation_engine = None
    _maintenance_predictor = None
    _video_summarizer = None