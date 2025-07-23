"""Risk Assessment API endpoints"""

from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from ...db.base import get_db
from ...core.exceptions import NotFoundError, ValidationError
from ...api.dependencies import get_current_user
from ...models.schemas import (
    RiskAssessmentCreate, RiskAssessmentUpdate, RiskAssessmentResponse,
    RiskFactorCreate, RiskFactorUpdate, RiskFactorResponse,
    RiskMitigationPlanCreate, RiskMitigationPlanUpdate, RiskMitigationPlanResponse,
    RiskIncidentCreate, RiskIncidentUpdate, RiskIncidentResponse,
    RiskMetricsResponse, RiskDashboardResponse,
    RiskCategory, RiskSeverity, RiskStatus, User
)
from ...services.risk_assessment_service import RiskAssessmentService

router = APIRouter(prefix="/api/v1/risk-assessment", tags=["risk-assessment"])


# Risk Assessment Management Endpoints

@router.post("/assessments", response_model=RiskAssessmentResponse, status_code=status.HTTP_201_CREATED)
async def create_risk_assessment(
    assessment_data: RiskAssessmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new risk assessment"""
    try:
        service = RiskAssessmentService(db)
        return await service.create_risk_assessment(assessment_data, str(current_user.id))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create risk assessment")


@router.get("/assessments/{assessment_id}", response_model=RiskAssessmentResponse)
async def get_risk_assessment(
    assessment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get risk assessment by ID"""
    try:
        service = RiskAssessmentService(db)
        return await service.get_risk_assessment(assessment_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve risk assessment")


@router.patch("/assessments/{assessment_id}", response_model=RiskAssessmentResponse)
async def update_risk_assessment(
    assessment_id: str,
    update_data: RiskAssessmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update risk assessment"""
    try:
        service = RiskAssessmentService(db)
        return await service.update_risk_assessment(assessment_id, update_data, str(current_user.id))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to update risk assessment")


@router.delete("/assessments/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_risk_assessment(
    assessment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete risk assessment"""
    try:
        service = RiskAssessmentService(db)
        await service.delete_risk_assessment(assessment_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to delete risk assessment")


@router.get("/assessments", response_model=List[RiskAssessmentResponse])
async def list_risk_assessments(
    category: Optional[RiskCategory] = Query(None, description="Filter by risk category"),
    severity: Optional[RiskSeverity] = Query(None, description="Filter by severity"),
    status: Optional[RiskStatus] = Query(None, description="Filter by status"),
    risk_owner: Optional[str] = Query(None, description="Filter by risk owner"),
    assigned_to: Optional[str] = Query(None, description="Filter by assigned user"),
    overdue_reviews: bool = Query(False, description="Show only overdue reviews"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of assessments to return"),
    offset: int = Query(0, ge=0, description="Number of assessments to skip"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List risk assessments with filtering and sorting"""
    try:
        service = RiskAssessmentService(db)
        return await service.list_risk_assessments(
            category=category,
            severity=severity,
            status=status,
            risk_owner=risk_owner,
            assigned_to=assigned_to,
            overdue_reviews=overdue_reviews,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve risk assessments")


# Risk Factor Management Endpoints

@router.post("/assessments/{assessment_id}/factors", response_model=RiskFactorResponse, status_code=status.HTTP_201_CREATED)
async def add_risk_factor(
    assessment_id: str,
    factor_data: RiskFactorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a risk factor to an assessment"""
    try:
        service = RiskAssessmentService(db)
        return await service.add_risk_factor(assessment_id, factor_data, str(current_user.id))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to add risk factor")


# Mitigation Plan Management Endpoints

@router.post("/assessments/{assessment_id}/mitigation-plans", response_model=RiskMitigationPlanResponse, status_code=status.HTTP_201_CREATED)
async def add_mitigation_plan(
    assessment_id: str,
    plan_data: RiskMitigationPlanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a mitigation plan to an assessment"""
    try:
        service = RiskAssessmentService(db)
        return await service.add_mitigation_plan(assessment_id, plan_data, str(current_user.id))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to add mitigation plan")


@router.patch("/mitigation-plans/{plan_id}/progress", response_model=RiskMitigationPlanResponse)
async def update_mitigation_progress(
    plan_id: str,
    progress_percentage: float = Query(..., ge=0.0, le=100.0, description="Progress percentage"),
    status: Optional[str] = Query(None, description="Updated status"),
    actual_completion_date: Optional[datetime] = Query(None, description="Actual completion date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update mitigation plan progress"""
    try:
        service = RiskAssessmentService(db)
        return await service.update_mitigation_progress(
            plan_id, progress_percentage, status, actual_completion_date
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to update mitigation progress")


# Incident Management Endpoints

@router.post("/incidents", response_model=RiskIncidentResponse, status_code=status.HTTP_201_CREATED)
async def create_risk_incident(
    incident_data: RiskIncidentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new risk incident"""
    try:
        service = RiskAssessmentService(db)
        return await service.create_incident(incident_data, str(current_user.id))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create risk incident")


# Analytics and Reporting Endpoints

@router.get("/metrics", response_model=RiskMetricsResponse)
async def get_risk_metrics(
    start_date: Optional[datetime] = Query(None, description="Start date for metrics"),
    end_date: Optional[datetime] = Query(None, description="End date for metrics"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get risk assessment metrics"""
    try:
        service = RiskAssessmentService(db)
        return await service.get_risk_metrics(start_date, end_date)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve risk metrics")


@router.get("/dashboard", response_model=RiskDashboardResponse)
async def get_risk_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive risk dashboard data"""
    try:
        service = RiskAssessmentService(db)
        return await service.get_risk_dashboard()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve risk dashboard")


# Advanced Analytics Endpoints

@router.get("/assessments/overdue-reviews", response_model=List[RiskAssessmentResponse])
async def get_overdue_reviews(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of assessments to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get risk assessments with overdue reviews"""
    try:
        service = RiskAssessmentService(db)
        return await service.list_risk_assessments(
            overdue_reviews=True,
            limit=limit,
            sort_by="next_review_due",
            sort_order="asc"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve overdue reviews")


@router.get("/assessments/high-risk", response_model=List[RiskAssessmentResponse])
async def get_high_risk_assessments(
    limit: int = Query(50, ge=1, le=500, description="Maximum number of assessments to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get high and critical risk assessments"""
    try:
        service = RiskAssessmentService(db)
        
        # Get high risk assessments
        high_risks = await service.list_risk_assessments(
            severity=RiskSeverity.HIGH,
            limit=limit//2,
            sort_by="risk_score",
            sort_order="desc"
        )
        
        # Get critical risk assessments
        critical_risks = await service.list_risk_assessments(
            severity=RiskSeverity.CRITICAL,
            limit=limit//2,
            sort_by="risk_score",
            sort_order="desc"
        )
        
        # Combine and sort by risk score
        all_risks = high_risks + critical_risks
        all_risks.sort(key=lambda x: x.risk_score, reverse=True)
        
        return all_risks[:limit]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve high risk assessments")


@router.get("/assessments/by-owner/{owner}", response_model=List[RiskAssessmentResponse])
async def get_assessments_by_owner(
    owner: str,
    status: Optional[RiskStatus] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of assessments to return"),
    offset: int = Query(0, ge=0, description="Number of assessments to skip"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get risk assessments by owner"""
    try:
        service = RiskAssessmentService(db)
        return await service.list_risk_assessments(
            risk_owner=owner,
            status=status,
            limit=limit,
            offset=offset,
            sort_by="created_at",
            sort_order="desc"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve assessments by owner")


# Risk Assessment Templates and Automation

@router.get("/templates/categories", response_model=Dict[str, List[str]])
async def get_risk_categories_and_types():
    """Get available risk categories and common risk types"""
    return {
        "categories": [category.value for category in RiskCategory],
        "severities": [severity.value for severity in RiskSeverity],
        "statuses": [status.value for status in RiskStatus],
        "common_risk_types": [
            "Data breach via unauthorized access",
            "System vulnerability exploitation",
            "Insider threat - malicious",
            "Insider threat - accidental",
            "Third-party vendor breach",
            "Regulatory compliance violation",
            "Privacy policy violation",
            "Inadequate data retention",
            "Cross-border data transfer",
            "Consent management failure",
            "Data quality degradation",
            "Business continuity failure",
            "Reputation damage",
            "Financial loss",
            "Legal liability"
        ],
        "mitigation_types": [
            "avoid",
            "transfer",
            "mitigate",
            "accept"
        ]
    }


# Health Check Endpoint

@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db)
):
    """Health check for risk assessment service"""
    try:
        # Test database connection
        await db.execute("SELECT 1")
        return {
            "status": "healthy",
            "service": "risk-assessment",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )