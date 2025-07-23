"""
Database base configuration for Asset Management Service

This module provides the base SQLAlchemy configuration and session management.
"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeMeta
from typing import AsyncGenerator
import logging

from ..core.config import get_settings

logger = logging.getLogger(__name__)

# Create declarative base
Base: DeclarativeMeta = declarative_base()

# Database engine and session factory (initialized on startup)
engine = None
async_session_factory = None


async def init_db():
    """Initialize database connection"""
    global engine, async_session_factory
    
    settings = get_settings()
    
    # Create async engine
    engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,
        pool_recycle=3600,  # Recycle connections after 1 hour
    )
    
    # Create session factory
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    logger.info("Database connection initialized")


async def close_db():
    """Close database connection"""
    global engine
    
    if engine:
        await engine.dispose()
        logger.info("Database connection closed")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session
    
    Yields:
        AsyncSession: Database session
    """
    if not async_session_factory:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_tables():
    """Create all database tables"""
    if not engine:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables created")


async def drop_tables():
    """Drop all database tables (use with caution!)"""
    if not engine:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    logger.warning("All database tables dropped!")