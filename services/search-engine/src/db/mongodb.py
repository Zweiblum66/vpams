"""
MongoDB connection management
"""

from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import structlog
from ..core.config import get_settings

logger = structlog.get_logger()

# Global MongoDB client
_mongodb_client: Optional[AsyncIOMotorClient] = None
_mongodb_database: Optional[AsyncIOMotorDatabase] = None


async def get_mongodb_client() -> AsyncIOMotorClient:
    """Get MongoDB client instance"""
    global _mongodb_client
    
    if _mongodb_client is None:
        settings = get_settings()
        _mongodb_client = AsyncIOMotorClient(
            settings.mongodb_url,
            maxPoolSize=settings.mongodb_max_pool_size,
            minPoolSize=settings.mongodb_min_pool_size
        )
        logger.info("mongodb_client_created", url=settings.mongodb_url)
    
    return _mongodb_client


async def get_mongodb() -> AsyncIOMotorDatabase:
    """Get MongoDB database instance"""
    global _mongodb_database
    
    if _mongodb_database is None:
        client = await get_mongodb_client()
        settings = get_settings()
        _mongodb_database = client[settings.mongodb_database_name]
        logger.info("mongodb_database_connected", database=settings.mongodb_database_name)
    
    return _mongodb_database


async def close_mongodb():
    """Close MongoDB connection"""
    global _mongodb_client, _mongodb_database
    
    if _mongodb_client:
        _mongodb_client.close()
        _mongodb_client = None
        _mongodb_database = None
        logger.info("mongodb_connection_closed")