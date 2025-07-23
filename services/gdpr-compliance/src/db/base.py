"""Database configuration for GDPR Compliance Service"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from sqlalchemy import text
import motor.motor_asyncio
import logging

from ..core.config import settings

logger = logging.getLogger(__name__)

# Create async engine for PostgreSQL
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_recycle=300,
    poolclass=NullPool if settings.debug else None
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Create declarative base
Base = declarative_base()

# MongoDB client
mongo_client = motor.motor_asyncio.AsyncIOMotorClient(settings.mongodb_url)
mongo_db = mongo_client.mams
gdpr_collection = mongo_db.gdpr_compliance


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session (alias for get_db)"""
    async for session in get_db():
        yield session


async def get_mongo_db():
    """Get MongoDB database instance"""
    return mongo_db


async def init_db():
    """Initialize database - create tables"""
    try:
        async with engine.begin() as conn:
            # Import all models to ensure they're registered
            from . import models
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise


async def create_tables():
    """Create database tables (alias for init_db)"""
    await init_db()


async def drop_tables():
    """Drop database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def check_db_connection() -> bool:
    """Check database connection"""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {str(e)}")
        return False