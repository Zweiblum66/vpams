"""
Redis Connection Management

Handles Redis connections for rate limiting, caching, and session management.
"""

import asyncio
import logging
from typing import Optional
import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool

from .config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Global Redis client
_redis_client: Optional[redis.Redis] = None
_connection_pool: Optional[ConnectionPool] = None


async def init_redis() -> None:
    """Initialize Redis connection"""
    global _redis_client, _connection_pool
    
    try:
        logger.info(f"Connecting to Redis at {settings.redis_url}")
        
        # Create connection pool
        _connection_pool = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=settings.redis_pool_size,
            retry_on_timeout=True,
            health_check_interval=30
        )
        
        # Create Redis client
        _redis_client = redis.Redis(
            connection_pool=_connection_pool,
            decode_responses=True
        )
        
        # Test connection
        await _redis_client.ping()
        logger.info("Redis connection established successfully")
        
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise


async def get_redis_client() -> redis.Redis:
    """Get Redis client"""
    global _redis_client
    
    if _redis_client is None:
        await init_redis()
    
    return _redis_client


async def close_redis() -> None:
    """Close Redis connection"""
    global _redis_client, _connection_pool
    
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
    
    if _connection_pool:
        await _connection_pool.disconnect()
        _connection_pool = None
    
    logger.info("Redis connection closed")


async def health_check() -> bool:
    """Check Redis health"""
    try:
        client = await get_redis_client()
        await client.ping()
        return True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return False


class RedisCache:
    """Redis cache utility class"""
    
    def __init__(self, client: redis.Redis):
        self.client = client
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        try:
            return await self.client.get(key)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    async def set(self, key: str, value: str, ttl: int = 3600) -> bool:
        """Set value in cache with TTL"""
        try:
            await self.client.set(key, value, ex=ttl)
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            return await self.client.exists(key)
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter"""
        try:
            return await self.client.incr(key, amount)
        except Exception as e:
            logger.error(f"Cache increment error: {e}")
            return 0
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL for key"""
        try:
            await self.client.expire(key, ttl)
            return True
        except Exception as e:
            logger.error(f"Cache expire error: {e}")
            return False


async def get_cache() -> RedisCache:
    """Get Redis cache instance"""
    client = await get_redis_client()
    return RedisCache(client)