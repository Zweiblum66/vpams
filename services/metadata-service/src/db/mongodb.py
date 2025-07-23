"""
MongoDB connection and database setup for Metadata Service
"""

import motor.motor_asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import logging
from typing import Optional

from src.core.config import settings

logger = logging.getLogger(__name__)

# Global MongoDB client and database
mongodb_client: Optional[AsyncIOMotorClient] = None
mongodb_database: Optional[AsyncIOMotorDatabase] = None


async def init_db():
    """
    Initialize MongoDB connection and create indexes
    """
    global mongodb_client, mongodb_database
    
    try:
        # Create MongoDB client
        mongodb_client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
            minPoolSize=settings.MONGODB_MIN_POOL_SIZE,
            serverSelectionTimeoutMS=5000
        )
        
        # Get database
        mongodb_database = mongodb_client[settings.MONGODB_DATABASE]
        
        # Verify connection
        await mongodb_client.server_info()
        logger.info(f"Connected to MongoDB at {settings.MONGODB_URL}")
        
        # Create indexes
        await create_indexes()
        
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise


async def close_db():
    """
    Close MongoDB connection
    """
    global mongodb_client
    
    if mongodb_client:
        mongodb_client.close()
        logger.info("MongoDB connection closed")


async def get_database() -> AsyncIOMotorDatabase:
    """
    Get MongoDB database instance
    """
    if not mongodb_database:
        await init_db()
    return mongodb_database


async def create_indexes():
    """
    Create MongoDB indexes for better performance
    """
    try:
        # Metadata schemas collection indexes
        schemas_collection = mongodb_database["metadata_schemas"]
        await schemas_collection.create_index("name", unique=True)
        await schemas_collection.create_index("asset_types")
        await schemas_collection.create_index("is_active")
        await schemas_collection.create_index([("created_at", -1)])
        
        # Metadata collection indexes
        metadata_collection = mongodb_database["metadata"]
        await metadata_collection.create_index("asset_id")
        await metadata_collection.create_index("schema_id")
        await metadata_collection.create_index([("asset_id", 1), ("schema_id", 1)])
        await metadata_collection.create_index([("updated_at", -1)])
        
        # Create text index for searchable fields
        await metadata_collection.create_index([("$**", "text")])
        
        # Technical metadata collection indexes
        tech_metadata_collection = mongodb_database["technical_metadata"]
        await tech_metadata_collection.create_index("asset_id", unique=True)
        await tech_metadata_collection.create_index("format")
        await tech_metadata_collection.create_index("mime_type")
        
        # Extraction tasks collection indexes
        extraction_tasks = mongodb_database["extraction_tasks"]
        await extraction_tasks.create_index("task_id", unique=True)
        await extraction_tasks.create_index("asset_id")
        await extraction_tasks.create_index("status")
        await extraction_tasks.create_index([("created_at", -1)])
        
        logger.info("MongoDB indexes created successfully")
        
    except Exception as e:
        logger.error(f"Failed to create indexes: {e}")
        raise


# Collection helpers
async def get_collection(collection_name: str):
    """
    Get a MongoDB collection
    """
    db = await get_database()
    return db[collection_name]