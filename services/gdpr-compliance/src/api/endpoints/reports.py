"""GDPR Compliance Reporting API Endpoints"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime, timedelta
import io

from ...models.schemas import (
    AuditReportRequest, AuditReportResponse,
    AuditReportType, AuditReportFormat,
    ComplianceTrend, ComplianceScoreCard,
    RiskAssessment, AuditReportSchedule
)
from ...services.audit_reporting_service import AuditReportingService
from ...core.exceptions import ReportGenerationError
from ..dependencies import get_db, require_admin

router = APIRouter()


@router.post("/generate", response_model=AuditReportResponse)
async def generate_report(
    request: AuditReportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """
    Generate a comprehensive GDPR compliance report.
    
    Report types:
    - compliance_overview: Overall GDPR compliance status
    - user_activity: User activity analysis
    - data_requests: Data request handling metrics
    - consent_analysis: Consent management analysis
    - risk_assessment: Compliance risk identification
    - incident_log: Security and compliance incidents
    """
    reporting_service = AuditReportingService(db)
    
    try:
        report = await reporting_service.generate_report(
            report_type=request.report_type,
            start_date=request.start_date,
            end_date=request.end_date,
            filters=request.filters,
            format=request.format
        )
        
        # If email requested, send in background
        if request.email_to:
            background_tasks.add_task(
                send_report_email,
                report,
                request.email_to,
                current_user["email"]
            )
        
        return report
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ReportGenerationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/compliance-score", response_model=ComplianceScoreCard)
async def get_compliance_score(
    start_date: Optional[datetime] = Query(None, description="Score calculation start date"),
    end_date: Optional[datetime] = Query(None, description="Score calculation end date"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Get current GDPR compliance score with detailed breakdown"""
    # Default to last 30 days
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    reporting_service = AuditReportingService(db)
    return await reporting_service._calculate_compliance_score(start_date, end_date)


@router.get("/trends", response_model=List[ComplianceTrend])
async def get_compliance_trends(
    months: int = Query(6, ge=1, le=24, description="Number of months to analyze"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Get compliance trends over time for dashboard visualization"""
    reporting_service = AuditReportingService(db)
    return await reporting_service.generate_compliance_trends(months)


@router.get("/risks", response_model=List[RiskAssessment])
async def get_compliance_risks(
    severity: Optional[str] = Query(None, regex="^(critical|high|medium|low)$"),
    category: Optional[str] = Query(None),
    resolved: Optional[bool] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Get identified compliance risks with filtering options"""
    # Default to last 90 days for risk assessment
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=90)
    
    reporting_service = AuditReportingService(db)
    risks = await reporting_service._identify_top_risks(start_date, end_date, limit)
    
    # Apply filters
    if severity:
        risks = [r for r in risks if r.severity == severity]
    if category:
        risks = [r for r in risks if r.category == category]
    if resolved is not None:
        risks = [r for r in risks if r.resolved == resolved]
    
    return risks[:limit]


@router.get("/quick-stats", response_model=Dict[str, Any])
async def get_quick_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Get quick compliance statistics for dashboard"""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)  # Last 7 days
    
    reporting_service = AuditReportingService(db)
    
    # Get various metrics
    event_stats = await reporting_service._get_event_statistics(start_date, end_date)
    compliance_score = await reporting_service._calculate_compliance_score(start_date, end_date)
    request_metrics = await reporting_service._get_data_request_metrics(start_date, end_date)
    consent_metrics = await reporting_service._get_consent_metrics(start_date, end_date)
    risks = await reporting_service._identify_top_risks(start_date, end_date, 3)
    
    return {
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        "compliance_score": compliance_score.overall_score,
        "compliance_grade": compliance_score.grade,
        "total_events": event_stats["total_events"],
        "success_rate": event_stats["success_rate"],
        "active_data_requests": request_metrics["total_requests"],
        "average_response_time_hours": request_metrics["average_response_time_hours"],
        "active_consents": consent_metrics["active_consents"],
        "consent_withdrawal_rate": consent_metrics["withdrawal_rate"],
        "high_priority_risks": len([r for r in risks if r.severity in ["critical", "high"]]),
        "total_risks": len(risks)
    }


@router.get("/export/{report_type}", response_class=Response)
async def export_report(
    report_type: AuditReportType,
    format: AuditReportFormat = Query(AuditReportFormat.PDF),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Export a report in the specified format"""
    # Default date range
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    reporting_service = AuditReportingService(db)
    
    try:
        report = await reporting_service.generate_report(
            report_type=report_type,
            start_date=start_date,
            end_date=end_date,
            format=format
        )
        
        # Determine content type
        content_types = {
            AuditReportFormat.CSV: "text/csv",
            AuditReportFormat.PDF: "application/pdf",
            AuditReportFormat.EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            AuditReportFormat.JSON: "application/json"
        }
        
        # Generate filename
        filename = f"gdpr_{report_type.value}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.{format.value}"
        
        # Return file response
        return Response(
            content=report.file_content or report.data,
            media_type=content_types[format],
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export report: {str(e)}"
        )


@router.post("/schedule", response_model=AuditReportSchedule)
async def schedule_report(
    schedule: AuditReportSchedule,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Schedule automated report generation"""
    # In production, this would save the schedule to database
    # and set up a scheduled task
    
    # For now, return the schedule with generated ID
    schedule.schedule_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    schedule.next_run = calculate_next_run(schedule.frequency)
    
    return schedule


@router.get("/schedules", response_model=List[AuditReportSchedule])
async def list_scheduled_reports(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """List all scheduled reports"""
    # In production, this would query from database
    # For now, return empty list
    return []


@router.delete("/schedule/{schedule_id}")
async def delete_scheduled_report(
    schedule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Delete a scheduled report"""
    # In production, this would delete from database
    return {"message": "Schedule deleted successfully"}


# Helper functions
async def send_report_email(
    report: AuditReportResponse,
    recipients: List[str],
    sender: str
):
    """Send report via email (placeholder)"""
    # In production, this would use email service
    pass


def calculate_next_run(frequency: str) -> datetime:
    """Calculate next run time based on frequency"""
    now = datetime.utcnow()
    
    if frequency == "daily":
        return now + timedelta(days=1)
    elif frequency == "weekly":
        return now + timedelta(weeks=1)
    elif frequency == "monthly":
        return now + timedelta(days=30)
    elif frequency == "quarterly":
        return now + timedelta(days=90)
    else:
        return now + timedelta(days=1)