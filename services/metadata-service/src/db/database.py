"""
Database connection and setup for MongoDB
"""

import asyncio
from typing import AsyncGenerator
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import structlog

from ..core.config import settings
from .models import INDEXES

logger = structlog.get_logger()

# Global database client
_client: AsyncIOMotorClient = None
_database: AsyncIOMotorDatabase = None


async def init_db():
    """Initialize database connection and create indexes"""
    global _client, _database
    
    try:
        # Create MongoDB client
        _client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
            minPoolSize=settings.MONGODB_MIN_POOL_SIZE
        )
        
        # Get database
        _database = _client[settings.MONGODB_DATABASE]
        
        # Test connection
        await _client.admin.command('ping')
        logger.info("MongoDB connection established")
        
        # Create indexes
        await _create_indexes()
        
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise


async def close_db():
    """Close database connection"""
    global _client
    
    if _client:
        _client.close()
        logger.info("MongoDB connection closed")


async def get_database() -> AsyncIOMotorDatabase:
    """Get database instance"""
    global _database
    
    if _database is None:
        await init_db()
    
    return _database


async def _create_indexes():
    """Create database indexes"""
    global _database
    
    if not _database:
        return
    
    try:
        for collection_name, index_spec, options in INDEXES:
            collection = _database[collection_name]
            
            # Create index
            await collection.create_index(
                index_spec,
                **options
            )
            
            logger.debug(
                "Index created",
                collection=collection_name,
                index=index_spec,
                options=options
            )
        
        logger.info("All database indexes created successfully")
        
    except Exception as e:
        logger.error("Failed to create indexes", error=str(e))
        raise


async def health_check() -> bool:
    """Check database health"""
    global _client
    
    try:
        if not _client:
            return False
        
        # Ping the database
        await _client.admin.command('ping')
        return True
        
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return False


async def get_collection_stats() -> dict:
    """Get database collection statistics"""
    global _database
    
    if not _database:
        return {}
    
    try:
        stats = {}
        
        # Get list of collections
        collections = await _database.list_collection_names()
        
        for collection_name in collections:
            collection = _database[collection_name]
            
            # Get collection stats
            collection_stats = await _database.command("collStats", collection_name)
            
            stats[collection_name] = {
                "count": collection_stats.get("count", 0),
                "size": collection_stats.get("size", 0),
                "avgObjSize": collection_stats.get("avgObjSize", 0),
                "storageSize": collection_stats.get("storageSize", 0),
                "indexes": collection_stats.get("nindexes", 0),
                "totalIndexSize": collection_stats.get("totalIndexSize", 0)
            }
        
        return stats
        
    except Exception as e:
        logger.error("Failed to get collection stats", error=str(e))
        return {}


# Database dependency for FastAPI
async def get_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """FastAPI dependency for database connection"""
    db = await get_database()
    try:
        yield db
    finally:
        # Connection cleanup is handled by the connection pool
        pass