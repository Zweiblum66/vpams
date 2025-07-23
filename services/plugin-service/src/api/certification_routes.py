"""
Plugin Certification Routes for Plugin Service
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_

from ..core.logging import get_logger
from ..core.exceptions import (
    PluginError,
    PluginNotFoundError,
    PluginPermissionError
)
from ..db.base import get_db
from ..models.schemas import PluginValidationResponse
from .dependencies import get_current_user

logger = get_logger(__name__)

router = APIRouter(prefix="/certification", tags=["certification"])


@router.post("/submit/{plugin_id}", response_model=Dict[str, Any])
async def submit_plugin_for_certification(
    plugin_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submit plugin for certification review"""
    from ..db.models import Plugin, CertificationRequest, DeveloperAccount
    import uuid
    
    # Get developer account
    developer_result = await db.execute(
        select(DeveloperAccount).where(
            DeveloperAccount.user_id == current_user.get("id")
        )
    )
    developer = developer_result.scalar_one_or_none()
    
    if not developer:
        raise HTTPException(status_code=404, detail="Developer account not found")
    
    # Get plugin
    plugin_result = await db.execute(
        select(Plugin).where(
            and_(
                Plugin.plugin_id == plugin_id,
                Plugin.developer_id == developer.id
            )
        )
    )
    plugin = plugin_result.scalar_one_or_none()
    
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    # Check if already submitted or certified
    existing_request = await db.execute(
        select(CertificationRequest).where(
            and_(
                CertificationRequest.plugin_id == plugin.id,
                CertificationRequest.status.in_(["pending", "in_review", "certified"])
            )
        )
    )
    
    if existing_request.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Plugin already submitted for certification or is certified"
        )
    
    # Create certification request
    cert_request = CertificationRequest(
        id=str(uuid.uuid4()),
        plugin_id=plugin.id,
        developer_id=developer.id,
        version=plugin.version,
        status="pending",
        submitted_at=datetime.utcnow(),
        certification_level="standard"  # Default level
    )
    
    db.add(cert_request)
    await db.commit()
    
    # Start automated validation in background
    background_tasks.add_task(run_automated_validation, cert_request.id, db)
    
    return {
        "certification_id": cert_request.id,
        "plugin_id": plugin_id,
        "status": "submitted",
        "message": "Plugin submitted for certification. Automated validation will begin shortly.",
        "estimated_review_time": "3-5 business days"
    }


@router.get("/status/{plugin_id}", response_model=Dict[str, Any])
async def get_certification_status(
    plugin_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get certification status for a plugin"""
    from ..db.models import Plugin, CertificationRequest, CertificationTest, DeveloperAccount
    
    # Get developer account
    developer_result = await db.execute(
        select(DeveloperAccount).where(
            DeveloperAccount.user_id == current_user.get("id")
        )
    )
    developer = developer_result.scalar_one_or_none()
    
    if not developer:
        raise HTTPException(status_code=404, detail="Developer account not found")
    
    # Get plugin
    plugin_result = await db.execute(
        select(Plugin).where(
            and_(
                Plugin.plugin_id == plugin_id,
                Plugin.developer_id == developer.id
            )
        )
    )
    plugin = plugin_result.scalar_one_or_none()
    
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    # Get latest certification request
    cert_request_result = await db.execute(
        select(CertificationRequest)
        .where(CertificationRequest.plugin_id == plugin.id)
        .order_by(desc(CertificationRequest.submitted_at))
        .limit(1)
    )
    cert_request = cert_request_result.scalar_one_or_none()
    
    if not cert_request:
        return {
            "plugin_id": plugin_id,
            "certification_status": "not_submitted",
            "message": "Plugin has not been submitted for certification"
        }
    
    # Get test results
    test_results = await db.execute(
        select(CertificationTest)
        .where(CertificationTest.certification_id == cert_request.id)
        .order_by(CertificationTest.created_at)
    )
    tests = test_results.scalars().all()
    
    test_summary = []
    for test in tests:
        test_summary.append({
            "test_name": test.test_name,
            "test_type": test.test_type,
            "status": test.status,
            "score": test.score,
            "details": test.details,
            "completed_at": test.completed_at
        })
    
    return {
        "certification_id": cert_request.id,
        "plugin_id": plugin_id,
        "certification_status": cert_request.status,
        "certification_level": cert_request.certification_level,
        "submitted_at": cert_request.submitted_at,
        "reviewed_at": cert_request.reviewed_at,
        "expires_at": cert_request.expires_at,
        "overall_score": cert_request.overall_score,
        "reviewer_notes": cert_request.reviewer_notes,
        "test_results": test_summary,
        "next_steps": get_next_steps(cert_request.status)
    }


@router.get("/tests/validate/{plugin_id}", response_model=PluginValidationResponse)
async def validate_plugin(
    plugin_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Run validation tests on a plugin before certification"""
    from ..services.certification_service import CertificationService
    from ..db.models import Plugin, DeveloperAccount
    
    # Get developer account
    developer_result = await db.execute(
        select(DeveloperAccount).where(
            DeveloperAccount.user_id == current_user.get("id")
        )
    )
    developer = developer_result.scalar_one_or_none()
    
    if not developer:
        raise HTTPException(status_code=404, detail="Developer account not found")
    
    # Get plugin
    plugin_result = await db.execute(
        select(Plugin).where(
            and_(
                Plugin.plugin_id == plugin_id,
                Plugin.developer_id == developer.id
            )
        )
    )
    plugin = plugin_result.scalar_one_or_none()
    
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    # Run validation
    cert_service = CertificationService()
    validation_result = await cert_service.validate_plugin(plugin)
    
    return validation_result


@router.get("/badges/{plugin_id}", response_model=Dict[str, Any])
async def get_certification_badges(
    plugin_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get certification badges for a plugin (public endpoint)"""
    from ..db.models import Plugin, CertificationRequest
    
    # Get plugin
    plugin_result = await db.execute(
        select(Plugin).where(Plugin.plugin_id == plugin_id)
    )
    plugin = plugin_result.scalar_one_or_none()
    
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    # Get latest certification
    cert_request_result = await db.execute(
        select(CertificationRequest)
        .where(
            and_(
                CertificationRequest.plugin_id == plugin.id,
                CertificationRequest.status == "certified",
                CertificationRequest.expires_at > datetime.utcnow()
            )
        )
        .order_by(desc(CertificationRequest.reviewed_at))
        .limit(1)
    )
    cert_request = cert_request_result.scalar_one_or_none()
    
    badges = []
    
    if cert_request:
        badges.append({
            "type": "certification",
            "level": cert_request.certification_level,
            "title": f"MAMS {cert_request.certification_level.title()} Certified",
            "description": "This plugin meets MAMS quality and security standards",
            "issued_date": cert_request.reviewed_at,
            "expires_date": cert_request.expires_at,
            "score": cert_request.overall_score,
            "badge_url": f"/badges/{cert_request.certification_level}.svg"
        })
        
        # Add specific badges based on test results
        if cert_request.overall_score >= 95:
            badges.append({
                "type": "excellence",
                "title": "Excellence Badge",
                "description": "Exceptional quality and performance",
                "badge_url": "/badges/excellence.svg"
            })
        
        if cert_request.overall_score >= 85:
            badges.append({
                "type": "quality",
                "title": "Quality Assured",
                "description": "High quality standards met",
                "badge_url": "/badges/quality.svg"
            })
    
    return {
        "plugin_id": plugin_id,
        "certified": len(badges) > 0,
        "badges": badges,
        "certification_url": f"/plugins/{plugin_id}/certification" if badges else None
    }


@router.get("/levels", response_model=List[Dict[str, Any]])
async def get_certification_levels():
    """Get available certification levels and requirements"""
    return [
        {
            "level": "basic",
            "title": "Basic Certification",
            "description": "Plugin meets basic functionality and security requirements",
            "requirements": [
                "Plugin loads and initializes correctly",
                "No security vulnerabilities detected",
                "Basic functionality tests pass",
                "Code quality score >= 60%"
            ],
            "benefits": [
                "Listed in certified section",
                "Basic quality badge",
                "Increased user trust"
            ],
            "min_score": 60,
            "review_time": "1-2 business days"
        },
        {
            "level": "standard",
            "title": "Standard Certification",
            "description": "Plugin meets comprehensive quality and performance standards",
            "requirements": [
                "All basic certification requirements",
                "Performance tests pass",
                "Documentation quality check",
                "Error handling validation",
                "Code quality score >= 75%"
            ],
            "benefits": [
                "All basic certification benefits",
                "Featured in marketplace",
                "Standard quality badge",
                "Priority customer support"
            ],
            "min_score": 75,
            "review_time": "3-5 business days"
        },
        {
            "level": "premium",
            "title": "Premium Certification",
            "description": "Plugin exceeds quality standards with exceptional performance",
            "requirements": [
                "All standard certification requirements",
                "Advanced security audit",
                "Performance optimization",
                "Comprehensive test coverage",
                "Code quality score >= 90%"
            ],
            "benefits": [
                "All standard certification benefits",
                "Premium marketplace placement",
                "Excellence badge",
                "Marketing support",
                "Direct developer support channel"
            ],
            "min_score": 90,
            "review_time": "5-7 business days"
        }
    ]


@router.get("/stats", response_model=Dict[str, Any])
async def get_certification_stats(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get certification statistics for developer"""
    from ..db.models import CertificationRequest, DeveloperAccount
    
    # Get developer account
    developer_result = await db.execute(
        select(DeveloperAccount).where(
            DeveloperAccount.user_id == current_user.get("id")
        )
    )
    developer = developer_result.scalar_one_or_none()
    
    if not developer:
        raise HTTPException(status_code=404, detail="Developer account not found")
    
    # Get certification statistics
    total_requests = await db.execute(
        select(func.count(CertificationRequest.id))
        .where(CertificationRequest.developer_id == developer.id)
    )
    
    certified_count = await db.execute(
        select(func.count(CertificationRequest.id))
        .where(
            and_(
                CertificationRequest.developer_id == developer.id,
                CertificationRequest.status == "certified"
            )
        )
    )
    
    pending_count = await db.execute(
        select(func.count(CertificationRequest.id))
        .where(
            and_(
                CertificationRequest.developer_id == developer.id,
                CertificationRequest.status.in_(["pending", "in_review"])
            )
        )
    )
    
    avg_score = await db.execute(
        select(func.avg(CertificationRequest.overall_score))
        .where(
            and_(
                CertificationRequest.developer_id == developer.id,
                CertificationRequest.status == "certified"
            )
        )
    )
    
    return {
        "total_submissions": total_requests.scalar() or 0,
        "certified_plugins": certified_count.scalar() or 0,
        "pending_reviews": pending_count.scalar() or 0,
        "average_score": float(avg_score.scalar() or 0),
        "certification_rate": (certified_count.scalar() or 0) / max(total_requests.scalar() or 1, 1) * 100
    }


# Admin routes for certification management
@router.get("/admin/queue", response_model=List[Dict[str, Any]])
async def get_certification_queue(
    status: Optional[str] = None,
    level: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get certification review queue (admin only)"""
    if not current_user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    from ..db.models import CertificationRequest, Plugin, DeveloperAccount
    
    # Build query
    query = select(CertificationRequest, Plugin, DeveloperAccount).join(
        Plugin, CertificationRequest.plugin_id == Plugin.id
    ).join(
        DeveloperAccount, CertificationRequest.developer_id == DeveloperAccount.id
    )
    
    if status:
        query = query.where(CertificationRequest.status == status)
    
    if level:
        query = query.where(CertificationRequest.certification_level == level)
    
    query = query.order_by(CertificationRequest.submitted_at)
    
    result = await db.execute(query)
    requests = result.all()
    
    queue = []
    for cert_request, plugin, developer in requests:
        queue.append({
            "certification_id": cert_request.id,
            "plugin_id": plugin.plugin_id,
            "plugin_name": plugin.name,
            "developer_name": developer.company_name or f"User {developer.user_id}",
            "version": cert_request.version,
            "level": cert_request.certification_level,
            "status": cert_request.status,
            "submitted_at": cert_request.submitted_at,
            "overall_score": cert_request.overall_score,
            "priority": get_review_priority(cert_request)
        })
    
    return queue


async def run_automated_validation(certification_id: str, db: AsyncSession):
    """Run automated validation tests for certification"""
    from ..services.certification_service import CertificationService
    from ..db.models import CertificationRequest
    
    try:
        cert_service = CertificationService()
        
        # Get certification request
        cert_request_result = await db.execute(
            select(CertificationRequest).where(CertificationRequest.id == certification_id)
        )
        cert_request = cert_request_result.scalar_one()
        
        # Update status to in_review
        cert_request.status = "in_review"
        await db.commit()
        
        # Run automated tests
        await cert_service.run_certification_tests(cert_request, db)
        
        logger.info(f"Automated validation completed for certification {certification_id}")
        
    except Exception as e:
        logger.error(f"Failed to run automated validation: {e}")
        
        # Update status to failed
        cert_request.status = "failed"
        cert_request.reviewer_notes = f"Automated validation failed: {str(e)}"
        await db.commit()


def get_next_steps(status: str) -> List[str]:
    """Get next steps based on certification status"""
    if status == "pending":
        return [
            "Automated validation will begin shortly",
            "You will receive an email when review starts"
        ]
    elif status == "in_review":
        return [
            "Your plugin is being reviewed",
            "Check back in 1-2 business days for updates"
        ]
    elif status == "certified":
        return [
            "Congratulations! Your plugin is certified",
            "Users can now see your certification badge"
        ]
    elif status == "rejected":
        return [
            "Review the feedback and fix identified issues",
            "Resubmit when ready for another review"
        ]
    elif status == "failed":
        return [
            "Automated tests failed",
            "Review the test results and fix issues",
            "Contact support if you need assistance"
        ]
    else:
        return []


def get_review_priority(cert_request) -> str:
    """Calculate review priority based on various factors"""
    days_waiting = (datetime.utcnow() - cert_request.submitted_at).days
    
    if cert_request.certification_level == "premium":
        return "high" if days_waiting > 3 else "medium"
    elif cert_request.certification_level == "standard":
        return "high" if days_waiting > 5 else "medium"
    else:
        return "high" if days_waiting > 7 else "low"