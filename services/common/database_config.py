"""
Optimized database configuration for MAMS services.

This module provides database connection and session configuration
with performance optimizations.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy import event
import logging

logger = logging.getLogger(__name__)


class OptimizedDatabaseConfig:
    """Database configuration with performance optimizations."""
    
    def __init__(
        self,
        database_url: str,
        pool_size: int = 20,
        max_overflow: int = 40,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        echo: bool = False,
        echo_pool: bool = False,
        stateless: bool = False
    ):
        """
        Initialize optimized database configuration.
        
        Args:
            database_url: Database connection URL
            pool_size: Number of connections to maintain in pool
            max_overflow: Maximum overflow connections allowed
            pool_timeout: Timeout for getting connection from pool
            pool_recycle: Recycle connections after this many seconds
            echo: Whether to log SQL statements
            echo_pool: Whether to log pool checkouts/checkins
            stateless: Use NullPool for serverless environments
        """
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.echo = echo
        self.echo_pool = echo_pool
        self.stateless = stateless
        
        self._engine = None
        self._sessionmaker = None
        
    @property
    def engine(self):
        """Get or create the database engine."""
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine
        
    @property
    def sessionmaker(self) -> async_sessionmaker:
        """Get or create the session maker."""
        if self._sessionmaker is None:
            self._sessionmaker = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
                autocommit=False
            )
        return self._sessionmaker
        
    def _create_engine(self):
        """Create optimized async engine."""
        # Choose appropriate pool class
        if self.stateless:
            # Use NullPool for serverless/Lambda environments
            poolclass = NullPool
            pool_kwargs = {}
        else:
            # Use QueuePool for traditional deployments
            poolclass = QueuePool
            pool_kwargs = {
                'pool_size': self.pool_size,
                'max_overflow': self.max_overflow,
                'pool_timeout': self.pool_timeout,
                'pool_recycle': self.pool_recycle,
                'pool_pre_ping': True,  # Verify connections before use
            }
            
        engine = create_async_engine(
            self.database_url,
            poolclass=poolclass,
            echo=self.echo,
            echo_pool=self.echo_pool,
            future=True,
            query_cache_size=1200,  # Increase query cache
            **pool_kwargs
        )
        
        # Add event listeners for monitoring
        self._setup_event_listeners(engine)
        
        return engine
        
    def _setup_event_listeners(self, engine):
        """Setup event listeners for monitoring and optimization."""
        
        @event.listens_for(engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            """Set SQLite pragmas for better performance."""
            if 'sqlite' in self.database_url:
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
                cursor.execute("PRAGMA temp_store=MEMORY")
                cursor.close()
                
        @event.listens_for(engine.sync_engine, "connect")
        def set_postgresql_params(dbapi_conn, connection_record):
            """Set PostgreSQL connection parameters."""
            if 'postgresql' in self.database_url:
                with dbapi_conn.cursor() as cursor:
                    # Set statement timeout to prevent long-running queries
                    cursor.execute("SET statement_timeout = '30s'")
                    # Set lock timeout to prevent deadlocks
                    cursor.execute("SET lock_timeout = '10s'")
                    # Enable JIT for complex queries
                    cursor.execute("SET jit = 'on'")
                    # Optimize for read-heavy workloads
                    cursor.execute("SET random_page_cost = 1.1")
                    
    async def get_session(self) -> AsyncSession:
        """Get a new database session."""
        async with self.sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
                
    async def close(self):
        """Close the database engine."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._sessionmaker = None


class DatabaseOptimizationMiddleware:
    """Middleware for database query optimization."""
    
    def __init__(self, app, db_config: OptimizedDatabaseConfig):
        self.app = app
        self.db_config = db_config
        
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Add database session to request state
            async with self.db_config.sessionmaker() as session:
                scope["state"] = scope.get("state", {})
                scope["state"]["db"] = session
                
                try:
                    await self.app(scope, receive, send)
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise
                finally:
                    await session.close()
        else:
            await self.app(scope, receive, send)


# Query execution monitoring
class QueryMonitor:
    """Monitor and log slow queries."""
    
    def __init__(self, slow_query_threshold: float = 1.0):
        """
        Initialize query monitor.
        
        Args:
            slow_query_threshold: Log queries slower than this (seconds)
        """
        self.slow_query_threshold = slow_query_threshold
        self.query_stats = {}
        
    def before_cursor_execute(self, conn, cursor, statement, parameters, context, executemany):
        """Called before query execution."""
        context._query_start_time = time.time()
        
    def after_cursor_execute(self, conn, cursor, statement, parameters, context, executemany):
        """Called after query execution."""
        total_time = time.time() - context._query_start_time
        
        # Log slow queries
        if total_time > self.slow_query_threshold:
            logger.warning(
                f"Slow query detected ({total_time:.2f}s): {statement[:100]}..."
            )
            
        # Update statistics
        query_type = statement.split()[0].upper()
        if query_type not in self.query_stats:
            self.query_stats[query_type] = {
                'count': 0,
                'total_time': 0,
                'max_time': 0
            }
            
        stats = self.query_stats[query_type]
        stats['count'] += 1
        stats['total_time'] += total_time
        stats['max_time'] = max(stats['max_time'], total_time)
        
    def get_stats(self):
        """Get query statistics."""
        return {
            query_type: {
                **stats,
                'avg_time': stats['total_time'] / stats['count'] if stats['count'] > 0 else 0
            }
            for query_type, stats in self.query_stats.items()
        }


# Connection pool monitoring
class PoolMonitor:
    """Monitor connection pool health."""
    
    def __init__(self, engine):
        self.engine = engine
        
    def get_pool_status(self):
        """Get current pool status."""
        pool = self.engine.pool
        
        return {
            'size': pool.size(),
            'checked_in': pool.checkedin(),
            'checked_out': pool.checkedout(),
            'overflow': pool.overflow(),
            'total': pool.total(),
        }
        
    def log_pool_status(self):
        """Log pool status for monitoring."""
        status = self.get_pool_status()
        logger.info(f"Connection pool status: {status}")
        
        # Warn if pool is exhausted
        if status['checked_out'] >= status['size']:
            logger.warning("Connection pool exhausted!")


# Example usage
"""
# 1. Create optimized database configuration
db_config = OptimizedDatabaseConfig(
    database_url="postgresql+asyncpg://user:pass@localhost/mams",
    pool_size=20,
    max_overflow=40,
    pool_recycle=3600,
    echo=False,
    echo_pool=True  # Monitor pool usage
)

# 2. Use in FastAPI app
from fastapi import FastAPI, Depends

app = FastAPI()

async def get_db():
    async with db_config.sessionmaker() as session:
        yield session

@app.on_event("startup")
async def startup():
    # Warm up the connection pool
    async with db_config.engine.begin() as conn:
        await conn.execute("SELECT 1")
        
@app.on_event("shutdown")
async def shutdown():
    await db_config.close()

# 3. Monitor queries
query_monitor = QueryMonitor(slow_query_threshold=0.5)
event.listen(db_config.engine.sync_engine, "before_cursor_execute", query_monitor.before_cursor_execute)
event.listen(db_config.engine.sync_engine, "after_cursor_execute", query_monitor.after_cursor_execute)

# 4. Monitor connection pool
pool_monitor = PoolMonitor(db_config.engine)
# Add to your monitoring/metrics collection
"""

import time