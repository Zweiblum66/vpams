"""
Database connection and session management
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
import structlog

from ..core.config import get_settings

logger = structlog.get_logger()

# Global variables
engine = None
SessionLocal = None


def init_database():
    """Initialize database connection"""
    global engine, SessionLocal
    
    settings = get_settings()
    
    # Create async engine
    engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
        poolclass=NullPool,  # Use NullPool for async
        future=True
    )
    
    # Create session factory
    SessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    logger.info("Database initialized", url=settings.database_url.split("@")[-1])


async def get_db() -> AsyncSession:
    """Get database session"""
    if SessionLocal is None:
        init_database()
    
    async with SessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error("Database session error", error=str(e))
            raise
        finally:
            await session.close()


async def create_tables():
    """Create database tables"""
    from ..models.database import Base
    
    if engine is None:
        init_database()
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables created")


async def drop_tables():
    """Drop database tables"""
    from ..models.database import Base
    
    if engine is None:
        init_database()
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    logger.info("Database tables dropped")


async def close_database():
    """Close database connections"""
    global engine
    
    if engine:
        await engine.dispose()
        logger.info("Database connections closed")