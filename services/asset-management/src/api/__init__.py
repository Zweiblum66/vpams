"""
API module for Asset Management Service

This module exports the main router that includes all sub-routers.
"""

from fastapi import APIRouter
from .routes import router as asset_router
from .project_routes import router as project_router
from .template_routes import router as template_router
from .sharing_routes import router as sharing_router
from .shotlist_routes import router as shotlist_router
from .timeline_routes import router as timeline_router
from .track_routes import router as track_router
from .transition_routes import router as transition_router
from .version_routes import router as version_router
from .comment_routes import router as comment_router
from .activity_routes import router as activity_router
from .notification_routes import router as notification_router
from .routes.monitoring import router as monitoring_router

# Create main router
router = APIRouter()

# Include sub-routers
router.include_router(asset_router)
router.include_router(project_router)
router.include_router(template_router)
router.include_router(sharing_router)
router.include_router(shotlist_router)
router.include_router(timeline_router)
router.include_router(track_router)
router.include_router(transition_router)
router.include_router(version_router)
router.include_router(comment_router)
router.include_router(activity_router)
router.include_router(notification_router)
router.include_router(monitoring_router)

__all__ = ["router"]