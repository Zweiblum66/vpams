"""
Escalation service for handling approval escalations
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, update
import asyncio
from enum import Enum

from ..models.approval_schemas import (
    ApprovalStatus, EscalationRule, EscalationType,
    ApproverConfig, ApproverType, NotificationPriority
)
from ..models.approval_models import ApprovalTask, ApprovalHistory
from ..core.exceptions import WorkflowException
from ..services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class EscalationTrigger(Enum):
    """Escalation trigger events"""
    TIME_EXPIRED = "time_expired"
    REJECTION = "rejection"
    CONDITION_MET = "condition_met"
    MANUAL = "manual"
    AUTO_APPROVAL_TIMEOUT = "auto_approval_timeout"


class EscalationService:
    """Service for managing approval escalations"""
    
    def __init__(self):
        self.notification_service = NotificationService()
        self.escalation_monitors: Dict[str, asyncio.Task] = {}
        
    async def apply_escalation_rules(
        self,
        approval_task: ApprovalTask,
        rules: List[EscalationRule],
        db: AsyncSession
    ) -> None:
        """
        Apply escalation rules to an approval task
        
        Args:
            approval_task: The approval task
            rules: List of escalation rules to apply
            db: Database session
        """
        try:
            for rule in rules:
                if rule.escalation_type == EscalationType.TIME_BASED:
                    await self._schedule_time_based_escalation(
                        approval_task, rule, db
                    )
                elif rule.escalation_type == EscalationType.CONDITION_BASED:
                    await self._setup_condition_monitoring(
                        approval_task, rule, db
                    )
                elif rule.escalation_type == EscalationType.REJECTION_BASED:
                    # Rejection-based escalation is handled when rejection occurs
                    logger.info(
                        f"Rejection-based escalation configured for task {approval_task.id}"
                    )
                    
        except Exception as e:
            logger.error(f"Failed to apply escalation rules: {e}")
            raise WorkflowException(f"Failed to apply escalation rules: {e}")
    
    async def _schedule_time_based_escalation(
        self,
        approval_task: ApprovalTask,
        rule: EscalationRule,
        db: AsyncSession
    ) -> None:
        """Schedule time-based escalation"""
        task_id = str(approval_task.id)
        
        # Cancel existing monitor if any
        if task_id in self.escalation_monitors:
            self.escalation_monitors[task_id].cancel()
        
        # Create monitoring task
        monitor_task = asyncio.create_task(
            self._monitor_time_escalation(approval_task, rule, db)
        )
        self.escalation_monitors[task_id] = monitor_task
        
        logger.info(
            f"Scheduled time-based escalation for task {task_id} "
            f"after {rule.trigger_after_hours} hours"
        )
    
    async def _monitor_time_escalation(
        self,
        approval_task: ApprovalTask,
        rule: EscalationRule,
        db: AsyncSession
    ) -> None:
        """Monitor and trigger time-based escalation"""
        try:
            # Wait for the specified time
            await asyncio.sleep(rule.trigger_after_hours * 3600)
            
            # Check if task is still pending
            result = await db.execute(
                select(ApprovalTask).where(
                    and_(
                        ApprovalTask.id == approval_task.id,
                        ApprovalTask.status == ApprovalStatus.PENDING
                    )
                )
            )
            task = result.scalar_one_or_none()
            
            if task:
                await self._execute_escalation(
                    task, rule, EscalationTrigger.TIME_EXPIRED, db
                )
            else:
                logger.info(
                    f"Task {approval_task.id} no longer pending, "
                    "skipping time-based escalation"
                )
                
        except asyncio.CancelledError:
            logger.info(f"Time escalation monitor cancelled for task {approval_task.id}")
        except Exception as e:
            logger.error(f"Error in time escalation monitor: {e}")
    
    async def _setup_condition_monitoring(
        self,
        approval_task: ApprovalTask,
        rule: EscalationRule,
        db: AsyncSession
    ) -> None:
        """Setup condition-based escalation monitoring"""
        # In a real implementation, this would set up event listeners
        # or periodic checks for the specified conditions
        logger.info(
            f"Condition-based escalation configured for task {approval_task.id}"
        )
    
    async def handle_rejection_escalation(
        self,
        approval_task: ApprovalTask,
        rejected_by: str,
        rejection_reason: str,
        db: AsyncSession
    ) -> None:
        """
        Handle escalation when an approval is rejected
        
        Args:
            approval_task: The rejected approval task
            rejected_by: ID of the user who rejected
            rejection_reason: Reason for rejection
            db: Database session
        """
        try:
            # Find rejection-based escalation rules
            config = approval_task.get_config()
            rejection_rules = [
                rule for rule in config.escalation_rules
                if rule.escalation_type == EscalationType.REJECTION_BASED
            ]
            
            for rule in rejection_rules:
                # Check if rejection count threshold is met
                rejection_count = await self._get_rejection_count(approval_task.id, db)
                
                if rejection_count >= rule.rejection_count:
                    await self._execute_escalation(
                        approval_task, rule, EscalationTrigger.REJECTION, db
                    )
                    
        except Exception as e:
            logger.error(f"Failed to handle rejection escalation: {e}")
            raise WorkflowException(f"Failed to handle rejection escalation: {e}")
    
    async def _execute_escalation(
        self,
        approval_task: ApprovalTask,
        rule: EscalationRule,
        trigger: EscalationTrigger,
        db: AsyncSession
    ) -> None:
        """Execute escalation action"""
        try:
            logger.info(
                f"Executing escalation for task {approval_task.id}, "
                f"trigger: {trigger.value}"
            )
            
            # Record escalation in history
            history_entry = ApprovalHistory(
                approval_task_id=approval_task.id,
                action="escalated",
                performed_by="system",
                details={
                    "trigger": trigger.value,
                    "rule_type": rule.escalation_type.value,
                    "escalated_to": rule.escalate_to.identifier if rule.escalate_to else None
                }
            )
            db.add(history_entry)
            
            # Perform escalation action
            if rule.escalation_action == "add_approver" and rule.escalate_to:
                # Add new approver to the approval chain
                await self._add_escalation_approver(
                    approval_task, rule.escalate_to, db
                )
            elif rule.escalation_action == "replace_approver" and rule.escalate_to:
                # Replace current approvers with escalation approver
                await self._replace_approvers(
                    approval_task, rule.escalate_to, db
                )
            elif rule.escalation_action == "notify":
                # Send notification without changing approvers
                await self._send_escalation_notification(
                    approval_task, rule, trigger
                )
            elif rule.escalation_action == "auto_approve":
                # Auto-approve after timeout
                await self._auto_approve_task(
                    approval_task, rule, db
                )
            elif rule.escalation_action == "cancel":
                # Cancel the approval task
                await self._cancel_task(
                    approval_task, rule, db
                )
            
            # Send notification if message is provided
            if rule.escalation_message:
                await self.notification_service.send_notification(
                    user_id=rule.escalate_to.identifier if rule.escalate_to else "admin",
                    title="Approval Escalation",
                    message=rule.escalation_message,
                    priority=NotificationPriority.HIGH,
                    metadata={
                        "approval_task_id": str(approval_task.id),
                        "trigger": trigger.value
                    }
                )
            
            await db.commit()
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to execute escalation: {e}")
            raise WorkflowException(f"Failed to execute escalation: {e}")
    
    async def _add_escalation_approver(
        self,
        approval_task: ApprovalTask,
        approver: ApproverConfig,
        db: AsyncSession
    ) -> None:
        """Add escalation approver to approval chain"""
        config = approval_task.get_config()
        
        # Add new approver
        config.approvers.append(approver)
        
        # Update task configuration
        approval_task.set_config(config)
        
        # Update task status to ensure it's being processed
        if approval_task.status == ApprovalStatus.PENDING:
            approval_task.status = ApprovalStatus.ESCALATED
        
        await db.flush()
        
        logger.info(
            f"Added escalation approver {approver.identifier} "
            f"to task {approval_task.id}"
        )
    
    async def _replace_approvers(
        self,
        approval_task: ApprovalTask,
        new_approver: ApproverConfig,
        db: AsyncSession
    ) -> None:
        """Replace current approvers with escalation approver"""
        config = approval_task.get_config()
        
        # Store original approvers in metadata
        approval_task.metadata = approval_task.metadata or {}
        approval_task.metadata["original_approvers"] = [
            a.dict() for a in config.approvers
        ]
        
        # Replace approvers
        config.approvers = [new_approver]
        
        # Update task configuration
        approval_task.set_config(config)
        approval_task.status = ApprovalStatus.ESCALATED
        
        await db.flush()
        
        logger.info(
            f"Replaced approvers with {new_approver.identifier} "
            f"for task {approval_task.id}"
        )
    
    async def _send_escalation_notification(
        self,
        approval_task: ApprovalTask,
        rule: EscalationRule,
        trigger: EscalationTrigger
    ) -> None:
        """Send escalation notification"""
        config = approval_task.get_config()
        
        # Determine recipients
        recipients = []
        if rule.escalate_to:
            recipients.append(rule.escalate_to.identifier)
        
        # Add current approvers
        recipients.extend([a.identifier for a in config.approvers])
        
        # Add requestor
        if approval_task.created_by:
            recipients.append(approval_task.created_by)
        
        # Send notifications
        for recipient in set(recipients):
            await self.notification_service.send_notification(
                user_id=recipient,
                title="Approval Escalation Alert",
                message=rule.escalation_message or f"Approval task has been escalated due to {trigger.value}",
                priority=NotificationPriority.HIGH,
                metadata={
                    "approval_task_id": str(approval_task.id),
                    "trigger": trigger.value
                }
            )
    
    async def _auto_approve_task(
        self,
        approval_task: ApprovalTask,
        rule: EscalationRule,
        db: AsyncSession
    ) -> None:
        """Auto-approve task after escalation timeout"""
        approval_task.status = ApprovalStatus.APPROVED
        approval_task.metadata = approval_task.metadata or {}
        approval_task.metadata["auto_approved"] = True
        approval_task.metadata["auto_approve_reason"] = rule.escalation_message or "Escalation timeout"
        
        # Add history entry
        history_entry = ApprovalHistory(
            approval_task_id=approval_task.id,
            action="auto_approved",
            performed_by="system",
            details={
                "reason": "escalation_timeout",
                "rule_type": rule.escalation_type.value
            }
        )
        db.add(history_entry)
        
        await db.flush()
        
        logger.info(f"Auto-approved task {approval_task.id} due to escalation timeout")
    
    async def _cancel_task(
        self,
        approval_task: ApprovalTask,
        rule: EscalationRule,
        db: AsyncSession
    ) -> None:
        """Cancel approval task"""
        approval_task.status = ApprovalStatus.CANCELLED
        approval_task.metadata = approval_task.metadata or {}
        approval_task.metadata["cancelled_reason"] = rule.escalation_message or "Escalation resulted in cancellation"
        
        # Add history entry
        history_entry = ApprovalHistory(
            approval_task_id=approval_task.id,
            action="cancelled",
            performed_by="system",
            details={
                "reason": "escalation_cancellation",
                "rule_type": rule.escalation_type.value
            }
        )
        db.add(history_entry)
        
        await db.flush()
        
        logger.info(f"Cancelled task {approval_task.id} due to escalation")
    
    async def _get_rejection_count(
        self,
        approval_task_id: str,
        db: AsyncSession
    ) -> int:
        """Get rejection count for an approval task"""
        result = await db.execute(
            select(ApprovalHistory).where(
                and_(
                    ApprovalHistory.approval_task_id == approval_task_id,
                    ApprovalHistory.action == "rejected"
                )
            )
        )
        rejections = result.scalars().all()
        return len(rejections)
    
    async def check_sla_violations(
        self,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """
        Check for SLA violations across all active approvals
        
        Returns:
            List of violations with task details
        """
        try:
            violations = []
            
            # Get all pending approvals
            result = await db.execute(
                select(ApprovalTask).where(
                    ApprovalTask.status.in_([
                        ApprovalStatus.PENDING,
                        ApprovalStatus.IN_PROGRESS
                    ])
                )
            )
            pending_tasks = result.scalars().all()
            
            current_time = datetime.utcnow()
            
            for task in pending_tasks:
                config = task.get_config()
                
                if config.approval_deadline_hours:
                    deadline = task.created_at + timedelta(
                        hours=config.approval_deadline_hours
                    )
                    
                    if current_time > deadline:
                        time_overdue = (current_time - deadline).total_seconds() / 3600
                        
                        violations.append({
                            "task_id": str(task.id),
                            "title": config.title,
                            "created_at": task.created_at.isoformat(),
                            "deadline": deadline.isoformat(),
                            "hours_overdue": round(time_overdue, 2),
                            "status": task.status.value,
                            "approvers": [
                                a.identifier for a in config.approvers
                            ]
                        })
            
            return violations
            
        except Exception as e:
            logger.error(f"Failed to check SLA violations: {e}")
            raise WorkflowException(f"Failed to check SLA violations: {e}")
    
    async def get_escalation_metrics(
        self,
        start_date: datetime,
        end_date: datetime,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Get escalation metrics for the specified period
        
        Args:
            start_date: Start date for metrics
            end_date: End date for metrics
            db: Database session
            
        Returns:
            Dictionary with escalation metrics
        """
        try:
            # Get escalation events
            result = await db.execute(
                select(ApprovalHistory).where(
                    and_(
                        ApprovalHistory.action == "escalated",
                        ApprovalHistory.created_at >= start_date,
                        ApprovalHistory.created_at <= end_date
                    )
                )
            )
            escalations = result.scalars().all()
            
            # Analyze escalation triggers
            trigger_counts = {}
            escalation_types = {}
            
            for escalation in escalations:
                details = escalation.details or {}
                trigger = details.get("trigger", "unknown")
                rule_type = details.get("rule_type", "unknown")
                
                trigger_counts[trigger] = trigger_counts.get(trigger, 0) + 1
                escalation_types[rule_type] = escalation_types.get(rule_type, 0) + 1
            
            # Get auto-approval count
            result = await db.execute(
                select(ApprovalHistory).where(
                    and_(
                        ApprovalHistory.action == "auto_approved",
                        ApprovalHistory.created_at >= start_date,
                        ApprovalHistory.created_at <= end_date
                    )
                )
            )
            auto_approvals = len(result.scalars().all())
            
            return {
                "total_escalations": len(escalations),
                "trigger_breakdown": trigger_counts,
                "type_breakdown": escalation_types,
                "auto_approvals": auto_approvals,
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get escalation metrics: {e}")
            raise WorkflowException(f"Failed to get escalation metrics: {e}")
    
    def cleanup_monitors(self) -> None:
        """Cleanup all escalation monitors"""
        for task_id, monitor in self.escalation_monitors.items():
            if not monitor.done():
                monitor.cancel()
        
        self.escalation_monitors.clear()
        logger.info("Cleaned up all escalation monitors")