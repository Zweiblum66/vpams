"""
Dependencies for Edge Computing Service
"""

from typing import AsyncGenerator, Optional
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from aioredis import Redis
import httpx

from .config import settings
from ..db.base import AsyncSessionLocal
from ..services.edge_manager import EdgeManager
from ..services.task_processor import TaskProcessor
from ..services.cache_manager import CacheManager


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


# Edge Manager dependency
_edge_manager: Optional[EdgeManager] = None


async def get_edge_manager(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
) -> EdgeManager:
    """Get edge manager instance"""
    global _edge_manager
    if _edge_manager is None:
        _edge_manager = EdgeManager(db=db, redis=redis)
        await _edge_manager.initialize()
    return _edge_manager


# Task Processor dependency
_task_processor: Optional[TaskProcessor] = None


async def get_task_processor(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
) -> TaskProcessor:
    """Get task processor instance"""
    global _task_processor
    if _task_processor is None:
        _task_processor = TaskProcessor(db=db, redis=redis)
        await _task_processor.initialize()
    return _task_processor


# Cache Manager dependency
_cache_manager: Optional[CacheManager] = None


async def get_cache_manager(
    redis: Redis = Depends(get_redis)
) -> CacheManager:
    """Get cache manager instance"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager(redis=redis)
        await _cache_manager.initialize()
    return _cache_manager


# API Key authentication
async def verify_api_key(
    api_key: Optional[str] = Header(None, alias=settings.API_KEY_HEADER)
) -> bool:
    """Verify API key for edge node communication"""
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
    return User(id="edge-user", username="edge-operator")


# HTTP client for inter-node communication
_http_client: Optional[httpx.AsyncClient] = None


async def get_http_client() -> httpx.AsyncClient:
    """Get HTTP client for inter-node communication"""
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
    global _redis_client, _edge_manager, _task_processor, _cache_manager, _http_client
    
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
    
    if _edge_manager:
        await _edge_manager.shutdown()
        _edge_manager = None
    
    if _task_processor:
        await _task_processor.shutdown()
        _task_processor = None
    
    if _cache_manager:
        await _cache_manager.shutdown()
        _cache_manager = None
    
    if _http_client:
        await _http_client.aclose()
        _http_client = None