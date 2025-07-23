"""
Main API routes for Integration Catalog Service
"""

from fastapi import APIRouter
from .catalog_routes import router as catalog_router
from .installation_routes import router as installation_router

router = APIRouter()

# Include all route modules
router.include_router(catalog_router, prefix="/catalog", tags=["catalog"])
router.include_router(installation_router, prefix="/installations", tags=["installations"])