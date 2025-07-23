"""API Routes for GDPR Compliance Service"""

from fastapi import APIRouter
from .endpoints import consent, data_requests, privacy_policy, audit, admin, retention, reports, classification, dashboard, policy, access_reviews, data_lineage, risk_assessment, compliance_automation

router = APIRouter(prefix="/api/v1")

# Include sub-routers
router.include_router(consent.router, prefix="/consent", tags=["consent"])
router.include_router(data_requests.router, prefix="/data-requests", tags=["data-requests"])
router.include_router(privacy_policy.router, prefix="/privacy-policy", tags=["privacy-policy"])
router.include_router(audit.router, prefix="/audit", tags=["audit"])
router.include_router(admin.router, prefix="/admin", tags=["admin"])
router.include_router(retention.router, prefix="/retention", tags=["retention"])
router.include_router(reports.router, prefix="/reports", tags=["reports"])
router.include_router(classification.router, prefix="/classification", tags=["classification"])
router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
router.include_router(policy.router, prefix="/policy", tags=["policy"])
router.include_router(access_reviews.router, prefix="/access-reviews", tags=["access-reviews"])
router.include_router(data_lineage.router, tags=["data-lineage"])
router.include_router(risk_assessment.router, tags=["risk-assessment"])
router.include_router(compliance_automation.router, tags=["compliance-automation"])