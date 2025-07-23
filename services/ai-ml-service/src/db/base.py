"""
Database configuration and initialization for AI/ML Service
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
import structlog

from ..core.config import settings

logger = structlog.get_logger(__name__)

# Create the declarative base
Base = declarative_base()
metadata = MetaData()

# Import all models to ensure they're registered
from .models import *
from .knowledge_base_models import *

# Database engine
engine = None
async_session_maker = None


async def init_db() -> None:
    """Initialize database connection and create tables."""
    global engine, async_session_maker
    
    logger.info("Initializing database connection", url=settings.DATABASE_URL.split("@")[1])
    
    try:
        # Create async engine
        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            future=True,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        
        # Create session maker
        async_session_maker = async_sessionmaker(
            engine, 
            class_=AsyncSession, 
            expire_on_commit=False
        )
        
        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session context manager."""
    if not async_session_maker:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async with get_db_session() as session:
        yield session


async def close_db() -> None:
    """Close database connection."""
    global engine
    if engine:
        await engine.dispose()
        logger.info("Database connection closed")