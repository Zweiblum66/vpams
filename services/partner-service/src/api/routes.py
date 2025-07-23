"""
Main API routes for Partner Service
"""

from fastapi import APIRouter
from .partner_routes import router as partner_router
from .dashboard_routes import router as dashboard_router

router = APIRouter()

# Include all route modules
router.include_router(partner_router, prefix="/partners", tags=["partners"])
router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])