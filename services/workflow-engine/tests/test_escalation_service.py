"""
Tests for escalation service
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
from uuid import uuid4

from src.services.escalation_service import (
    EscalationService, EscalationTrigger
)
from src.models.approval_schemas import (
    ApprovalStatus, EscalationType, EscalationRule,
    ApproverConfig, ApproverType, ApprovalTaskConfig,
    ApprovalType, NotificationPriority
)
from src.models.approval_models import ApprovalTask, ApprovalHistory


@pytest.fixture
def escalation_service():
    """Create escalation service instance"""
    return EscalationService()


@pytest.fixture
def mock_db():
    """Create mock database session"""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.flush = AsyncMock()
    return db


@pytest.fixture
def sample_approval_task():
    """Create sample approval task"""
    task = ApprovalTask()
    task.id = uuid4()
    task.workflow_instance_id = uuid4()
    task.task_instance_id = uuid4()
    task.status = ApprovalStatus.PENDING
    task.created_at = datetime.utcnow()
    task.created_by = "user123"
    
    config = ApprovalTaskConfig(
        approval_type=ApprovalType.SEQUENTIAL,
        title="Test Approval",
        description="Test approval task",
        approvers=[
            ApproverConfig(
                approver_type=ApproverType.USER,
                identifier="approver1",
                name="Approver 1"
            )
        ],
        approval_deadline_hours=72
    )
    task.config_json = config.dict()
    
    return task


@pytest.fixture
def time_based_rule():
    """Create time-based escalation rule"""
    return EscalationRule(
        escalation_type=EscalationType.TIME_BASED,
        trigger_after_hours=24,
        escalation_action="add_approver",
        escalate_to=ApproverConfig(
            approver_type=ApproverType.ROLE,
            identifier="manager",
            name="Manager"
        ),
        escalation_message="Escalated due to timeout"
    )


@pytest.fixture
def rejection_based_rule():
    """Create rejection-based escalation rule"""
    return EscalationRule(
        escalation_type=EscalationType.REJECTION_BASED,
        rejection_count=2,
        escalation_action="replace_approver",
        escalate_to=ApproverConfig(
            approver_type=ApproverType.ROLE,
            identifier="director",
            name="Director"
        ),
        escalation_message="Escalated after multiple rejections"
    )


class TestEscalationService:
    """Test escalation service functionality"""
    
    @pytest.mark.asyncio
    async def test_apply_time_based_escalation(
        self, escalation_service, sample_approval_task, time_based_rule, mock_db
    ):
        """Test applying time-based escalation rules"""
        # Apply escalation rules
        await escalation_service.apply_escalation_rules(
            sample_approval_task, [time_based_rule], mock_db
        )
        
        # Check that monitor was created
        task_id = str(sample_approval_task.id)
        assert task_id in escalation_service.escalation_monitors
        assert not escalation_service.escalation_monitors[task_id].done()
        
        # Cleanup
        escalation_service.cleanup_monitors()
    
    @pytest.mark.asyncio
    async def test_execute_escalation_add_approver(
        self, escalation_service, sample_approval_task, time_based_rule, mock_db
    ):
        """Test executing escalation that adds an approver"""
        # Execute escalation
        await escalation_service._execute_escalation(
            sample_approval_task,
            time_based_rule,
            EscalationTrigger.TIME_EXPIRED,
            mock_db
        )
        
        # Check that approver was added
        config = sample_approval_task.get_config()
        assert len(config.approvers) == 2
        assert config.approvers[1].identifier == "manager"
        
        # Check that history was recorded
        assert mock_db.add.called
        history_call = mock_db.add.call_args[0][0]
        assert isinstance(history_call, ApprovalHistory)
        assert history_call.action == "escalated"
    
    @pytest.mark.asyncio
    async def test_execute_escalation_replace_approver(
        self, escalation_service, sample_approval_task, rejection_based_rule, mock_db
    ):
        """Test executing escalation that replaces approvers"""
        # Execute escalation
        await escalation_service._execute_escalation(
            sample_approval_task,
            rejection_based_rule,
            EscalationTrigger.REJECTION,
            mock_db
        )
        
        # Check that approvers were replaced
        config = sample_approval_task.get_config()
        assert len(config.approvers) == 1
        assert config.approvers[0].identifier == "director"
        
        # Check that original approvers were stored in metadata
        assert "original_approvers" in sample_approval_task.metadata
        assert sample_approval_task.status == ApprovalStatus.ESCALATED
    
    @pytest.mark.asyncio
    async def test_execute_escalation_auto_approve(
        self, escalation_service, sample_approval_task, mock_db
    ):
        """Test executing escalation that auto-approves"""
        rule = EscalationRule(
            escalation_type=EscalationType.TIME_BASED,
            trigger_after_hours=72,
            escalation_action="auto_approve",
            escalation_message="Auto-approved due to timeout"
        )
        
        # Execute escalation
        await escalation_service._execute_escalation(
            sample_approval_task,
            rule,
            EscalationTrigger.AUTO_APPROVAL_TIMEOUT,
            mock_db
        )
        
        # Check that task was auto-approved
        assert sample_approval_task.status == ApprovalStatus.APPROVED
        assert sample_approval_task.metadata["auto_approved"] is True
        assert "Auto-approved due to timeout" in sample_approval_task.metadata["auto_approve_reason"]
    
    @pytest.mark.asyncio
    async def test_execute_escalation_cancel(
        self, escalation_service, sample_approval_task, mock_db
    ):
        """Test executing escalation that cancels the task"""
        rule = EscalationRule(
            escalation_type=EscalationType.TIME_BASED,
            trigger_after_hours=168,  # 7 days
            escalation_action="cancel",
            escalation_message="Cancelled due to no response"
        )
        
        # Execute escalation
        await escalation_service._execute_escalation(
            sample_approval_task,
            rule,
            EscalationTrigger.TIME_EXPIRED,
            mock_db
        )
        
        # Check that task was cancelled
        assert sample_approval_task.status == ApprovalStatus.CANCELLED
        assert "Cancelled due to no response" in sample_approval_task.metadata["cancelled_reason"]
    
    @pytest.mark.asyncio
    async def test_handle_rejection_escalation(
        self, escalation_service, sample_approval_task, rejection_based_rule, mock_db
    ):
        """Test handling rejection-based escalation"""
        # Set up rejection count
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [
            MagicMock(action="rejected"),
            MagicMock(action="rejected")
        ]
        mock_db.execute.return_value = mock_result
        
        # Add rejection rule to task config
        config = sample_approval_task.get_config()
        config.escalation_rules = [rejection_based_rule]
        sample_approval_task.set_config(config)
        
        # Handle rejection escalation
        await escalation_service.handle_rejection_escalation(
            sample_approval_task,
            "approver1",
            "Not approved",
            mock_db
        )
        
        # Verify escalation was triggered
        assert mock_db.add.called
    
    @pytest.mark.asyncio
    async def test_check_sla_violations(self, escalation_service, mock_db):
        """Test checking for SLA violations"""
        # Create tasks with SLA violations
        overdue_task = ApprovalTask()
        overdue_task.id = uuid4()
        overdue_task.status = ApprovalStatus.PENDING
        overdue_task.created_at = datetime.utcnow() - timedelta(hours=100)
        
        config = ApprovalTaskConfig(
            approval_type=ApprovalType.SINGLE,
            title="Overdue Approval",
            description="This approval is overdue",
            approvers=[
                ApproverConfig(
                    approver_type=ApproverType.USER,
                    identifier="user1",
                    name="User 1"
                )
            ],
            approval_deadline_hours=72
        )
        overdue_task.config_json = config.dict()
        
        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [overdue_task]
        mock_db.execute.return_value = mock_result
        
        # Check violations
        violations = await escalation_service.check_sla_violations(mock_db)
        
        assert len(violations) == 1
        assert violations[0]["task_id"] == str(overdue_task.id)
        assert violations[0]["hours_overdue"] > 0
        assert violations[0]["title"] == "Overdue Approval"
    
    @pytest.mark.asyncio
    async def test_get_escalation_metrics(self, escalation_service, mock_db):
        """Test getting escalation metrics"""
        # Mock escalation history
        escalations = [
            MagicMock(
                action="escalated",
                details={"trigger": "time_expired", "rule_type": "time_based"},
                created_at=datetime.utcnow()
            ),
            MagicMock(
                action="escalated",
                details={"trigger": "rejection", "rule_type": "rejection_based"},
                created_at=datetime.utcnow()
            )
        ]
        
        auto_approvals = [
            MagicMock(action="auto_approved", created_at=datetime.utcnow())
        ]
        
        # Mock database queries
        mock_result1 = AsyncMock()
        mock_result1.scalars.return_value.all.return_value = escalations
        
        mock_result2 = AsyncMock()
        mock_result2.scalars.return_value.all.return_value = auto_approvals
        
        mock_db.execute.side_effect = [mock_result1, mock_result2]
        
        # Get metrics
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        metrics = await escalation_service.get_escalation_metrics(
            start_date, end_date, mock_db
        )
        
        assert metrics["total_escalations"] == 2
        assert metrics["trigger_breakdown"]["time_expired"] == 1
        assert metrics["trigger_breakdown"]["rejection"] == 1
        assert metrics["type_breakdown"]["time_based"] == 1
        assert metrics["type_breakdown"]["rejection_based"] == 1
        assert metrics["auto_approvals"] == 1
    
    @pytest.mark.asyncio
    async def test_notification_on_escalation(
        self, escalation_service, sample_approval_task, time_based_rule, mock_db
    ):
        """Test that notifications are sent on escalation"""
        with patch.object(
            escalation_service.notification_service,
            'send_notification',
            new_callable=AsyncMock
        ) as mock_notify:
            # Execute escalation
            await escalation_service._execute_escalation(
                sample_approval_task,
                time_based_rule,
                EscalationTrigger.TIME_EXPIRED,
                mock_db
            )
            
            # Verify notification was sent
            assert mock_notify.called
            call_args = mock_notify.call_args[1]
            assert call_args["user_id"] == "manager"
            assert call_args["title"] == "Approval Escalation"
            assert call_args["priority"] == NotificationPriority.HIGH
    
    @pytest.mark.asyncio
    async def test_escalation_monitor_cancellation(
        self, escalation_service, sample_approval_task, time_based_rule, mock_db
    ):
        """Test that escalation monitors can be cancelled"""
        # Apply escalation rules
        await escalation_service.apply_escalation_rules(
            sample_approval_task, [time_based_rule], mock_db
        )
        
        task_id = str(sample_approval_task.id)
        assert task_id in escalation_service.escalation_monitors
        
        # Cancel monitor
        escalation_service.escalation_monitors[task_id].cancel()
        
        # Wait a bit for cancellation
        await asyncio.sleep(0.1)
        
        # Check monitor is cancelled
        assert escalation_service.escalation_monitors[task_id].cancelled()
        
        # Cleanup
        escalation_service.cleanup_monitors()
        assert len(escalation_service.escalation_monitors) == 0
    
    def test_cleanup_monitors(self, escalation_service):
        """Test cleanup of all escalation monitors"""
        # Create some mock monitors
        for i in range(3):
            task = AsyncMock()
            task.done.return_value = False
            task.cancel = MagicMock()
            escalation_service.escalation_monitors[f"task_{i}"] = task
        
        # Cleanup
        escalation_service.cleanup_monitors()
        
        # Verify all monitors were cancelled
        assert len(escalation_service.escalation_monitors) == 0