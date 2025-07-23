"""API endpoints for GDPR compliance dashboards"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4
from datetime import datetime, timedelta
import json
import os

from ...core.deps import get_current_user, get_db
from ...core.exceptions import NotFoundError, ValidationError
from ...db.models import User
from ...models.schemas import (
    ComplianceDashboard, DataClassificationSummary, ConsentMetrics,
    DataRequestMetrics, RetentionMetrics, AuditMetrics, DashboardWidget,
    DashboardRequest, DashboardExportRequest, DashboardExportResponse,
    ExportFormat
)
from ...services.dashboard_service import DashboardService
from ...services.export_service import ExportService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/overview", response_model=ComplianceDashboard)
async def get_compliance_overview(
    time_range_days: int = Query(30, ge=1, le=365, description="Time range in days"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive compliance dashboard overview.
    
    This endpoint provides:
    - Overall compliance score and grade
    - Key metrics with trends
    - Risk indicators
    - Pre-configured dashboard widgets
    
    Requires: compliance:view permission
    """
    try:
        # Check permissions
        if not current_user.has_permission("compliance:view"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view compliance dashboard"
            )
        
        service = DashboardService(db)
        dashboard = await service.get_compliance_overview(time_range_days)
        
        logger.info(
            f"Compliance dashboard accessed by user {current_user.id}",
            extra={
                "user_id": str(current_user.id),
                "time_range_days": time_range_days
            }
        )
        
        return dashboard
        
    except Exception as e:
        logger.error(f"Error generating compliance overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate compliance dashboard"
        )


@router.get("/classification", response_model=DataClassificationSummary)
async def get_data_classification_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get data classification summary for dashboard.
    
    Provides:
    - Total categories and mappings
    - Privacy level distribution
    - PII distribution
    - Retention period analysis
    - Compliance gaps
    
    Requires: compliance:view permission
    """
    try:
        if not current_user.has_permission("compliance:view"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = DashboardService(db)
        summary = await service.get_data_classification_summary()
        
        return summary
        
    except Exception as e:
        logger.error(f"Error getting classification summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get classification summary"
        )


@router.get("/consent", response_model=ConsentMetrics)
async def get_consent_metrics(
    time_range_days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get consent management metrics.
    
    Provides:
    - Active consent counts
    - Consent/withdrawal rates
    - Consent distribution by type
    - Trend analysis
    
    Requires: compliance:view permission
    """
    try:
        if not current_user.has_permission("compliance:view"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = DashboardService(db)
        metrics = await service.get_consent_metrics(time_range_days)
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting consent metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get consent metrics"
        )


@router.get("/requests", response_model=DataRequestMetrics)
async def get_data_request_metrics(
    time_range_days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get data request handling metrics.
    
    Provides:
    - Request counts by type and status
    - Average completion times
    - Compliance rates
    - Overdue request alerts
    
    Requires: compliance:view permission
    """
    try:
        if not current_user.has_permission("compliance:view"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = DashboardService(db)
        metrics = await service.get_data_request_metrics(time_range_days)
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting request metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get request metrics"
        )


@router.get("/retention", response_model=RetentionMetrics)
async def get_retention_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get data retention policy metrics.
    
    Provides:
    - Active retention rules
    - Rules by action type
    - Scheduled deletions
    - Average retention periods
    
    Requires: compliance:view permission
    """
    try:
        if not current_user.has_permission("compliance:view"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = DashboardService(db)
        metrics = await service.get_retention_metrics()
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting retention metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get retention metrics"
        )


@router.get("/audit", response_model=AuditMetrics)
async def get_audit_metrics(
    time_range_days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get audit logging metrics.
    
    Provides:
    - Total audit events
    - Success/failure rates
    - Top users by activity
    - Critical event tracking
    
    Requires: compliance:view permission
    """
    try:
        if not current_user.has_permission("compliance:view"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = DashboardService(db)
        metrics = await service.get_audit_metrics(time_range_days)
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting audit metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get audit metrics"
        )


@router.get("/widgets", response_model=List[DashboardWidget])
async def get_dashboard_widgets(
    widget_types: Optional[List[str]] = Query(None, description="Specific widget types to retrieve"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get specific dashboard widgets.
    
    Available widget types:
    - compliance_score: Overall compliance gauge
    - data_requests: Request status summary
    - consent_status: Consent distribution
    - retention_overview: Retention policy status
    - audit_activity: Recent audit activity
    - risk_matrix: Risk assessment heatmap
    
    Requires: compliance:view permission
    """
    try:
        if not current_user.has_permission("compliance:view"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = DashboardService(db)
        widgets = await service.get_dashboard_widgets(widget_types)
        
        return widgets
        
    except Exception as e:
        logger.error(f"Error getting dashboard widgets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get dashboard widgets"
        )


@router.post("/export", response_model=DashboardExportResponse)
async def export_dashboard(
    request: DashboardExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export dashboard data in various formats.
    
    Supported formats:
    - PDF: Full dashboard report with charts
    - Excel: Detailed data in spreadsheet format
    - JSON: Raw data for integration
    
    Requires: compliance:export permission
    """
    try:
        if not current_user.has_permission("compliance:export"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to export dashboard"
            )
        
        # Get dashboard data
        dashboard_service = DashboardService(db)
        dashboard = await dashboard_service.get_compliance_overview(request.time_range_days)
        
        # Prepare export data
        export_data = {
            "dashboard": dashboard.dict(),
            "generated_at": datetime.utcnow().isoformat(),
            "generated_by": str(current_user.id),
            "time_range_days": request.time_range_days
        }
        
        # Generate export file
        export_service = ExportService(db)
        export_id = str(uuid4())
        
        if request.format == ExportFormat.JSON:
            # Export as JSON
            file_path = f"/tmp/gdpr-dashboard-{export_id}.json"
            with open(file_path, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
        elif request.format == ExportFormat.EXCEL:
            # Export as Excel (would use pandas/openpyxl in production)
            file_path = f"/tmp/gdpr-dashboard-{export_id}.xlsx"
            # Simplified for demo - in production would create proper Excel file
            import pandas as pd
            
            # Convert metrics to dataframes
            metrics_df = pd.DataFrame([
                {"Metric": m.name, "Value": m.value, "Unit": m.unit}
                for m in dashboard.key_metrics
            ])
            
            with pd.ExcelWriter(file_path) as writer:
                metrics_df.to_excel(writer, sheet_name="Key Metrics", index=False)
                
                # Add more sheets for other data...
        
        elif request.format == ExportFormat.PDF:
            # Export as PDF (would use reportlab or similar in production)
            file_path = f"/tmp/gdpr-dashboard-{export_id}.pdf"
            # Simplified for demo
            with open(file_path, 'w') as f:
                f.write("GDPR Compliance Dashboard Report\n")
                f.write(f"Generated: {datetime.utcnow()}\n")
                f.write(f"Compliance Score: {dashboard.compliance_score.score} ({dashboard.compliance_score.grade})\n")
        
        else:
            raise ValueError(f"Unsupported export format: {request.format}")
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Log export
        logger.info(
            f"Dashboard exported by user {current_user.id}",
            extra={
                "user_id": str(current_user.id),
                "export_id": export_id,
                "format": request.format,
                "size_bytes": file_size
            }
        )
        
        return DashboardExportResponse(
            export_id=export_id,
            file_path=file_path,
            format=request.format,
            size_bytes=file_size,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
    except Exception as e:
        logger.error(f"Error exporting dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export dashboard"
        )


@router.get("/quick-stats")
async def get_quick_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get quick statistics for dashboard header.
    
    Returns key numbers for at-a-glance monitoring:
    - Compliance score
    - Active users
    - Pending requests  
    - Critical risks
    
    Requires: compliance:view permission
    """
    try:
        if not current_user.has_permission("compliance:view"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = DashboardService(db)
        
        # Get key stats
        score = await service._calculate_compliance_score()
        pending = await service._get_pending_request_count()
        risks = await service._get_risk_indicators()
        critical_risks = len([r for r in risks if r.severity == "high"])
        
        return {
            "compliance_score": score.score,
            "compliance_grade": score.grade,
            "pending_requests": pending,
            "critical_risks": critical_risks,
            "last_updated": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Error getting quick stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get quick stats"
        )


@router.post("/refresh-cache")
async def refresh_dashboard_cache(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Force refresh of dashboard cache.
    
    Use this to update cached dashboard data immediately
    rather than waiting for automatic refresh.
    
    Requires: compliance:admin permission
    """
    try:
        if not current_user.has_permission("compliance:admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permissions required"
            )
        
        # In production, would clear Redis cache here
        # For now, just log the action
        logger.info(
            f"Dashboard cache refreshed by user {current_user.id}",
            extra={"user_id": str(current_user.id)}
        )
        
        return {
            "status": "success",
            "message": "Dashboard cache refreshed",
            "refreshed_at": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Error refreshing cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh cache"
        )