"""Startup utilities for health checks"""

import asyncio
from pathlib import Path
import redis.asyncio as aioredis
from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import aiosmtplib
import logging

from ..core.config import settings

logger = logging.getLogger(__name__)


async def check_database_connection() -> bool:
    """Check PostgreSQL database connection"""
    try:
        engine = create_async_engine(settings.database_url)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {str(e)}")
        return False


async def check_mongodb_connection() -> bool:
    """Check MongoDB connection"""
    try:
        client = AsyncIOMotorClient(settings.mongodb_url)
        await client.admin.command('ping')
        client.close()
        return True
    except Exception as e:
        logger.error(f"MongoDB connection check failed: {str(e)}")
        return False


async def check_redis_connection() -> bool:
    """Check Redis connection"""
    try:
        redis = aioredis.from_url(settings.redis_url)
        await redis.ping()
        await redis.close()
        return True
    except Exception as e:
        logger.error(f"Redis connection check failed: {str(e)}")
        return False


async def check_storage_access() -> bool:
    """Check storage directory access"""
    try:
        storage_path = Path(settings.export_storage_path)
        storage_path.mkdir(parents=True, exist_ok=True)
        
        # Test write access
        test_file = storage_path / ".health_check"
        test_file.write_text("test")
        test_file.unlink()
        
        return True
    except Exception as e:
        logger.error(f"Storage access check failed: {str(e)}")
        return False


async def check_email_service() -> bool:
    """Check email service connectivity"""
    if not settings.email_enabled:
        return True
    
    try:
        smtp = aiosmtplib.SMTP(
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            use_tls=settings.smtp_tls
        )
        
        await smtp.connect()
        await smtp.quit()
        return True
    except Exception as e:
        logger.error(f"Email service check failed: {str(e)}")
        return False