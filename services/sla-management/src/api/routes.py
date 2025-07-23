"""
API routes for SLA Management Service.
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.dependencies import get_db, get_current_user
from ..services.sla_service import (
    SLAService, SLATier, SLAStatus, MetricType, SLAMetric, SLAPenalty, 
    SLANotification, SLAAgreement
)
from ..db.models import Customer

router = APIRouter(prefix="/api/v1/sla", tags=["sla-management"])

# Pydantic schemas
class CustomerCreate(BaseModel):
    """Schema for creating customers."""
    customer_id: str = Field(..., description="Unique customer identifier")
    company_name: str = Field(..., description="Company name")
    contact_email: str = Field(..., description="Contact email")
    contact_name: str = Field(..., description="Contact person name")


class SLAMetricCreate(BaseModel):
    """Schema for creating SLA metrics."""
    metric_id: str = Field(..., description="Unique metric identifier")
    name: str = Field(..., description="Metric name")
    description: str = Field(..., description="Metric description")
    type: str = Field(..., description="Metric type (percentage, time, count, boolean)")
    target_value: float = Field(..., description="Target value for the metric")
    measurement_unit: str = Field(..., description="Unit of measurement")
    measurement_period: str = Field(..., description="Measurement period")
    threshold_warning: Optional[float] = Field(None, description="Warning threshold")
    threshold_critical: Optional[float] = Field(None, description="Critical threshold")


class SLAPenaltyCreate(BaseModel):
    """Schema for creating SLA penalties."""
    penalty_id: str = Field(..., description="Unique penalty identifier")
    name: str = Field(..., description="Penalty name")
    description: str = Field(..., description="Penalty description")
    trigger_condition: str = Field(..., description="Condition that triggers the penalty")
    penalty_type: str = Field(..., description="Type of penalty")
    penalty_amount: float = Field(..., description="Penalty amount")
    penalty_unit: str = Field(..., description="Penalty unit")
    max_penalty_per_period: Optional[float] = Field(None, description="Maximum penalty per period")


class SLANotificationCreate(BaseModel):
    """Schema for creating SLA notifications."""
    notification_id: str = Field(..., description="Unique notification identifier")
    trigger_condition: str = Field(..., description="Condition that triggers notification")
    notification_type: str = Field(..., description="Type of notification")
    recipients: List[str] = Field(..., description="List of recipients")
    template: str = Field(default="", description="Message template")
    escalation_delay: Optional[int] = Field(None, description="Escalation delay in minutes")


class SLAAgreementCreate(BaseModel):
    """Schema for creating SLA agreements."""
    customer_id: str = Field(..., description="Customer identifier")
    tier: str = Field(..., description="SLA tier (basic, professional, enterprise, premium)")
    name: Optional[str] = Field(None, description="Custom agreement name")
    description: Optional[str] = Field(None, description="Agreement description")
    effective_date: Optional[datetime] = Field(None, description="Effective date")
    expiration_date: Optional[datetime] = Field(None, description="Expiration date")
    custom_metrics: Optional[List[SLAMetricCreate]] = Field(None, description="Custom metrics")
    custom_penalties: Optional[List[SLAPenaltyCreate]] = Field(None, description="Custom penalties")
    custom_notifications: Optional[List[SLANotificationCreate]] = Field(None, description="Custom notifications")


class CompliancePeriodRequest(BaseModel):
    """Schema for compliance period requests."""
    agreement_id: str = Field(..., description="SLA agreement ID")
    period_start: datetime = Field(..., description="Period start date")
    period_end: datetime = Field(..., description="Period end date")


class SLAResponse(BaseModel):
    """Standard SLA response schema."""
    success: bool
    data: Dict[str, Any]
    message: str = ""


# Initialize service
sla_service = SLAService()


@router.post("/customers", response_model=SLAResponse)
async def create_customer(
    customer: CustomerCreate,
    current_user: Customer = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new customer."""
    try:
        # In a real implementation, this would save to database
        customer_data = {
            "id": str(uuid.uuid4()),
            "customer_id": customer.customer_id,
            "company_name": customer.company_name,
            "contact_email": customer.contact_email,
            "contact_name": customer.contact_name,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        return SLAResponse(
            success=True,
            data={"customer": customer_data},
            message="Customer created successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create customer: {str(e)}"
        )


@router.get("/tiers", response_model=SLAResponse)
async def get_sla_tiers(
    current_user: Customer = Depends(get_current_user)
):
    """Get available SLA tiers with their features."""
    try:
        tiers = {
            "basic": {
                "name": "Basic",
                "uptime_target": "99.0%",
                "support_hours": "Business hours (9 AM - 5 PM)",
                "response_time": "≤2000ms",
                "support_response": "≤24 hours",
                "features": [
                    "Basic monitoring",
                    "Email support",
                    "Standard backups (30 days)",
                    "Community forum access"
                ],
                "price_range": "$100-500/month"
            },
            "professional": {
                "name": "Professional",
                "uptime_target": "99.5%",
                "support_hours": "Extended hours (6 AM - 10 PM)",
                "response_time": "≤1000ms",
                "support_response": "≤8 hours",
                "features": [
                    "Advanced monitoring",
                    "Phone and email support",
                    "Extended backups (90 days)",
                    "Priority support queue",
                    "Dedicated account manager"
                ],
                "price_range": "$500-2000/month"
            },
            "enterprise": {
                "name": "Enterprise",
                "uptime_target": "99.9%",
                "support_hours": "24/7 support",
                "response_time": "≤500ms",
                "support_response": "≤2 hours",
                "features": [
                    "Real-time monitoring",
                    "Multi-channel support",
                    "Long-term backups (1 year)",
                    "Dedicated technical account manager",
                    "On-site support available",
                    "Compliance reporting"
                ],
                "price_range": "$2000-10000/month"
            },
            "premium": {
                "name": "Premium",
                "uptime_target": "99.99%",
                "support_hours": "24/7/365 premium support",
                "response_time": "≤250ms",
                "support_response": "≤1 hour",
                "features": [
                    "Predictive monitoring",
                    "Dedicated support team",
                    "Unlimited backups",
                    "Named technical contacts",
                    "Emergency hotline",
                    "Custom development",
                    "Strategic consulting"
                ],
                "price_range": "$10000+/month"
            }
        }
        
        return SLAResponse(
            success=True,
            data={"tiers": tiers},
            message="SLA tiers retrieved successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get SLA tiers: {str(e)}"
        )


@router.post("/agreements", response_model=SLAResponse)
async def create_sla_agreement(
    agreement: SLAAgreementCreate,
    background_tasks: BackgroundTasks,
    current_user: Customer = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new SLA agreement."""
    try:
        # Validate tier
        try:
            tier = SLATier(agreement.tier.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid SLA tier: {agreement.tier}"
            )
        
        # Convert custom metrics if provided
        custom_metrics = None
        if agreement.custom_metrics:
            custom_metrics = [
                SLAMetric(
                    metric_id=m.metric_id,
                    name=m.name,
                    description=m.description,
                    type=MetricType(m.type.lower()),
                    target_value=m.target_value,
                    measurement_unit=m.measurement_unit,
                    measurement_period=m.measurement_period,
                    threshold_warning=m.threshold_warning,
                    threshold_critical=m.threshold_critical
                ) for m in agreement.custom_metrics
            ]
        
        # Convert custom penalties if provided
        custom_penalties = None
        if agreement.custom_penalties:
            custom_penalties = [
                SLAPenalty(
                    penalty_id=p.penalty_id,
                    name=p.name,
                    description=p.description,
                    trigger_condition=p.trigger_condition,
                    penalty_type=p.penalty_type,
                    penalty_amount=p.penalty_amount,
                    penalty_unit=p.penalty_unit,
                    max_penalty_per_period=p.max_penalty_per_period
                ) for p in agreement.custom_penalties
            ]
        
        # Convert custom notifications if provided
        custom_notifications = None
        if agreement.custom_notifications:
            custom_notifications = [
                SLANotification(
                    notification_id=n.notification_id,
                    trigger_condition=n.trigger_condition,
                    notification_type=n.notification_type,
                    recipients=n.recipients,
                    template=n.template,
                    escalation_delay=n.escalation_delay
                ) for n in agreement.custom_notifications
            ]
        
        # Create SLA agreement
        sla_agreement = await sla_service.create_customer_sla(
            customer_id=agreement.customer_id,
            tier=tier,
            custom_metrics=custom_metrics,
            custom_penalties=custom_penalties,
            custom_notifications=custom_notifications
        )
        
        # Schedule background task for agreement processing
        background_tasks.add_task(
            _process_sla_agreement,
            sla_agreement.agreement_id
        )
        
        return SLAResponse(
            success=True,
            data={
                "agreement_id": sla_agreement.agreement_id,
                "customer_id": sla_agreement.customer_id,
                "tier": sla_agreement.tier.value,
                "status": sla_agreement.status.value,
                "effective_date": sla_agreement.effective_date.isoformat(),
                "metrics_count": len(sla_agreement.metrics),
                "penalties_count": len(sla_agreement.penalties),
                "notifications_count": len(sla_agreement.notifications)
            },
            message="SLA agreement created successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create SLA agreement: {str(e)}"
        )


@router.get("/agreements/{agreement_id}", response_model=SLAResponse)
async def get_sla_agreement(
    agreement_id: str,
    current_user: Customer = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get SLA agreement details."""
    try:
        # In a real implementation, this would query the database
        # For demo, return a sample agreement
        agreement_data = {
            "agreement_id": agreement_id,
            "customer_id": "customer_123",
            "tier": "professional",
            "name": "MAMS Professional SLA - Customer 123",
            "status": "active",
            "effective_date": "2025-01-01T00:00:00Z",
            "expiration_date": "2025-12-31T23:59:59Z",
            "metrics": [
                {
                    "metric_id": "uptime_professional",
                    "name": "System Uptime",
                    "target_value": 99.5,
                    "measurement_unit": "percentage"
                },
                {
                    "metric_id": "response_time_professional",
                    "name": "API Response Time",
                    "target_value": 1000,
                    "measurement_unit": "milliseconds"
                }
            ],
            "penalties": [
                {
                    "penalty_id": "uptime_penalty_professional",
                    "name": "Uptime Penalty",
                    "penalty_amount": 10.0,
                    "penalty_unit": "percentage"
                }
            ],
            "current_compliance": {
                "overall_score": 98.7,
                "status": "compliant",
                "last_assessment": "2025-07-20T12:00:00Z"
            }
        }
        
        return SLAResponse(
            success=True,
            data={"agreement": agreement_data},
            message="SLA agreement retrieved successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get SLA agreement: {str(e)}"
        )


@router.get("/agreements", response_model=SLAResponse)
async def list_sla_agreements(
    customer_id: Optional[str] = Query(None, description="Filter by customer ID"),
    tier: Optional[str] = Query(None, description="Filter by SLA tier"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200, description="Number of agreements to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: Customer = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List SLA agreements with filtering and pagination."""
    try:
        # In a real implementation, this would query the database
        # For demo, return sample agreements
        agreements = [
            {
                "agreement_id": f"sla_customer_{i}_{uuid.uuid4().hex[:8]}",
                "customer_id": f"customer_{i}",
                "company_name": f"Company {i}",
                "tier": ["basic", "professional", "enterprise", "premium"][i % 4],
                "status": "active",
                "effective_date": "2025-01-01T00:00:00Z",
                "current_compliance": {
                    "overall_score": 95.0 + (i % 10),
                    "status": "compliant" if (95.0 + (i % 10)) >= 95 else "warning"
                }
            } for i in range(1, min(limit + 1, 21))
        ]
        
        # Apply filters
        if customer_id:
            agreements = [a for a in agreements if a["customer_id"] == customer_id]
        if tier:
            agreements = [a for a in agreements if a["tier"] == tier.lower()]
        if status:
            agreements = [a for a in agreements if a["status"] == status.lower()]
        
        # Apply pagination
        total_agreements = len(agreements)
        paginated_agreements = agreements[offset:offset + limit]
        
        return SLAResponse(
            success=True,
            data={
                "agreements": paginated_agreements,
                "pagination": {
                    "total": total_agreements,
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + limit < total_agreements
                },
                "filters_applied": {
                    "customer_id": customer_id,
                    "tier": tier,
                    "status": status
                }
            },
            message="SLA agreements retrieved successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list SLA agreements: {str(e)}"
        )


@router.post("/compliance/calculate", response_model=SLAResponse)
async def calculate_compliance(
    request: CompliancePeriodRequest,
    current_user: Customer = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Calculate SLA compliance for a specific period."""
    try:
        # Get SLA agreement (mock for demo)
        tier = SLATier.PROFESSIONAL  # Would be retrieved from database
        template_agreement = sla_service.predefined_slas[tier]
        
        # Create agreement with request details
        agreement = SLAAgreement(
            agreement_id=request.agreement_id,
            customer_id="demo_customer",
            tier=tier,
            name="Demo Agreement",
            description="Demo SLA Agreement",
            effective_date=request.period_start,
            expiration_date=None,
            status=SLAStatus.ACTIVE,
            metrics=template_agreement.metrics,
            penalties=template_agreement.penalties,
            notifications=template_agreement.notifications,
            terms_and_conditions=template_agreement.terms_and_conditions,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Calculate compliance
        compliance_results = await sla_service.calculate_sla_compliance(
            agreement=agreement,
            period_start=request.period_start,
            period_end=request.period_end
        )
        
        return SLAResponse(
            success=True,
            data=compliance_results,
            message="SLA compliance calculated successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate compliance: {str(e)}"
        )


@router.get("/compliance/{agreement_id}/history", response_model=SLAResponse)
async def get_compliance_history(
    agreement_id: str,
    period_type: str = Query("monthly", description="Period type (daily, weekly, monthly, quarterly)"),
    limit: int = Query(12, ge=1, le=100, description="Number of periods to return"),
    current_user: Customer = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get compliance history for an SLA agreement."""
    try:
        # Generate sample compliance history
        compliance_history = []
        for i in range(limit):
            if period_type == "monthly":
                period_start = datetime.now(timezone.utc) - timedelta(days=30 * (i + 1))
                period_end = datetime.now(timezone.utc) - timedelta(days=30 * i)
            elif period_type == "weekly":
                period_start = datetime.now(timezone.utc) - timedelta(days=7 * (i + 1))
                period_end = datetime.now(timezone.utc) - timedelta(days=7 * i)
            else:  # daily
                period_start = datetime.now(timezone.utc) - timedelta(days=i + 1)
                period_end = datetime.now(timezone.utc) - timedelta(days=i)
            
            # Simulate compliance scores with some variation
            base_score = 97.5
            variation = (i % 7) - 3  # -3 to +3
            compliance_score = max(90, min(100, base_score + variation))
            
            compliance_history.append({
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "period_type": period_type,
                "overall_compliance": compliance_score,
                "status": "compliant" if compliance_score >= 95 else "warning" if compliance_score >= 90 else "critical",
                "total_penalties": 0 if compliance_score >= 95 else 50 if compliance_score >= 90 else 150
            })
        
        # Calculate trends
        scores = [h["overall_compliance"] for h in compliance_history[-6:]]
        trend = "stable"
        if len(scores) >= 3:
            recent_avg = sum(scores[-3:]) / 3
            older_avg = sum(scores[-6:-3]) / 3 if len(scores) >= 6 else recent_avg
            if recent_avg > older_avg + 1:
                trend = "improving"
            elif recent_avg < older_avg - 1:
                trend = "declining"
        
        return SLAResponse(
            success=True,
            data={
                "agreement_id": agreement_id,
                "period_type": period_type,
                "compliance_history": compliance_history,
                "trend_analysis": {
                    "overall_trend": trend,
                    "average_compliance": sum(h["overall_compliance"] for h in compliance_history) / len(compliance_history),
                    "best_period": max(compliance_history, key=lambda x: x["overall_compliance"]),
                    "worst_period": min(compliance_history, key=lambda x: x["overall_compliance"])
                }
            },
            message="Compliance history retrieved successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get compliance history: {str(e)}"
        )


@router.post("/agreements/{agreement_id}/activate", response_model=SLAResponse)
async def activate_sla_agreement(
    agreement_id: str,
    current_user: Customer = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Activate an SLA agreement."""
    try:
        success = await sla_service.activate_sla(agreement_id)
        
        if success:
            return SLAResponse(
                success=True,
                data={
                    "agreement_id": agreement_id,
                    "status": "active",
                    "activated_at": datetime.now(timezone.utc).isoformat()
                },
                message="SLA agreement activated successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to activate SLA agreement"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate SLA agreement: {str(e)}"
        )


@router.get("/templates/{tier}", response_model=SLAResponse)
async def get_sla_template(
    tier: str,
    current_user: Customer = Depends(get_current_user)
):
    """Get SLA template for a specific tier."""
    try:
        # Validate tier
        try:
            sla_tier = SLATier(tier.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid SLA tier: {tier}"
            )
        
        # Get template
        template = sla_service.predefined_slas[sla_tier]
        
        # Convert to dictionary for JSON response
        template_data = {
            "tier": template.tier.value,
            "name": template.name,
            "description": template.description,
            "metrics": [
                {
                    "metric_id": m.metric_id,
                    "name": m.name,
                    "description": m.description,
                    "type": m.type.value,
                    "target_value": m.target_value,
                    "measurement_unit": m.measurement_unit,
                    "measurement_period": m.measurement_period,
                    "threshold_warning": m.threshold_warning,
                    "threshold_critical": m.threshold_critical
                } for m in template.metrics
            ],
            "penalties": [
                {
                    "penalty_id": p.penalty_id,
                    "name": p.name,
                    "description": p.description,
                    "trigger_condition": p.trigger_condition,
                    "penalty_type": p.penalty_type,
                    "penalty_amount": p.penalty_amount,
                    "penalty_unit": p.penalty_unit,
                    "max_penalty_per_period": p.max_penalty_per_period
                } for p in template.penalties
            ],
            "notifications": [
                {
                    "notification_id": n.notification_id,
                    "trigger_condition": n.trigger_condition,
                    "notification_type": n.notification_type,
                    "recipients": n.recipients,
                    "template": n.template,
                    "escalation_delay": n.escalation_delay
                } for n in template.notifications
            ],
            "terms_and_conditions": template.terms_and_conditions
        }
        
        return SLAResponse(
            success=True,
            data={"template": template_data},
            message="SLA template retrieved successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get SLA template: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint for SLA management service."""
    return {
        "status": "healthy",
        "service": "sla-management",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0"
    }


async def _process_sla_agreement(agreement_id: str):
    """Background task to process SLA agreement."""
    try:
        # This would perform agreement validation, setup monitoring, etc.
        # For now, we'll simulate processing
        await asyncio.sleep(2)
        
        logger.info(
            "SLA agreement processed",
            agreement_id=agreement_id,
            processing_time="2 seconds"
        )
        
    except Exception as e:
        logger.error(
            "Failed to process SLA agreement",
            agreement_id=agreement_id,
            error=str(e)
        )