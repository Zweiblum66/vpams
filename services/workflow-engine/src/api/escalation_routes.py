"""
API routes for escalation management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel, Field

from ..core.auth import get_current_user
from ..db.session import get_db
from ..models.approval_models import ApprovalTask, ApprovalHistory
from ..models.approval_schemas import (
    ApprovalStatus, EscalationRule, EscalationType,
    ApproverConfig, ApproverType
)
from ..services.escalation_service import EscalationService, EscalationTrigger

router = APIRouter(prefix="/api/v1/escalations", tags=["escalations"])
escalation_service = EscalationService()


class ManualEscalationRequest(BaseModel):
    """Request for manual escalation"""
    approval_task_id: str
    reason: str
    escalate_to: ApproverConfig
    notify_message: Optional[str] = None


class EscalationRuleRequest(BaseModel):
    """Request to add/update escalation rule"""
    approval_task_id: str
    rule: EscalationRule


class SLAViolation(BaseModel):
    """SLA violation details"""
    task_id: str
    title: str
    created_at: datetime
    deadline: datetime
    hours_overdue: float
    status: str
    approvers: List[str]


class EscalationMetricsResponse(BaseModel):
    """Escalation metrics response"""
    total_escalations: int
    trigger_breakdown: Dict[str, int]
    type_breakdown: Dict[str, int]
    auto_approvals: int
    period: Dict[str, str]


@router.post("/manual")
async def trigger_manual_escalation(
    request: ManualEscalationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Manually trigger escalation for an approval task
    
    This endpoint allows authorized users to manually escalate an approval
    to a different approver with a specific reason.
    """
    try:
        # Get approval task
        result = await db.execute(
            select(ApprovalTask).where(
                and_(
                    ApprovalTask.id == request.approval_task_id,
                    ApprovalTask.status.in_([ApprovalStatus.PENDING, ApprovalStatus.IN_PROGRESS])
                )
            )
        )
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Approval task not found or not in escalatable status"
            )
        
        # Check authorization - user must be admin or involved in the approval
        config = task.get_config()
        approver_ids = [a.identifier for a in config.approvers]
        
        if (current_user["user_id"] != task.created_by and 
            current_user["user_id"] not in approver_ids and
            not current_user.get("is_admin", False)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to escalate this approval"
            )
        
        # Create manual escalation rule
        escalation_rule = EscalationRule(
            escalation_type=EscalationType.MANUAL,
            escalate_to=request.escalate_to,
            escalation_message=request.notify_message or f"Manual escalation: {request.reason}",
            escalation_action="add_approver"
        )
        
        # Execute escalation
        await escalation_service._execute_escalation(
            task, escalation_rule, EscalationTrigger.MANUAL, db
        )
        
        # Add history entry
        history_entry = ApprovalHistory(
            approval_task_id=task.id,
            action="manual_escalation",
            performed_by=current_user["user_id"],
            details={
                "reason": request.reason,
                "escalated_to": request.escalate_to.identifier,
                "message": request.notify_message
            }
        )
        db.add(history_entry)
        
        await db.commit()
        
        return {
            "success": True,
            "task_id": str(task.id),
            "escalated_to": request.escalate_to.identifier,
            "message": "Approval successfully escalated"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/rules")
async def update_escalation_rules(
    request: EscalationRuleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update escalation rules for an approval task
    
    This endpoint allows updating the escalation rules for a pending approval task.
    """
    try:
        # Get approval task
        result = await db.execute(
            select(ApprovalTask).where(
                and_(
                    ApprovalTask.id == request.approval_task_id,
                    ApprovalTask.status == ApprovalStatus.PENDING
                )
            )
        )
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Approval task not found or not pending"
            )
        
        # Check authorization
        if (current_user["user_id"] != task.created_by and
            not current_user.get("is_admin", False)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update escalation rules"
            )
        
        # Update configuration
        config = task.get_config()
        config.escalation_rules.append(request.rule)
        task.set_config(config)
        
        # Apply the new rule
        await escalation_service.apply_escalation_rules(task, [request.rule], db)
        
        await db.commit()
        
        return {
            "success": True,
            "task_id": str(task.id),
            "total_rules": len(config.escalation_rules),
            "message": "Escalation rule added successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/sla-violations", response_model=List[SLAViolation])
async def get_sla_violations(
    department: Optional[str] = Query(None, description="Filter by department"),
    hours_overdue_min: Optional[float] = Query(None, description="Minimum hours overdue"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get current SLA violations
    
    Returns a list of approval tasks that have exceeded their SLA deadlines.
    """
    try:
        violations = await escalation_service.check_sla_violations(db)
        
        # Apply filters
        if department:
            violations = [v for v in violations if v.get("department") == department]
        
        if hours_overdue_min is not None:
            violations = [v for v in violations if v["hours_overdue"] >= hours_overdue_min]
        
        return violations
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/metrics", response_model=EscalationMetricsResponse)
async def get_escalation_metrics(
    start_date: Optional[datetime] = Query(None, description="Start date for metrics"),
    end_date: Optional[datetime] = Query(None, description="End date for metrics"),
    days: Optional[int] = Query(30, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get escalation metrics
    
    Returns metrics about escalations for the specified time period.
    """
    try:
        # Calculate date range
        if not end_date:
            end_date = datetime.utcnow()
        
        if not start_date:
            start_date = end_date - timedelta(days=days)
        
        metrics = await escalation_service.get_escalation_metrics(
            start_date, end_date, db
        )
        
        return EscalationMetricsResponse(**metrics)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/history/{approval_task_id}")
async def get_escalation_history(
    approval_task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get escalation history for an approval task
    
    Returns all escalation events for the specified approval task.
    """
    try:
        # Get escalation history
        result = await db.execute(
            select(ApprovalHistory).where(
                and_(
                    ApprovalHistory.approval_task_id == approval_task_id,
                    ApprovalHistory.action.in_(["escalated", "manual_escalation"])
                )
            ).order_by(ApprovalHistory.created_at.desc())
        )
        history = result.scalars().all()
        
        return {
            "task_id": approval_task_id,
            "escalation_count": len(history),
            "history": [
                {
                    "id": str(h.id),
                    "action": h.action,
                    "performed_by": h.performed_by,
                    "details": h.details,
                    "created_at": h.created_at.isoformat()
                }
                for h in history
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/test-escalation")
async def test_escalation_rule(
    rule: EscalationRule,
    context: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """
    Test an escalation rule
    
    This endpoint allows testing escalation rules without creating an actual approval.
    """
    try:
        # Validate rule
        if rule.escalation_type == EscalationType.TIME_BASED and not rule.trigger_after_hours:
            raise ValueError("Time-based escalation requires trigger_after_hours")
        
        if rule.escalation_type == EscalationType.REJECTION_BASED and not rule.rejection_count:
            raise ValueError("Rejection-based escalation requires rejection_count")
        
        # Test conditions
        would_trigger = False
        trigger_reason = ""
        
        if rule.escalation_type == EscalationType.TIME_BASED:
            # Check if enough time has passed
            created_at = context.get("created_at", datetime.utcnow())
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)
            
            hours_pending = (datetime.utcnow() - created_at).total_seconds() / 3600
            would_trigger = hours_pending >= rule.trigger_after_hours
            trigger_reason = f"Task pending for {hours_pending:.1f} hours"
            
        elif rule.escalation_type == EscalationType.REJECTION_BASED:
            rejection_count = context.get("rejection_count", 0)
            would_trigger = rejection_count >= rule.rejection_count
            trigger_reason = f"Rejected {rejection_count} times"
        
        return {
            "rule_type": rule.escalation_type,
            "would_trigger": would_trigger,
            "trigger_reason": trigger_reason,
            "escalate_to": rule.escalate_to.identifier if rule.escalate_to else None,
            "escalation_action": rule.escalation_action
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/suggested-escalations")
async def get_suggested_escalations(
    approval_type: Optional[str] = Query(None, description="Type of approval"),
    department: Optional[str] = Query(None, description="Department"),
    urgency: Optional[str] = Query(None, description="Urgency level"),
    amount: Optional[float] = Query(None, description="Amount for expense approvals"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get suggested escalation paths
    
    Returns suggested escalation approvers based on the approval context.
    """
    try:
        suggestions = []
        
        # Time-based escalation suggestions
        if urgency in ["high", "critical"]:
            suggestions.append({
                "rule_type": "time_based",
                "trigger_after_hours": 4 if urgency == "critical" else 24,
                "escalate_to": {
                    "approver_type": "role",
                    "identifier": "ceo" if urgency == "critical" else "department_head",
                    "name": "Executive" if urgency == "critical" else "Department Head"
                },
                "reason": f"High urgency ({urgency}) requires faster escalation"
            })
        
        # Amount-based escalation for expenses
        if approval_type == "expense" and amount:
            if amount > 50000:
                suggestions.append({
                    "rule_type": "time_based",
                    "trigger_after_hours": 48,
                    "escalate_to": {
                        "approver_type": "role",
                        "identifier": "cfo",
                        "name": "Chief Financial Officer"
                    },
                    "reason": f"High-value expense (${amount:,.2f}) requires executive oversight"
                })
        
        # Department-based suggestions
        if department:
            dept_escalation_map = {
                "engineering": "cto",
                "marketing": "cmo",
                "finance": "cfo",
                "operations": "coo",
                "hr": "chro"
            }
            
            exec_role = dept_escalation_map.get(department.lower(), "ceo")
            suggestions.append({
                "rule_type": "rejection_based",
                "rejection_count": 2,
                "escalate_to": {
                    "approver_type": "role",
                    "identifier": exec_role,
                    "name": exec_role.upper()
                },
                "reason": f"Multiple rejections in {department} department escalate to executive"
            })
        
        # Default suggestion
        if not suggestions:
            suggestions.append({
                "rule_type": "time_based",
                "trigger_after_hours": 72,
                "escalate_to": {
                    "approver_type": "role",
                    "identifier": "admin",
                    "name": "Administrator"
                },
                "reason": "Default escalation after 3 days"
            })
        
        return {
            "suggestions": suggestions,
            "context": {
                "approval_type": approval_type,
                "department": department,
                "urgency": urgency,
                "amount": amount
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )