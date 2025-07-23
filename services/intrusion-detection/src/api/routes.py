"""API routes for Intrusion Detection Service"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc

from src.db.base import get_db
from src.models.db_models import (
    IntrusionEvent, SecurityAlert, ThreatIntelligence,
    FileIntegrityRecord, SystemActivity, NetworkBaseline
)
from src.models.schemas import (
    IntrusionEventResponse, IntrusionEventCreate,
    SecurityAlertResponse, SecurityAlertUpdate,
    ThreatIntelResponse, ThreatIntelCreate,
    SystemMetricsResponse, NetworkStatsResponse
)
from src.core.security import get_current_user
from src.services.detection_service import DetectionService
from src.services.alert_service import AlertService
from src.services.network_monitor import NetworkMonitor

# Create router
router = APIRouter(prefix="/api/v1", tags=["intrusion-detection"])

# Service instances (would be dependency injected in production)
detection_service = DetectionService()
alert_service = AlertService()
network_monitor = None  # Initialized in startup


# Health check
@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "intrusion-detection",
        "timestamp": datetime.utcnow().isoformat()
    }


# Intrusion Events endpoints
@router.get("/events", response_model=List[IntrusionEventResponse])
async def get_intrusion_events(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    severity: Optional[str] = None,
    event_type: Optional[str] = None,
    source_ip: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
):
    """Get intrusion events with filtering"""
    query = select(IntrusionEvent)
    
    # Apply filters
    conditions = []
    if severity:
        conditions.append(IntrusionEvent.severity == severity)
    if event_type:
        conditions.append(IntrusionEvent.event_type == event_type)
    if source_ip:
        conditions.append(IntrusionEvent.source_ip == source_ip)
    if start_time:
        conditions.append(IntrusionEvent.timestamp >= start_time)
    if end_time:
        conditions.append(IntrusionEvent.timestamp <= end_time)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Order by timestamp descending
    query = query.order_by(desc(IntrusionEvent.timestamp))
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    events = result.scalars().all()
    
    return events


@router.get("/events/{event_id}", response_model=IntrusionEventResponse)
async def get_intrusion_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get specific intrusion event"""
    result = await db.execute(
        select(IntrusionEvent).where(IntrusionEvent.id == event_id)
    )
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intrusion event not found"
        )
    
    return event


# Security Alerts endpoints
@router.get("/alerts", response_model=List[SecurityAlertResponse])
async def get_security_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None,
    severity: Optional[str] = None,
    assigned_to: Optional[str] = None
):
    """Get security alerts with filtering"""
    query = select(SecurityAlert)
    
    # Apply filters
    conditions = []
    if status:
        conditions.append(SecurityAlert.status == status)
    if severity:
        conditions.append(SecurityAlert.severity == severity)
    if assigned_to:
        conditions.append(SecurityAlert.assigned_to == assigned_to)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Order by created_at descending
    query = query.order_by(desc(SecurityAlert.created_at))
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    alerts = result.scalars().all()
    
    return alerts


@router.get("/alerts/{alert_id}", response_model=SecurityAlertResponse)
async def get_security_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get specific security alert with related events"""
    result = await db.execute(
        select(SecurityAlert).where(SecurityAlert.id == alert_id)
    )
    alert = result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Security alert not found"
        )
    
    return alert


@router.patch("/alerts/{alert_id}", response_model=SecurityAlertResponse)
async def update_security_alert(
    alert_id: str,
    alert_update: SecurityAlertUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update security alert status or assignment"""
    result = await db.execute(
        select(SecurityAlert).where(SecurityAlert.id == alert_id)
    )
    alert = result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Security alert not found"
        )
    
    # Update fields
    update_data = alert_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(alert, field, value)
    
    # Set resolved timestamp if status is resolved
    if alert_update.status == "resolved" and not alert.resolved_at:
        alert.resolved_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(alert)
    
    return alert


# Threat Intelligence endpoints
@router.get("/threat-intel", response_model=List[ThreatIntelResponse])
async def get_threat_intelligence(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    indicator_type: Optional[str] = None,
    is_active: bool = True
):
    """Get threat intelligence indicators"""
    query = select(ThreatIntelligence)
    
    # Apply filters
    conditions = [ThreatIntelligence.is_active == is_active]
    if indicator_type:
        conditions.append(ThreatIntelligence.indicator_type == indicator_type)
    
    query = query.where(and_(*conditions))
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    indicators = result.scalars().all()
    
    return indicators


@router.post("/threat-intel", response_model=ThreatIntelResponse)
async def create_threat_intel(
    threat_intel: ThreatIntelCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Add new threat intelligence indicator"""
    # Check if indicator already exists
    result = await db.execute(
        select(ThreatIntelligence).where(
            ThreatIntelligence.indicator == threat_intel.indicator
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        # Update existing indicator
        for field, value in threat_intel.dict(exclude_unset=True).items():
            setattr(existing, field, value)
        existing.last_seen = datetime.utcnow()
        indicator = existing
    else:
        # Create new indicator
        indicator = ThreatIntelligence(**threat_intel.dict())
        indicator.first_seen = datetime.utcnow()
        indicator.last_seen = datetime.utcnow()
        db.add(indicator)
    
    await db.commit()
    await db.refresh(indicator)
    
    return indicator


# System monitoring endpoints
@router.get("/system/metrics", response_model=SystemMetricsResponse)
async def get_system_metrics(
    current_user: dict = Depends(get_current_user)
):
    """Get current system metrics"""
    metrics = await detection_service.get_system_metrics()
    return SystemMetricsResponse(**metrics)


@router.get("/network/stats", response_model=NetworkStatsResponse)
async def get_network_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get network monitoring statistics"""
    if not network_monitor:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Network monitor not initialized"
        )
    
    stats = await network_monitor.analyze_traffic_patterns(db)
    return NetworkStatsResponse(**stats)


# File integrity endpoints
@router.get("/file-integrity")
async def get_file_integrity_records(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    changed_only: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get file integrity monitoring records"""
    query = select(FileIntegrityRecord)
    
    if changed_only:
        query = query.where(FileIntegrityRecord.changed == True)
    
    query = query.order_by(desc(FileIntegrityRecord.last_checked))
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    records = result.scalars().all()
    
    return records


# System activity endpoints
@router.get("/system/activities")
async def get_system_activities(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    user: Optional[str] = None,
    activity_type: Optional[str] = None,
    suspicious_only: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get system activity logs"""
    query = select(SystemActivity)
    
    # Apply filters
    conditions = []
    if user:
        conditions.append(SystemActivity.user == user)
    if activity_type:
        conditions.append(SystemActivity.activity_type == activity_type)
    if suspicious_only:
        conditions.append(SystemActivity.suspicious == True)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(desc(SystemActivity.timestamp))
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    activities = result.scalars().all()
    
    return activities


# Dashboard statistics
@router.get("/dashboard/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    time_range: str = Query("24h", regex="^(1h|6h|24h|7d|30d)$")
):
    """Get dashboard statistics"""
    # Calculate time range
    time_ranges = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30)
    }
    
    start_time = datetime.utcnow() - time_ranges[time_range]
    
    # Get event counts by severity
    severity_counts = {}
    for severity in ["critical", "high", "medium", "low"]:
        result = await db.execute(
            select(func.count(IntrusionEvent.id)).where(
                and_(
                    IntrusionEvent.severity == severity,
                    IntrusionEvent.timestamp >= start_time
                )
            )
        )
        severity_counts[severity] = result.scalar()
    
    # Get event counts by type
    result = await db.execute(
        select(
            IntrusionEvent.event_type,
            func.count(IntrusionEvent.id).label("count")
        ).where(
            IntrusionEvent.timestamp >= start_time
        ).group_by(IntrusionEvent.event_type)
    )
    event_type_counts = {row.event_type: row.count for row in result}
    
    # Get open alerts count
    result = await db.execute(
        select(func.count(SecurityAlert.id)).where(
            SecurityAlert.status == "open"
        )
    )
    open_alerts = result.scalar()
    
    # Get recent alerts
    result = await db.execute(
        select(SecurityAlert)
        .where(SecurityAlert.created_at >= start_time)
        .order_by(desc(SecurityAlert.created_at))
        .limit(10)
    )
    recent_alerts = result.scalars().all()
    
    return {
        "time_range": time_range,
        "severity_counts": severity_counts,
        "event_type_counts": event_type_counts,
        "open_alerts": open_alerts,
        "total_events": sum(severity_counts.values()),
        "recent_alerts": [
            {
                "id": str(alert.id),
                "title": alert.title,
                "severity": alert.severity,
                "created_at": alert.created_at.isoformat()
            }
            for alert in recent_alerts
        ]
    }


# Manual actions
@router.post("/actions/block-ip")
async def block_ip_address(
    ip_address: str,
    duration: int = Query(3600, ge=60, le=86400),
    reason: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Manually block an IP address"""
    # Create intrusion event for the block
    event = IntrusionEvent(
        event_type="manual_block",
        severity="high",
        source_ip=ip_address,
        description=f"IP manually blocked: {reason}",
        detection_method="manual",
        action_taken="blocked",
        blocked=True
    )
    
    db.add(event)
    await db.commit()
    
    # TODO: Implement actual IP blocking in firewall/iptables
    
    return {
        "status": "success",
        "ip_address": ip_address,
        "duration": duration,
        "reason": reason
    }


@router.post("/actions/trigger-scan")
async def trigger_security_scan(
    scan_type: str = Query(..., regex="^(full|quick|vulnerability)$"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Manually trigger a security scan"""
    # TODO: Implement actual scan triggering
    
    return {
        "status": "scan_initiated",
        "scan_type": scan_type,
        "timestamp": datetime.utcnow().isoformat()
    }