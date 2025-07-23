"""
MAMS Analytics Service

This service provides comprehensive usage analytics, user behavior tracking,
and business intelligence for the MAMS platform.
"""

import os
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging.python_logging import setup_fastapi_logging
from shared.tracing.python_tracing import setup_service_tracing
from shared.auth.dependencies import get_current_user
from shared.db.postgres import get_session

from .core.config import settings
from .core.database import init_database
from .api.v1 import usage, user_behavior, reports, real_time
from .services.analytics_engine import AnalyticsEngine
from .services.data_collector import DataCollector
from .services.report_generator import ReportGenerator


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    await init_database()
    
    # Initialize analytics services
    app.state.analytics_engine = AnalyticsEngine()
    app.state.data_collector = DataCollector()
    app.state.report_generator = ReportGenerator()
    
    # Start background tasks
    app.state.background_tasks = asyncio.create_task(
        start_background_tasks(app)
    )
    
    yield
    
    # Shutdown
    if hasattr(app.state, 'background_tasks'):
        app.state.background_tasks.cancel()
        try:
            await app.state.background_tasks
        except asyncio.CancelledError:
            pass


async def start_background_tasks(app: FastAPI):
    """Start background data processing tasks."""
    try:
        while True:
            # Process analytics data every 5 minutes
            await app.state.analytics_engine.process_batch()
            
            # Generate periodic reports every hour
            await app.state.report_generator.generate_periodic_reports()
            
            # Clean up old data based on retention policies
            await app.state.data_collector.cleanup_old_data()
            
            # Wait 5 minutes before next cycle
            await asyncio.sleep(300)
    except asyncio.CancelledError:
        pass


# Create FastAPI app
app = FastAPI(
    title="MAMS Analytics Service",
    description="Usage analytics and business intelligence for MAMS",
    version="1.0.0",
    lifespan=lifespan,
)

# Setup logging and tracing
setup_fastapi_logging(app, "analytics")
tracer = setup_service_tracing(app, "analytics", "1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
from .api.v1 import analytics, predictive
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(usage.router, prefix="/api/v1/usage", tags=["usage"])
app.include_router(user_behavior.router, prefix="/api/v1/behavior", tags=["behavior"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(real_time.router, prefix="/api/v1/realtime", tags=["realtime"])
app.include_router(predictive.router, prefix="/api/v1/predictive", tags=["predictive"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "analytics",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from fastapi import Response
    
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@app.post("/api/v1/events")
async def track_event(
    event_data: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session)
):
    """Track a user event for analytics."""
    # Add to processing queue
    background_tasks.add_task(
        app.state.data_collector.collect_event,
        event_data,
        db
    )
    
    return {"status": "accepted", "message": "Event queued for processing"}


@app.get("/api/v1/dashboard/overview")
async def dashboard_overview(
    timeframe: str = Query("24h", description="Time range: 1h, 24h, 7d, 30d"),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Get dashboard overview data."""
    if not current_user.has_permission("analytics.view"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Parse timeframe
    end_time = datetime.utcnow()
    if timeframe == "1h":
        start_time = end_time - timedelta(hours=1)
    elif timeframe == "24h":
        start_time = end_time - timedelta(hours=24)
    elif timeframe == "7d":
        start_time = end_time - timedelta(days=7)
    elif timeframe == "30d":
        start_time = end_time - timedelta(days=30)
    else:
        raise HTTPException(status_code=400, detail="Invalid timeframe")
    
    # Get overview metrics
    overview = await app.state.analytics_engine.get_overview_metrics(
        start_time, end_time, db
    )
    
    return overview


@app.get("/api/v1/dashboard/trends")
async def dashboard_trends(
    metric: str = Query(..., description="Metric to analyze"),
    timeframe: str = Query("7d", description="Time range"),
    granularity: str = Query("1h", description="Data granularity"),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Get trend data for dashboard charts."""
    if not current_user.has_permission("analytics.view"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    trends = await app.state.analytics_engine.get_trend_data(
        metric, timeframe, granularity, db
    )
    
    return trends


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8013,
        reload=True,
        log_config=None  # Use our custom logging
    )