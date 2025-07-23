"""
API routes for approval dashboard functionality
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, case
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field

from ..core.auth import get_current_user
from ..db.session import get_db
from ..models.approval_models import (
    ApprovalTask, ApprovalDecision, ApprovalHistory, ApprovalMetrics
)
from ..models.approval_schemas import ApprovalStatus

router = APIRouter(prefix="/api/v1/approvals/dashboard", tags=["approval-dashboard"])


class DashboardSummary(BaseModel):
    """Dashboard summary statistics"""
    pending_count: int = 0
    approved_count: int = 0
    rejected_count: int = 0
    escalated_count: int = 0
    total_count: int = 0
    average_response_time_hours: float = 0.0
    sla_compliance_rate: float = 0.0
    pending_urgent: int = 0


class ApprovalRequestSummary(BaseModel):
    """Summary of an approval request for dashboard"""
    id: str
    title: str
    description: str
    status: str
    priority: str
    created_at: datetime
    deadline: Optional[datetime] = None
    approvers: List[Dict[str, Any]]
    requestor: Dict[str, Any]


class DashboardMetrics(BaseModel):
    """Detailed dashboard metrics"""
    weekly_trend: List[Dict[str, Any]]
    by_department: List[Dict[str, Any]]
    by_type: List[Dict[str, Any]]
    response_time_distribution: List[Dict[str, Any]]
    top_requestors: List[Dict[str, Any]]
    top_approvers: List[Dict[str, Any]]


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    user_id: Optional[str] = Query(None, description="Filter by specific user"),
    department: Optional[str] = Query(None, description="Filter by department"),
    days: int = Query(30, description="Number of days to include"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get dashboard summary statistics
    
    Returns counts and metrics for approval tasks based on filters.
    """
    try:
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Base query
        query = select(ApprovalTask).where(
            ApprovalTask.created_at >= start_date
        )
        
        # Apply filters
        if user_id:
            # Filter by tasks assigned to user or created by user
            query = query.where(
                or_(
                    ApprovalTask.created_by == user_id,
                    ApprovalTask.id.in_(
                        select(ApprovalDecision.approval_task_id).where(
                            ApprovalDecision.approver_id == user_id
                        )
                    )
                )
            )
        
        if department:
            # Filter by department (assuming it's in metadata)
            query = query.where(
                ApprovalTask.metadata["department"].astext == department
            )
        
        # Execute query
        result = await db.execute(query)
        tasks = result.scalars().all()
        
        # Calculate summary
        summary = DashboardSummary()
        total_response_time = 0
        response_count = 0
        sla_met_count = 0
        
        for task in tasks:
            summary.total_count += 1
            config = task.get_config()
            
            # Count by status
            if task.status == ApprovalStatus.PENDING:
                summary.pending_count += 1
                # Check if urgent
                if config.approval_deadline_hours:
                    deadline = task.created_at + timedelta(hours=config.approval_deadline_hours)
                    if deadline < datetime.utcnow() + timedelta(hours=24):
                        summary.pending_urgent += 1
            elif task.status == ApprovalStatus.APPROVED:
                summary.approved_count += 1
            elif task.status == ApprovalStatus.REJECTED:
                summary.rejected_count += 1
            elif task.status == ApprovalStatus.ESCALATED:
                summary.escalated_count += 1
            
            # Calculate response time for completed tasks
            if task.completed_at and task.status in [ApprovalStatus.APPROVED, ApprovalStatus.REJECTED]:
                response_time = (task.completed_at - task.created_at).total_seconds() / 3600
                total_response_time += response_time
                response_count += 1
                
                # Check SLA compliance
                if config.approval_deadline_hours:
                    if response_time <= config.approval_deadline_hours:
                        sla_met_count += 1
        
        # Calculate averages
        if response_count > 0:
            summary.average_response_time_hours = total_response_time / response_count
            summary.sla_compliance_rate = sla_met_count / response_count
        
        return summary
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/recent", response_model=List[ApprovalRequestSummary])
async def get_recent_requests(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(10, ge=1, le=50, description="Number of requests to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get recent approval requests
    
    Returns a list of recent approval requests with basic information.
    """
    try:
        # Build query
        query = select(ApprovalTask).options(
            selectinload(ApprovalTask.decisions)
        ).order_by(ApprovalTask.created_at.desc())
        
        # Apply filters
        if status:
            query = query.where(ApprovalTask.status == status)
        
        # Filter by user's approvals
        query = query.where(
            or_(
                ApprovalTask.created_by == current_user["user_id"],
                ApprovalTask.id.in_(
                    select(ApprovalDecision.approval_task_id).where(
                        ApprovalDecision.approver_id == current_user["user_id"]
                    )
                )
            )
        )
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        tasks = result.scalars().all()
        
        # Format response
        requests = []
        for task in tasks:
            config = task.get_config()
            
            # Format approvers
            approvers = []
            for approver in config.approvers:
                approver_status = "pending"
                decided_at = None
                
                # Check if this approver has made a decision
                for decision in task.decisions:
                    if decision.approver_id == approver.identifier:
                        approver_status = decision.decision
                        decided_at = decision.decided_at
                        break
                
                approvers.append({
                    "id": approver.identifier,
                    "name": approver.name,
                    "status": approver_status,
                    "decided_at": decided_at.isoformat() if decided_at else None
                })
            
            # Get priority from metadata or default
            priority = task.metadata.get("priority", "normal") if task.metadata else "normal"
            
            # Calculate deadline
            deadline = None
            if config.approval_deadline_hours:
                deadline = task.created_at + timedelta(hours=config.approval_deadline_hours)
            
            requests.append(ApprovalRequestSummary(
                id=str(task.id),
                title=config.title,
                description=config.description,
                status=task.status.value,
                priority=priority,
                created_at=task.created_at,
                deadline=deadline,
                approvers=approvers,
                requestor={
                    "id": task.created_by or "system",
                    "name": task.metadata.get("requestor_name", "Unknown") if task.metadata else "Unknown",
                    "avatar": None
                }
            ))
        
        return requests
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    days: int = Query(30, description="Number of days for metrics"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed dashboard metrics
    
    Returns various metrics for charts and analytics.
    """
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Weekly trend
        weekly_trend = []
        for i in range(7):
            day_start = end_date - timedelta(days=6-i)
            day_end = day_start + timedelta(days=1)
            
            # Count tasks by status for this day
            day_query = select(
                func.count(case((ApprovalTask.status == ApprovalStatus.PENDING, 1))).label("pending"),
                func.count(case((ApprovalTask.status == ApprovalStatus.APPROVED, 1))).label("approved"),
                func.count(case((ApprovalTask.status == ApprovalStatus.REJECTED, 1))).label("rejected")
            ).where(
                and_(
                    ApprovalTask.created_at >= day_start,
                    ApprovalTask.created_at < day_end
                )
            )
            
            result = await db.execute(day_query)
            day_data = result.first()
            
            weekly_trend.append({
                "date": day_start.date().isoformat(),
                "pending": day_data.pending or 0,
                "approved": day_data.approved or 0,
                "rejected": day_data.rejected or 0
            })
        
        # By department
        dept_query = select(
            func.coalesce(ApprovalTask.metadata["department"].astext, "Unknown").label("department"),
            func.count(ApprovalTask.id).label("count")
        ).where(
            ApprovalTask.created_at >= start_date
        ).group_by("department").order_by(func.count(ApprovalTask.id).desc()).limit(10)
        
        dept_result = await db.execute(dept_query)
        by_department = [
            {"department": row.department, "count": row.count}
            for row in dept_result
        ]
        
        # By type
        type_query = select(
            func.coalesce(ApprovalTask.metadata["approval_type"].astext, "general").label("type"),
            func.count(ApprovalTask.id).label("count")
        ).where(
            ApprovalTask.created_at >= start_date
        ).group_by("type").order_by(func.count(ApprovalTask.id).desc())
        
        type_result = await db.execute(type_query)
        by_type = [
            {"type": row.type, "count": row.count}
            for row in type_result
        ]
        
        # Response time distribution
        response_times = []
        completed_query = select(ApprovalTask).where(
            and_(
                ApprovalTask.created_at >= start_date,
                ApprovalTask.completed_at.isnot(None),
                ApprovalTask.status.in_([ApprovalStatus.APPROVED, ApprovalStatus.REJECTED])
            )
        )
        
        completed_result = await db.execute(completed_query)
        completed_tasks = completed_result.scalars().all()
        
        for task in completed_tasks:
            response_hours = (task.completed_at - task.created_at).total_seconds() / 3600
            response_times.append(response_hours)
        
        # Create distribution buckets
        response_time_distribution = [
            {"range": "< 1h", "count": sum(1 for t in response_times if t < 1)},
            {"range": "1-4h", "count": sum(1 for t in response_times if 1 <= t < 4)},
            {"range": "4-8h", "count": sum(1 for t in response_times if 4 <= t < 8)},
            {"range": "8-24h", "count": sum(1 for t in response_times if 8 <= t < 24)},
            {"range": "1-3d", "count": sum(1 for t in response_times if 24 <= t < 72)},
            {"range": "> 3d", "count": sum(1 for t in response_times if t >= 72)},
        ]
        
        # Top requestors
        requestor_query = select(
            ApprovalTask.created_by.label("user_id"),
            func.coalesce(ApprovalTask.metadata["requestor_name"].astext, "Unknown").label("name"),
            func.count(ApprovalTask.id).label("count")
        ).where(
            and_(
                ApprovalTask.created_at >= start_date,
                ApprovalTask.created_by.isnot(None)
            )
        ).group_by(
            ApprovalTask.created_by,
            ApprovalTask.metadata["requestor_name"].astext
        ).order_by(func.count(ApprovalTask.id).desc()).limit(5)
        
        requestor_result = await db.execute(requestor_query)
        top_requestors = [
            {"name": row.name, "count": row.count}
            for row in requestor_result
        ]
        
        # Top approvers
        approver_query = select(
            ApprovalDecision.approver_id.label("user_id"),
            ApprovalDecision.approver_name.label("name"),
            func.count(ApprovalDecision.id).label("count"),
            func.avg(
                func.extract("epoch", ApprovalDecision.decided_at - ApprovalTask.created_at) / 3600
            ).label("avg_response_time")
        ).join(
            ApprovalTask
        ).where(
            and_(
                ApprovalTask.created_at >= start_date,
                ApprovalDecision.decision.in_(["approved", "rejected"])
            )
        ).group_by(
            ApprovalDecision.approver_id,
            ApprovalDecision.approver_name
        ).order_by(func.count(ApprovalDecision.id).desc()).limit(5)
        
        approver_result = await db.execute(approver_query)
        top_approvers = [
            {
                "name": row.name or "Unknown",
                "count": row.count,
                "avg_response_time": float(row.avg_response_time or 0)
            }
            for row in approver_result
        ]
        
        return DashboardMetrics(
            weekly_trend=weekly_trend,
            by_department=by_department,
            by_type=by_type,
            response_time_distribution=response_time_distribution,
            top_requestors=top_requestors,
            top_approvers=top_approvers
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/my-stats")
async def get_my_approval_stats(
    days: int = Query(30, description="Number of days for stats"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get personal approval statistics
    
    Returns statistics specific to the current user.
    """
    try:
        user_id = current_user["user_id"]
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Tasks assigned to me
        assigned_query = select(func.count(ApprovalDecision.id)).where(
            and_(
                ApprovalDecision.approver_id == user_id,
                ApprovalDecision.created_at >= start_date
            )
        )
        assigned_result = await db.execute(assigned_query)
        assigned_count = assigned_result.scalar() or 0
        
        # Tasks I've completed
        completed_query = select(func.count(ApprovalDecision.id)).where(
            and_(
                ApprovalDecision.approver_id == user_id,
                ApprovalDecision.decided_at.isnot(None),
                ApprovalDecision.created_at >= start_date
            )
        )
        completed_result = await db.execute(completed_query)
        completed_count = completed_result.scalar() or 0
        
        # My average response time
        response_query = select(
            func.avg(
                func.extract("epoch", ApprovalDecision.decided_at - ApprovalDecision.created_at) / 3600
            )
        ).where(
            and_(
                ApprovalDecision.approver_id == user_id,
                ApprovalDecision.decided_at.isnot(None),
                ApprovalDecision.created_at >= start_date
            )
        )
        response_result = await db.execute(response_query)
        avg_response_time = response_result.scalar() or 0
        
        # Tasks I've created
        created_query = select(func.count(ApprovalTask.id)).where(
            and_(
                ApprovalTask.created_by == user_id,
                ApprovalTask.created_at >= start_date
            )
        )
        created_result = await db.execute(created_query)
        created_count = created_result.scalar() or 0
        
        # Pending my action
        pending_query = select(func.count(ApprovalDecision.id)).where(
            and_(
                ApprovalDecision.approver_id == user_id,
                ApprovalDecision.decided_at.is_(None),
                ApprovalDecision.created_at >= start_date
            )
        )
        pending_result = await db.execute(pending_query)
        pending_count = pending_result.scalar() or 0
        
        return {
            "assigned_to_me": assigned_count,
            "completed_by_me": completed_count,
            "pending_my_action": pending_count,
            "created_by_me": created_count,
            "avg_response_time_hours": float(avg_response_time),
            "completion_rate": completed_count / assigned_count if assigned_count > 0 else 0,
            "period_days": days
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/export")
async def export_dashboard_data(
    format: str = Query("csv", regex="^(csv|excel|pdf)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Export dashboard data
    
    Exports approval data in various formats for reporting.
    """
    try:
        # This would generate and return a file
        # For now, return a placeholder response
        return {
            "message": "Export functionality will be implemented",
            "format": format,
            "start_date": start_date,
            "end_date": end_date
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )