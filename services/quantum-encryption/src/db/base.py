from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import logging
from typing import AsyncGenerator

from ..core.config import settings

logger = logging.getLogger(__name__)

# Create base class for models
Base = declarative_base()

# Create async engine
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    poolclass=NullPool,  # Use NullPool for better connection handling
    future=True
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db() -> None:
    """Initialize database."""
    try:
        async with engine.begin() as conn:
            # Import all models to ensure they're registered
            from ..models import quantum_key  # noqa
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
    logger.info("Database connections closed")