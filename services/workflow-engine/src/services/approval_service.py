"""
Approval workflow service for managing approval processes
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
import uuid
import json

from ..models.approval_schemas import (
    ApprovalStatus, ApprovalType, ApprovalRequest, ApprovalDecision,
    ApprovalTaskConfig, ApproverConfig, ApprovalNotification,
    EscalationRule, CreateApprovalRequest, UpdateApprovalDecision,
    DelegateApprovalRequest, ApprovalSearchRequest, ApprovalResponse,
    ApprovalListResponse, ApprovalDashboard, VotingStrategy
)
from ..db.models import WorkflowInstance, TaskInstance
from ..core.exceptions import WorkflowException

logger = logging.getLogger(__name__)


class ApprovalService:
    """Service for managing approval workflows"""
    
    def __init__(self):
        self.approval_store: Dict[str, ApprovalRequest] = {}
        self.notifications_store: Dict[str, List[ApprovalNotification]] = {}
        self.decision_store: Dict[str, List[ApprovalDecision]] = {}
    
    async def create_approval_request(
        self,
        db: AsyncSession,
        user_id: str,
        request: CreateApprovalRequest
    ) -> ApprovalRequest:
        """Create a new approval request"""
        try:
            # Verify workflow and task instances exist
            workflow_instance = await self._get_workflow_instance(
                db, request.workflow_instance_id
            )
            task_instance = await self._get_task_instance(
                db, request.task_instance_id
            )
            
            # Create approval request
            approval_request = ApprovalRequest(
                workflow_instance_id=request.workflow_instance_id,
                task_instance_id=request.task_instance_id,
                title=request.title,
                description=request.description,
                requestor_id=user_id,
                requestor_name=f"User {user_id}",  # In real implementation, fetch from user service
                approval_config=request.approval_config,
                context_data=request.context_data,
                attachments=request.attachments,
                tags=request.tags
            )
            
            # Calculate deadline if specified
            if request.approval_config.approval_deadline_hours:
                approval_request.deadline_at = datetime.utcnow() + timedelta(
                    hours=request.approval_config.approval_deadline_hours
                )
            
            # Store the approval request
            self.approval_store[approval_request.request_id] = approval_request
            
            # Create notifications for approvers
            await self._create_initial_notifications(approval_request)
            
            # Update task instance status
            await self._update_task_status(db, task_instance, "waiting_approval")
            
            logger.info(f"Created approval request {approval_request.request_id}")
            return approval_request
            
        except Exception as e:
            logger.error(f"Failed to create approval request: {e}")
            raise WorkflowException(f"Failed to create approval request: {e}")
    
    async def get_approval_request(
        self,
        request_id: str
    ) -> Optional[ApprovalRequest]:
        """Get an approval request by ID"""
        return self.approval_store.get(request_id)
    
    async def update_approval_decision(
        self,
        request_id: str,
        approver_id: str,
        decision_update: UpdateApprovalDecision
    ) -> ApprovalDecision:
        """Update an approval decision"""
        try:
            approval_request = self.approval_store.get(request_id)
            if not approval_request:
                raise WorkflowException(f"Approval request {request_id} not found")
            
            if approval_request.status != ApprovalStatus.PENDING:
                raise WorkflowException(
                    f"Cannot update decision for {approval_request.status} request"
                )
            
            # Find the approver
            approver = self._find_approver(
                approval_request.approval_config.approvers, approver_id
            )
            if not approver:
                raise WorkflowException(f"Approver {approver_id} not found")
            
            # Create decision
            decision = ApprovalDecision(
                request_id=request_id,
                approver_id=approver_id,
                approver_name=approver.name,
                approver_type=approver.approver_type,
                decision=decision_update.decision,
                comments=decision_update.comments,
                form_data=decision_update.form_data,
                attachments=decision_update.attachments,
                assigned_at=approval_request.created_at,
                vote_weight=approver.vote_weight
            )
            
            # Calculate response time
            decision.response_time_hours = (
                decision.decided_at - decision.assigned_at
            ).total_seconds() / 3600
            
            # Store decision
            if request_id not in self.decision_store:
                self.decision_store[request_id] = []
            self.decision_store[request_id].append(decision)
            approval_request.approval_decisions.append(decision)
            
            # Check if approval is complete
            await self._check_approval_completion(approval_request)
            
            # Send notification about the decision
            await self._send_decision_notification(approval_request, decision)
            
            logger.info(
                f"Updated approval decision for request {request_id} "
                f"by {approver_id}: {decision.decision}"
            )
            return decision
            
        except Exception as e:
            logger.error(f"Failed to update approval decision: {e}")
            raise WorkflowException(f"Failed to update approval decision: {e}")
    
    async def delegate_approval(
        self,
        request_id: str,
        approver_id: str,
        delegation: DelegateApprovalRequest
    ) -> ApprovalRequest:
        """Delegate an approval to another approver"""
        try:
            approval_request = self.approval_store.get(request_id)
            if not approval_request:
                raise WorkflowException(f"Approval request {request_id} not found")
            
            # Find and update the approver
            for i, approver in enumerate(approval_request.approval_config.approvers):
                if approver.identifier == approver_id:
                    if not approver.can_delegate:
                        raise WorkflowException(
                            f"Approver {approver_id} cannot delegate"
                        )
                    
                    # Replace with delegate
                    approval_request.approval_config.approvers[i] = delegation.delegate_to
                    
                    # Record delegation in history
                    approval_request.metadata["delegations"] = approval_request.metadata.get(
                        "delegations", []
                    )
                    approval_request.metadata["delegations"].append({
                        "from": approver_id,
                        "to": delegation.delegate_to.identifier,
                        "reason": delegation.delegation_reason,
                        "timestamp": datetime.utcnow().isoformat(),
                        "retain_visibility": delegation.retain_visibility
                    })
                    
                    # Send notifications
                    await self._send_delegation_notification(
                        approval_request, approver, delegation.delegate_to
                    )
                    
                    break
            
            logger.info(
                f"Delegated approval {request_id} from {approver_id} "
                f"to {delegation.delegate_to.identifier}"
            )
            return approval_request
            
        except Exception as e:
            logger.error(f"Failed to delegate approval: {e}")
            raise WorkflowException(f"Failed to delegate approval: {e}")
    
    async def escalate_approval(
        self,
        request_id: str,
        escalation_rule: EscalationRule
    ) -> ApprovalRequest:
        """Escalate an approval request"""
        try:
            approval_request = self.approval_store.get(request_id)
            if not approval_request:
                raise WorkflowException(f"Approval request {request_id} not found")
            
            # Check if we can escalate
            if approval_request.current_escalation_level >= escalation_rule.max_escalation_levels:
                raise WorkflowException("Maximum escalation level reached")
            
            # Update escalation level
            approval_request.current_escalation_level += 1
            approval_request.status = ApprovalStatus.ESCALATED
            
            # Add escalation to history
            approval_request.escalation_history.append({
                "level": approval_request.current_escalation_level,
                "rule_id": escalation_rule.rule_id,
                "escalated_to": escalation_rule.escalate_to.identifier,
                "timestamp": datetime.utcnow().isoformat(),
                "reason": escalation_rule.escalation_type
            })
            
            # Add new approver
            approval_request.approval_config.approvers.append(escalation_rule.escalate_to)
            
            # Send escalation notifications
            await self._send_escalation_notifications(
                approval_request, escalation_rule
            )
            
            logger.info(
                f"Escalated approval {request_id} to level "
                f"{approval_request.current_escalation_level}"
            )
            return approval_request
            
        except Exception as e:
            logger.error(f"Failed to escalate approval: {e}")
            raise WorkflowException(f"Failed to escalate approval: {e}")
    
    async def search_approvals(
        self,
        search_request: ApprovalSearchRequest
    ) -> ApprovalListResponse:
        """Search for approval requests"""
        try:
            # Filter approvals based on criteria
            filtered_approvals = []
            
            for approval in self.approval_store.values():
                # Status filter
                if search_request.status and approval.status not in search_request.status:
                    continue
                
                # Approver filter
                if search_request.approver_id:
                    approver_ids = [
                        a.identifier for a in approval.approval_config.approvers
                    ]
                    if search_request.approver_id not in approver_ids:
                        continue
                
                # Requestor filter
                if (search_request.requestor_id and 
                    approval.requestor_id != search_request.requestor_id):
                    continue
                
                # Date filters
                if (search_request.created_after and 
                    approval.created_at < search_request.created_after):
                    continue
                if (search_request.created_before and 
                    approval.created_at > search_request.created_before):
                    continue
                
                # Deadline filter
                if search_request.deadline_before and approval.deadline_at:
                    if approval.deadline_at > search_request.deadline_before:
                        continue
                
                # Tag filter
                if search_request.tags:
                    if not any(tag in approval.tags for tag in search_request.tags):
                        continue
                
                filtered_approvals.append(approval)
            
            # Sort results
            filtered_approvals.sort(
                key=lambda x: getattr(x, search_request.sort_by),
                reverse=(search_request.sort_order == "desc")
            )
            
            # Paginate
            start = (search_request.page - 1) * search_request.page_size
            end = start + search_request.page_size
            paginated_approvals = filtered_approvals[start:end]
            
            # Convert to response format
            approval_responses = [
                ApprovalResponse(
                    request_id=a.request_id,
                    title=a.title,
                    description=a.description,
                    status=a.status,
                    requestor_name=a.requestor_name,
                    created_at=a.created_at,
                    deadline_at=a.deadline_at,
                    approval_progress=self._calculate_approval_progress(a),
                    pending_approvers=self._get_pending_approvers(a),
                    completed_approvers=self._get_completed_approvers(a)
                )
                for a in paginated_approvals
            ]
            
            return ApprovalListResponse(
                approvals=approval_responses,
                total=len(filtered_approvals),
                page=search_request.page,
                page_size=search_request.page_size
            )
            
        except Exception as e:
            logger.error(f"Failed to search approvals: {e}")
            raise WorkflowException(f"Failed to search approvals: {e}")
    
    async def get_approval_dashboard(
        self,
        user_id: str
    ) -> ApprovalDashboard:
        """Get approval dashboard for a user"""
        try:
            dashboard = ApprovalDashboard(user_id=user_id)
            
            # Get pending approvals for the user
            for approval in self.approval_store.values():
                approver_ids = [
                    a.identifier for a in approval.approval_config.approvers
                ]
                if user_id in approver_ids and approval.status == ApprovalStatus.PENDING:
                    dashboard.pending_approvals.append(approval)
                    dashboard.pending_count += 1
            
            # Get recent decisions by the user
            for request_id, decisions in self.decision_store.items():
                for decision in decisions:
                    if decision.approver_id == user_id:
                        dashboard.recent_decisions.append(decision)
                        
                        # Update statistics
                        dashboard.total_requests_received += 1
                        if decision.decision == ApprovalStatus.APPROVED:
                            dashboard.total_approved += 1
                        elif decision.decision == ApprovalStatus.REJECTED:
                            dashboard.total_rejected += 1
            
            # Calculate average response time
            if dashboard.recent_decisions:
                total_response_time = sum(
                    d.response_time_hours or 0 for d in dashboard.recent_decisions
                )
                dashboard.average_response_time_hours = (
                    total_response_time / len(dashboard.recent_decisions)
                )
            
            # Group by status
            for approval in self.approval_store.values():
                approver_ids = [
                    a.identifier for a in approval.approval_config.approvers
                ]
                if user_id in approver_ids:
                    status = approval.status
                    dashboard.requests_by_status[status] = dashboard.requests_by_status.get(
                        status, 0
                    ) + 1
            
            # Get upcoming deadlines
            for approval in dashboard.pending_approvals:
                if approval.deadline_at:
                    time_remaining = approval.deadline_at - datetime.utcnow()
                    if time_remaining.total_seconds() > 0:
                        dashboard.upcoming_deadlines.append({
                            "request_id": approval.request_id,
                            "title": approval.title,
                            "deadline": approval.deadline_at.isoformat(),
                            "hours_remaining": time_remaining.total_seconds() / 3600
                        })
            
            # Sort deadlines by urgency
            dashboard.upcoming_deadlines.sort(key=lambda x: x["hours_remaining"])
            
            return dashboard
            
        except Exception as e:
            logger.error(f"Failed to get approval dashboard: {e}")
            raise WorkflowException(f"Failed to get approval dashboard: {e}")
    
    async def check_timeouts(self):
        """Check for approval timeouts and trigger actions"""
        try:
            current_time = datetime.utcnow()
            
            for approval in self.approval_store.values():
                if (approval.status == ApprovalStatus.PENDING and 
                    approval.deadline_at and 
                    approval.deadline_at < current_time):
                    
                    # Handle timeout based on configuration
                    config = approval.approval_config
                    
                    if config.auto_approve_on_timeout:
                        approval.status = ApprovalStatus.APPROVED
                        approval.final_decision = ApprovalStatus.APPROVED
                        approval.final_comments = "Auto-approved due to timeout"
                    elif config.auto_reject_on_timeout:
                        approval.status = ApprovalStatus.REJECTED
                        approval.final_decision = ApprovalStatus.REJECTED
                        approval.final_comments = "Auto-rejected due to timeout"
                    else:
                        approval.status = ApprovalStatus.EXPIRED
                    
                    approval.completed_at = current_time
                    
                    # Trigger timeout actions
                    for action in config.on_timeout_actions:
                        await self._trigger_action(approval, action)
                    
                    logger.info(
                        f"Approval {approval.request_id} timed out. "
                        f"Status: {approval.status}"
                    )
                    
        except Exception as e:
            logger.error(f"Error checking timeouts: {e}")
    
    async def send_reminders(self):
        """Send reminder notifications for pending approvals"""
        try:
            current_time = datetime.utcnow()
            
            for approval in self.approval_store.values():
                if approval.status != ApprovalStatus.PENDING:
                    continue
                
                config = approval.approval_config
                if not config.send_reminder_notifications:
                    continue
                
                # Calculate time since creation
                time_elapsed = current_time - approval.created_at
                hours_elapsed = time_elapsed.total_seconds() / 3600
                
                # Check reminder intervals
                for interval in config.reminder_intervals_hours:
                    # Check if we should send a reminder
                    last_reminder = approval.metadata.get(
                        f"reminder_{interval}h_sent", False
                    )
                    
                    if hours_elapsed >= interval and not last_reminder:
                        # Send reminders to pending approvers
                        pending_approver_ids = self._get_pending_approver_ids(approval)
                        
                        for approver_id in pending_approver_ids:
                            await self._send_reminder_notification(
                                approval, approver_id, interval
                            )
                        
                        # Mark reminder as sent
                        approval.metadata[f"reminder_{interval}h_sent"] = True
                        
                        logger.info(
                            f"Sent {interval}h reminder for approval "
                            f"{approval.request_id}"
                        )
                        
        except Exception as e:
            logger.error(f"Error sending reminders: {e}")
    
    # Private helper methods
    
    async def _get_workflow_instance(
        self,
        db: AsyncSession,
        instance_id: str
    ) -> WorkflowInstance:
        """Get workflow instance from database"""
        result = await db.execute(
            select(WorkflowInstance).where(
                WorkflowInstance.instance_id == instance_id
            )
        )
        instance = result.scalar_one_or_none()
        if not instance:
            raise WorkflowException(f"Workflow instance {instance_id} not found")
        return instance
    
    async def _get_task_instance(
        self,
        db: AsyncSession,
        task_id: str
    ) -> TaskInstance:
        """Get task instance from database"""
        result = await db.execute(
            select(TaskInstance).where(
                TaskInstance.task_instance_id == task_id
            )
        )
        instance = result.scalar_one_or_none()
        if not instance:
            raise WorkflowException(f"Task instance {task_id} not found")
        return instance
    
    async def _update_task_status(
        self,
        db: AsyncSession,
        task_instance: TaskInstance,
        status: str
    ):
        """Update task instance status"""
        task_instance.status = status
        task_instance.updated_at = datetime.utcnow()
        await db.commit()
    
    def _find_approver(
        self,
        approvers: List[ApproverConfig],
        approver_id: str
    ) -> Optional[ApproverConfig]:
        """Find an approver by ID"""
        for approver in approvers:
            if approver.identifier == approver_id:
                return approver
        return None
    
    async def _check_approval_completion(
        self,
        approval_request: ApprovalRequest
    ):
        """Check if approval is complete based on type and strategy"""
        config = approval_request.approval_config
        decisions = approval_request.approval_decisions
        
        if config.approval_type == ApprovalType.SINGLE:
            # Single approver - complete when one decision is made
            if decisions:
                decision = decisions[0]
                approval_request.status = decision.decision
                approval_request.final_decision = decision.decision
                approval_request.completed_at = datetime.utcnow()
                
        elif config.approval_type == ApprovalType.SEQUENTIAL:
            # Sequential - check if current level is complete
            current_level_approvers = self._get_current_level_approvers(
                approval_request
            )
            current_level_decisions = [
                d for d in decisions 
                if d.approver_id in [a.identifier for a in current_level_approvers]
            ]
            
            if len(current_level_decisions) == len(current_level_approvers):
                # Current level complete
                if any(d.decision == ApprovalStatus.REJECTED for d in current_level_decisions):
                    # Rejected at this level
                    approval_request.status = ApprovalStatus.REJECTED
                    approval_request.final_decision = ApprovalStatus.REJECTED
                    approval_request.completed_at = datetime.utcnow()
                else:
                    # Move to next level or complete
                    approval_request.current_level += 1
                    if approval_request.current_level >= self._get_total_levels(approval_request):
                        approval_request.status = ApprovalStatus.APPROVED
                        approval_request.final_decision = ApprovalStatus.APPROVED
                        approval_request.completed_at = datetime.utcnow()
                        
        elif config.approval_type in [ApprovalType.PARALLEL, ApprovalType.VOTING]:
            # Parallel/Voting - check voting strategy
            self._check_voting_completion(approval_request)
    
    def _check_voting_completion(
        self,
        approval_request: ApprovalRequest
    ):
        """Check if voting-based approval is complete"""
        config = approval_request.approval_config
        decisions = approval_request.approval_decisions
        total_approvers = len(config.approvers)
        
        if len(decisions) < total_approvers and not config.allow_partial_approval:
            return  # Not all votes in yet
        
        # Calculate votes
        approve_weight = sum(
            d.vote_weight for d in decisions 
            if d.decision == ApprovalStatus.APPROVED
        )
        reject_weight = sum(
            d.vote_weight for d in decisions 
            if d.decision == ApprovalStatus.REJECTED
        )
        total_weight = sum(a.vote_weight for a in config.approvers)
        
        if config.voting_strategy == VotingStrategy.UNANIMOUS:
            if reject_weight > 0:
                approval_request.status = ApprovalStatus.REJECTED
                approval_request.final_decision = ApprovalStatus.REJECTED
            elif approve_weight == total_weight:
                approval_request.status = ApprovalStatus.APPROVED
                approval_request.final_decision = ApprovalStatus.APPROVED
                
        elif config.voting_strategy == VotingStrategy.MAJORITY:
            if approve_weight > total_weight / 2:
                approval_request.status = ApprovalStatus.APPROVED
                approval_request.final_decision = ApprovalStatus.APPROVED
            elif reject_weight > total_weight / 2:
                approval_request.status = ApprovalStatus.REJECTED
                approval_request.final_decision = ApprovalStatus.REJECTED
                
        elif config.voting_strategy == VotingStrategy.CUSTOM_THRESHOLD:
            threshold = config.approval_threshold or 0.5
            if approve_weight / total_weight >= threshold:
                approval_request.status = ApprovalStatus.APPROVED
                approval_request.final_decision = ApprovalStatus.APPROVED
            elif len(decisions) == total_approvers:
                approval_request.status = ApprovalStatus.REJECTED
                approval_request.final_decision = ApprovalStatus.REJECTED
        
        if approval_request.final_decision:
            approval_request.completed_at = datetime.utcnow()
    
    def _calculate_approval_progress(
        self,
        approval: ApprovalRequest
    ) -> float:
        """Calculate approval progress (0.0 to 1.0)"""
        total_approvers = len(approval.approval_config.approvers)
        if total_approvers == 0:
            return 0.0
        
        completed_decisions = len(approval.approval_decisions)
        return completed_decisions / total_approvers
    
    def _get_pending_approvers(
        self,
        approval: ApprovalRequest
    ) -> List[str]:
        """Get list of pending approver names"""
        decided_approver_ids = {
            d.approver_id for d in approval.approval_decisions
        }
        
        pending = []
        for approver in approval.approval_config.approvers:
            if approver.identifier not in decided_approver_ids:
                pending.append(approver.name)
        
        return pending
    
    def _get_pending_approver_ids(
        self,
        approval: ApprovalRequest
    ) -> List[str]:
        """Get list of pending approver IDs"""
        decided_approver_ids = {
            d.approver_id for d in approval.approval_decisions
        }
        
        pending = []
        for approver in approval.approval_config.approvers:
            if approver.identifier not in decided_approver_ids:
                pending.append(approver.identifier)
        
        return pending
    
    def _get_completed_approvers(
        self,
        approval: ApprovalRequest
    ) -> List[str]:
        """Get list of completed approver names"""
        return [d.approver_name for d in approval.approval_decisions]
    
    def _get_current_level_approvers(
        self,
        approval: ApprovalRequest
    ) -> List[ApproverConfig]:
        """Get approvers for current level (sequential approval)"""
        # In a real implementation, approvers would be organized by level
        # For now, we'll treat them as one level each
        level = approval.current_level
        if level < len(approval.approval_config.approvers):
            return [approval.approval_config.approvers[level]]
        return []
    
    def _get_total_levels(
        self,
        approval: ApprovalRequest
    ) -> int:
        """Get total number of levels (sequential approval)"""
        # In a real implementation, this would be based on the approval structure
        return len(approval.approval_config.approvers)
    
    async def _create_initial_notifications(
        self,
        approval: ApprovalRequest
    ):
        """Create initial notifications for approvers"""
        if not approval.approval_config.send_initial_notification:
            return
        
        for approver in approval.approval_config.approvers:
            notification = ApprovalNotification(
                request_id=approval.request_id,
                notification_type="new_request",
                recipient_id=approver.identifier,
                recipient_email=approver.email or f"{approver.identifier}@example.com",
                subject=f"New Approval Request: {approval.title}",
                body=f"""
                You have a new approval request:
                
                Title: {approval.title}
                Description: {approval.description}
                Requestor: {approval.requestor_name}
                Created: {approval.created_at}
                Deadline: {approval.deadline_at or 'No deadline'}
                
                Please review and respond at your earliest convenience.
                """,
                priority="normal" if not approval.deadline_at else "high",
                action_links=[{
                    "label": "Review Request",
                    "url": f"/approvals/{approval.request_id}"
                }]
            )
            
            # Store notification
            if approval.request_id not in self.notifications_store:
                self.notifications_store[approval.request_id] = []
            self.notifications_store[approval.request_id].append(notification)
            
            # In a real implementation, send via notification service
            logger.info(
                f"Created notification for {approver.identifier} "
                f"for approval {approval.request_id}"
            )
    
    async def _send_decision_notification(
        self,
        approval: ApprovalRequest,
        decision: ApprovalDecision
    ):
        """Send notification about a decision"""
        # Notify requestor
        notification = ApprovalNotification(
            request_id=approval.request_id,
            notification_type="decision",
            recipient_id=approval.requestor_id,
            recipient_email=approval.requestor_email or f"{approval.requestor_id}@example.com",
            subject=f"Approval Decision: {approval.title}",
            body=f"""
            An approval decision has been made:
            
            Title: {approval.title}
            Approver: {decision.approver_name}
            Decision: {decision.decision}
            Comments: {decision.comments or 'No comments'}
            Decided at: {decision.decided_at}
            
            Current Status: {approval.status}
            """,
            priority="normal"
        )
        
        if approval.request_id not in self.notifications_store:
            self.notifications_store[approval.request_id] = []
        self.notifications_store[approval.request_id].append(notification)
    
    async def _send_delegation_notification(
        self,
        approval: ApprovalRequest,
        from_approver: ApproverConfig,
        to_approver: ApproverConfig
    ):
        """Send notification about delegation"""
        notification = ApprovalNotification(
            request_id=approval.request_id,
            notification_type="delegation",
            recipient_id=to_approver.identifier,
            recipient_email=to_approver.email or f"{to_approver.identifier}@example.com",
            subject=f"Approval Delegated: {approval.title}",
            body=f"""
            An approval has been delegated to you:
            
            Title: {approval.title}
            Description: {approval.description}
            Delegated by: {from_approver.name}
            Original Requestor: {approval.requestor_name}
            Created: {approval.created_at}
            Deadline: {approval.deadline_at or 'No deadline'}
            
            Please review and respond at your earliest convenience.
            """,
            priority="high",
            action_links=[{
                "label": "Review Request",
                "url": f"/approvals/{approval.request_id}"
            }]
        )
        
        if approval.request_id not in self.notifications_store:
            self.notifications_store[approval.request_id] = []
        self.notifications_store[approval.request_id].append(notification)
    
    async def _send_escalation_notifications(
        self,
        approval: ApprovalRequest,
        escalation_rule: EscalationRule
    ):
        """Send notifications about escalation"""
        # Notify new approver
        notification = ApprovalNotification(
            request_id=approval.request_id,
            notification_type="escalation",
            recipient_id=escalation_rule.escalate_to.identifier,
            recipient_email=escalation_rule.escalate_to.email or 
                          f"{escalation_rule.escalate_to.identifier}@example.com",
            subject=f"Escalated Approval: {approval.title}",
            body=f"""
            An approval has been escalated to you:
            
            Title: {approval.title}
            Description: {approval.description}
            Escalation Reason: {escalation_rule.escalation_type}
            Original Requestor: {approval.requestor_name}
            Created: {approval.created_at}
            Deadline: {approval.deadline_at or 'No deadline'}
            
            {escalation_rule.escalation_message or ''}
            
            This requires your immediate attention.
            """,
            priority="urgent",
            action_links=[{
                "label": "Review Urgent Request",
                "url": f"/approvals/{approval.request_id}"
            }]
        )
        
        if approval.request_id not in self.notifications_store:
            self.notifications_store[approval.request_id] = []
        self.notifications_store[approval.request_id].append(notification)
        
        # Notify others if configured
        if escalation_rule.notify_original_approvers:
            for approver in approval.approval_config.approvers:
                if approver.identifier != escalation_rule.escalate_to.identifier:
                    # Send FYI notification
                    pass
        
        if escalation_rule.notify_requestor:
            # Notify requestor about escalation
            pass
    
    async def _send_reminder_notification(
        self,
        approval: ApprovalRequest,
        approver_id: str,
        interval_hours: int
    ):
        """Send reminder notification"""
        approver = self._find_approver(
            approval.approval_config.approvers, approver_id
        )
        if not approver:
            return
        
        notification = ApprovalNotification(
            request_id=approval.request_id,
            notification_type="reminder",
            recipient_id=approver_id,
            recipient_email=approver.email or f"{approver_id}@example.com",
            subject=f"Reminder: Pending Approval - {approval.title}",
            body=f"""
            This is a reminder about a pending approval request:
            
            Title: {approval.title}
            Description: {approval.description}
            Requestor: {approval.requestor_name}
            Waiting for: {interval_hours} hours
            Deadline: {approval.deadline_at or 'No deadline'}
            
            Please review and respond as soon as possible.
            """,
            priority="high" if approval.deadline_at else "normal",
            action_links=[{
                "label": "Review Request",
                "url": f"/approvals/{approval.request_id}"
            }]
        )
        
        if approval.request_id not in self.notifications_store:
            self.notifications_store[approval.request_id] = []
        self.notifications_store[approval.request_id].append(notification)
    
    async def _trigger_action(
        self,
        approval: ApprovalRequest,
        action: Dict[str, Any]
    ):
        """Trigger an action (placeholder for integration with workflow engine)"""
        logger.info(
            f"Triggering action {action.get('type')} for approval "
            f"{approval.request_id}"
        )
        # In a real implementation, this would integrate with the workflow engine
        # to trigger subsequent tasks or workflows