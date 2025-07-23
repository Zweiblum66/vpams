"""Database configuration and session management"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from contextlib import asynccontextmanager
import structlog

from .config import get_settings

logger = structlog.get_logger()

# Create base class for models
Base = declarative_base()

# Global engine and session factory
engine = None
async_session_factory = None


async def init_db():
    """Initialize database connection"""
    global engine, async_session_factory
    
    settings = get_settings()
    
    engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
    )
    
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("database_initialized")


async def get_db() -> AsyncSession:
    """Get database session"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context():
    """Get database session as context manager"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()