"""
Database base configuration and session management

This module provides the base database setup, session management,
and connection utilities for the User Management Service.
"""

import asyncio
from typing import AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool
import logging

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class Base(DeclarativeBase):
    """Base class for all database models"""
    pass


# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=20,
    max_overflow=30,
    connect_args={
        "server_settings": {
            "application_name": "mams_user_management",
            "jit": "off"
        }
    }
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database session
    
    Usage:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            # Use db session
            pass
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        # Import all models to ensure they're registered
        from . import models
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")


async def close_db():
    """Close database connections"""
    await engine.dispose()
    logger.info("Database connections closed")


# Health check function
async def check_db_health() -> bool:
    """Check database connectivity"""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False