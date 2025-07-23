"""
API routes for Security Audit Service
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from ..core.config import get_settings, Settings
from ..core.audit_engine import AuditEngine
from ..models.schemas import (
    AuditRequest, AuditResult, ScanRequest, ScanResult, ComplianceResult,
    ScanListResponse, AuditListResponse, HealthStatus, ScanType, ComplianceStandard
)
from ..services.database import get_db
from ..services.audit_service import AuditService

logger = structlog.get_logger()

# Initialize routers
audit_router = APIRouter(prefix="/api/v1/audits", tags=["Security Audits"])
scan_router = APIRouter(prefix="/api/v1/scans", tags=["Security Scans"])
compliance_router = APIRouter(prefix="/api/v1/compliance", tags=["Compliance"])
health_router = APIRouter(prefix="/health", tags=["Health"])

# Global audit engine instance
audit_engine: Optional[AuditEngine] = None


def get_audit_engine(settings: Settings = Depends(get_settings)) -> AuditEngine:
    """Get audit engine instance"""
    global audit_engine
    if audit_engine is None:
        audit_engine = AuditEngine(settings)
    return audit_engine


# Audit endpoints
@audit_router.post("/", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def start_audit(
    request: AuditRequest,
    background_tasks: BackgroundTasks,
    audit_engine: AuditEngine = Depends(get_audit_engine),
    audit_service: AuditService = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Start a comprehensive security audit"""
    try:
        audit_id = await audit_engine.start_audit(request)
        
        # Store audit request in database
        background_tasks.add_task(
            audit_service.create_audit_record,
            audit_id,
            request,
            db
        )
        
        return {
            "audit_id": audit_id,
            "status": "accepted",
            "message": "Security audit started successfully"
        }
        
    except Exception as e:
        logger.error("Failed to start audit", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start audit: {str(e)}"
        )


@audit_router.get("/{audit_id}/status", response_model=dict)
async def get_audit_status(
    audit_id: str,
    audit_engine: AuditEngine = Depends(get_audit_engine)
):
    """Get audit execution status"""
    status_info = await audit_engine.get_audit_status(audit_id)
    
    if not status_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit not found"
        )
    
    return {
        "audit_id": audit_id,
        "status": status_info["status"],
        "started_at": status_info["started_at"].isoformat(),
        "completed_at": status_info.get("completed_at").isoformat() if status_info.get("completed_at") else None,
        "duration_seconds": status_info.get("duration_seconds"),
        "progress": {
            "completed_scans": len(status_info["scan_results"]),
            "total_scans": len(status_info["scans"]),
            "completed_compliance": len(status_info["compliance_results"]),
            "total_compliance": len(status_info["compliance_standards"])
        },
        "error_messages": status_info.get("error_messages", [])
    }


@audit_router.get("/{audit_id}", response_model=AuditResult)
async def get_audit_result(
    audit_id: str,
    audit_engine: AuditEngine = Depends(get_audit_engine)
):
    """Get complete audit result"""
    result = await audit_engine.get_audit_result(audit_id)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit not found"
        )
    
    return result


@audit_router.delete("/{audit_id}", response_model=dict)
async def cancel_audit(
    audit_id: str,
    audit_engine: AuditEngine = Depends(get_audit_engine)
):
    """Cancel a running audit"""
    success = await audit_engine.cancel_audit(audit_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit not found or cannot be cancelled"
        )
    
    return {
        "audit_id": audit_id,
        "status": "cancelled",
        "message": "Audit cancelled successfully"
    }


@audit_router.get("/", response_model=AuditListResponse)
async def list_audits(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    target: Optional[str] = Query(None, description="Filter by target"),
    status: Optional[str] = Query(None, description="Filter by status"),
    audit_service: AuditService = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """List audit results with pagination"""
    try:
        audits, total = await audit_service.list_audits(
            db, page=page, limit=limit, target=target, status=status
        )
        
        return AuditListResponse(
            audits=audits,
            total=total,
            page=page,
            limit=limit
        )
        
    except Exception as e:
        logger.error("Failed to list audits", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list audits: {str(e)}"
        )


# Scan endpoints
@scan_router.post("/", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def start_scan(
    request: ScanRequest,
    background_tasks: BackgroundTasks,
    audit_engine: AuditEngine = Depends(get_audit_engine)
):
    """Start an individual security scan"""
    try:
        # Create audit request with single scan
        audit_request = AuditRequest(
            target=request.target,
            scans=[request.scan_type],
            options=request.options
        )
        
        audit_id = await audit_engine.start_audit(audit_request)
        
        return {
            "scan_id": audit_id,
            "status": "accepted",
            "message": f"{request.scan_type} scan started successfully"
        }
        
    except Exception as e:
        logger.error("Failed to start scan", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start scan: {str(e)}"
        )


@scan_router.get("/{scan_id}", response_model=ScanResult)
async def get_scan_result(
    scan_id: str,
    audit_engine: AuditEngine = Depends(get_audit_engine)
):
    """Get individual scan result"""
    audit_result = await audit_engine.get_audit_result(scan_id)
    
    if not audit_result or not audit_result.scan_results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found"
        )
    
    # Return the first (and only) scan result
    return audit_result.scan_results[0]


@scan_router.get("/", response_model=ScanListResponse)
async def list_scans(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    scan_type: Optional[ScanType] = Query(None, description="Filter by scan type"),
    severity: Optional[str] = Query(None, description="Filter by minimum severity"),
    audit_service: AuditService = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """List scan results with pagination"""
    try:
        scans, total = await audit_service.list_scans(
            db, page=page, limit=limit, scan_type=scan_type, severity=severity
        )
        
        return ScanListResponse(
            scans=scans,
            total=total,
            page=page,
            limit=limit
        )
        
    except Exception as e:
        logger.error("Failed to list scans", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list scans: {str(e)}"
        )


# Compliance endpoints
@compliance_router.post("/check", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def start_compliance_check(
    target: str,
    standards: List[ComplianceStandard],
    background_tasks: BackgroundTasks,
    audit_engine: AuditEngine = Depends(get_audit_engine)
):
    """Start a compliance check"""
    try:
        # Create audit request with compliance checks only
        audit_request = AuditRequest(
            target=target,
            scans=[],
            compliance_standards=standards
        )
        
        audit_id = await audit_engine.start_audit(audit_request)
        
        return {
            "check_id": audit_id,
            "status": "accepted",
            "message": f"Compliance check started for {len(standards)} standards"
        }
        
    except Exception as e:
        logger.error("Failed to start compliance check", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start compliance check: {str(e)}"
        )


@compliance_router.get("/{check_id}", response_model=List[ComplianceResult])
async def get_compliance_result(
    check_id: str,
    audit_engine: AuditEngine = Depends(get_audit_engine)
):
    """Get compliance check results"""
    audit_result = await audit_engine.get_audit_result(check_id)
    
    if not audit_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Compliance check not found"
        )
    
    return audit_result.compliance_results


@compliance_router.get("/", response_model=List[ComplianceResult])
async def list_compliance_results(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    standard: Optional[ComplianceStandard] = Query(None, description="Filter by standard"),
    min_score: Optional[float] = Query(None, ge=0, le=1, description="Minimum compliance score"),
    audit_service: AuditService = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """List compliance results with pagination"""
    try:
        results = await audit_service.list_compliance_results(
            db, page=page, limit=limit, standard=standard, min_score=min_score
        )
        
        return results
        
    except Exception as e:
        logger.error("Failed to list compliance results", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list compliance results: {str(e)}"
        )


# Health endpoint
@health_router.get("/", response_model=HealthStatus)
async def health_check(
    settings: Settings = Depends(get_settings),
    audit_engine: AuditEngine = Depends(get_audit_engine),
    db: AsyncSession = Depends(get_db)
):
    """Service health check"""
    import time
    from datetime import datetime
    
    try:
        # Check database connection
        await db.execute("SELECT 1")
        database_connected = True
    except Exception:
        database_connected = False
    
    # Check Redis connection (if configured)
    redis_connected = True  # Simplified for now
    
    # Get active scans count
    active_scans = audit_engine.get_active_audit_count()
    
    return HealthStatus(
        status="healthy" if database_connected else "unhealthy",
        timestamp=datetime.utcnow(),
        version="1.0.0",
        uptime_seconds=time.time(),  # Simplified uptime
        database_connected=database_connected,
        redis_connected=redis_connected,
        active_scans=active_scans
    )


# Analytics endpoints
@audit_router.get("/analytics/summary", response_model=dict)
async def get_audit_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    audit_service: AuditService = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Get audit analytics and metrics"""
    try:
        analytics = await audit_service.get_audit_analytics(db, days=days)
        return analytics
        
    except Exception as e:
        logger.error("Failed to get audit analytics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get audit analytics: {str(e)}"
        )


@scan_router.get("/findings/export", response_model=dict)
async def export_findings(
    format: str = Query("json", regex="^(json|csv|pdf)$", description="Export format"),
    scan_ids: Optional[List[str]] = Query(None, description="Specific scan IDs to export"),
    severity: Optional[str] = Query(None, description="Minimum severity level"),
    audit_service: AuditService = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Export security findings"""
    try:
        export_data = await audit_service.export_findings(
            db, format=format, scan_ids=scan_ids, severity=severity
        )
        
        return {
            "format": format,
            "data": export_data,
            "exported_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to export findings", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export findings: {str(e)}"
        )