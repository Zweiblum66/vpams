"""Audit Log API Endpoints"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime, timedelta

from ...models.schemas import (
    AuditLogQuery, AuditLogResponse,
    AuditReportRequest, AuditReportResponse,
    AuditReportType, AuditReportFormat,
    ComplianceTrend
)
from ...services.audit_service import AuditService
from ...services.audit_reporting_service import AuditReportingService
from ..dependencies import get_db, get_current_user, require_admin

router = APIRouter()


@router.get("/", response_model=List[AuditLogResponse])
async def query_audit_logs(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    actor_id: Optional[UUID] = Query(None, description="Filter by actor ID"),
    subject_user_id: Optional[UUID] = Query(None, description="Filter by subject user ID"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    limit: int = Query(50, ge=1, le=1000, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Query audit logs (admin can see all, users can see their own)"""
    # Build query
    query_params = AuditLogQuery(
        event_type=event_type,
        actor_id=actor_id,
        subject_user_id=subject_user_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )
    
    # Non-admins can only see their own logs
    if "admin" not in current_user.get("roles", []):
        user_id = UUID(current_user["user_id"])
        # Override filters to only show user's own logs
        if actor_id and actor_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot view audit logs for other users"
            )
        if subject_user_id and subject_user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot view audit logs for other users"
            )
        
        # Set filters to user's ID if not already set
        if not actor_id and not subject_user_id:
            query_params.subject_user_id = user_id
    
    audit_service = AuditService(db)
    return await audit_service.query_logs(query_params)


@router.get("/user/{user_id}/activity", response_model=Dict[str, Any])
async def get_user_activity_report(
    user_id: UUID,
    start_date: Optional[datetime] = Query(None, description="Report start date"),
    end_date: Optional[datetime] = Query(None, description="Report end date"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get activity report for a user"""
    # Validate access
    if str(user_id) != current_user["user_id"] and \
       "admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view activity report for another user"
        )
    
    audit_service = AuditService(db)
    return await audit_service.get_user_activity_report(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date
    )


@router.get("/event-types", response_model=List[str])
async def get_event_types(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all available audit event types"""
    # This would typically query distinct event types from the database
    # For now, return a static list
    return [
        "consent",
        "data_request",
        "data_export",
        "data_deletion",
        "anonymization",
        "privacy_policy",
        "access_control",
        "configuration_change",
        "security_event"
    ]


@router.get("/stats", response_model=Dict[str, Any])
async def get_audit_statistics(
    start_date: Optional[datetime] = Query(None, description="Statistics start date"),
    end_date: Optional[datetime] = Query(None, description="Statistics end date"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Get audit log statistics (admin only)"""
    # Default to last 30 days if no dates provided
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    reporting_service = AuditReportingService(db)
    event_stats = await reporting_service._get_event_statistics(start_date, end_date)
    
    return {
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        "total_events": event_stats["total_events"],
        "events_by_type": event_stats["events_by_type"],
        "events_by_day": event_stats["daily_distribution"],
        "success_rate": event_stats["success_rate"],
        "failed_operations": event_stats["failed_events"],
        "peak_day": event_stats["peak_day"]
    }


@router.post("/export", response_model=Dict[str, str])
async def export_audit_logs(
    query: AuditLogQuery,
    export_format: str = Query("csv", regex="^(csv|json|excel)$"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Export audit logs (admin only)"""
    # This would generate an export file
    # For now, return a mock response
    
    export_id = "AUDIT-EXPORT-20240115-123456"
    
    return {
        "export_id": export_id,
        "status": "processing",
        "format": export_format,
        "download_url": f"/api/v1/audit/export/{export_id}/download"
    }


@router.post("/reports/generate", response_model=AuditReportResponse)
async def generate_audit_report(
    request: AuditReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Generate a comprehensive audit report"""
    reporting_service = AuditReportingService(db)
    
    try:
        report = await reporting_service.generate_report(
            report_type=request.report_type,
            start_date=request.start_date,
            end_date=request.end_date,
            filters=request.filters,
            format=request.format
        )
        
        # If file format, set up download
        if request.format != AuditReportFormat.JSON:
            # In production, this would save to storage and return a download URL
            report.file_name = f"gdpr_report_{request.report_type.value}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{request.format.value}"
            report.download_url = f"/api/v1/audit/reports/{report.report_id}/download"
        
        return report
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}"
        )


@router.get("/reports/{report_id}/download")
async def download_audit_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Download a generated audit report"""
    # In production, this would retrieve the report from storage
    # For now, return a placeholder response
    
    return Response(
        content=b"Report content here",
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename=report_{report_id}.pdf"
        }
    )


@router.get("/reports/compliance-trends", response_model=List[ComplianceTrend])
async def get_compliance_trends(
    months: int = Query(6, ge=1, le=24, description="Number of months to analyze"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Get compliance trends over time"""
    reporting_service = AuditReportingService(db)
    return await reporting_service.generate_compliance_trends(months)


@router.get("/reports/compliance-overview", response_model=Dict[str, Any])
async def get_compliance_overview(
    start_date: Optional[datetime] = Query(None, description="Report start date"),
    end_date: Optional[datetime] = Query(None, description="Report end date"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Get a quick compliance overview"""
    # Default to last 30 days
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    reporting_service = AuditReportingService(db)
    
    # Generate compliance overview
    overview = await reporting_service._generate_compliance_overview(
        start_date, end_date, None
    )
    
    return overview


@router.get("/reports/risk-assessment", response_model=List[Dict[str, Any]])
async def get_risk_assessment(
    start_date: Optional[datetime] = Query(None, description="Assessment start date"),
    end_date: Optional[datetime] = Query(None, description="Assessment end date"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of risks to return"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Get current compliance risks"""
    # Default to last 90 days
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=90)
    
    reporting_service = AuditReportingService(db)
    
    # Get top risks
    risks = await reporting_service._identify_top_risks(start_date, end_date, limit)
    
    # Convert to dict for response
    return [
        {
            "risk_id": risk.risk_id,
            "category": risk.category,
            "severity": risk.severity,
            "description": risk.description,
            "impact": risk.impact,
            "likelihood": risk.likelihood,
            "mitigation": risk.mitigation,
            "detected_at": risk.detected_at.isoformat()
        }
        for risk in risks
    ]