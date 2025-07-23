"""Database configuration and connection management"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from ..core.config import settings

# Create async engine
engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Base class for models
Base = declarative_base()

async def init_db():
    """Initialize database"""
    async with engine.begin() as conn:
        # Create tables (in production, use Alembic migrations)
        await conn.run_sync(Base.metadata.create_all)

async def close_db():
    """Close database connections"""
    await engine.dispose()

async def get_db() -> AsyncSession:
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()