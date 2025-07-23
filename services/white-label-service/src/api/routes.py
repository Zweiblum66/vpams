"""
Main API routes for White-Label Service
"""

from fastapi import APIRouter
from .theme_routes import router as theme_router
from .branding_routes import router as branding_router
from .domain_routes import router as domain_router
from .email_template_routes import router as email_template_router
from .mobile_app_routes import router as mobile_app_router
from .asset_routes import router as asset_router
from .analytics_routes import router as analytics_router

router = APIRouter()

# Include all route modules
router.include_router(theme_router, prefix="/themes", tags=["themes"])
router.include_router(branding_router, prefix="/branding", tags=["branding"])
router.include_router(domain_router, prefix="/domains", tags=["domains"])
router.include_router(email_template_router, prefix="/email-templates", tags=["email-templates"])
router.include_router(mobile_app_router, prefix="/mobile-apps", tags=["mobile-apps"])
router.include_router(asset_router, prefix="/assets", tags=["assets"])
router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])