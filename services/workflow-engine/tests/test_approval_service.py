"""
Tests for approval workflow service
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from src.services.approval_service import ApprovalService
from src.models.approval_schemas import (
    ApprovalStatus, ApprovalType, CreateApprovalRequest, ApprovalTaskConfig,
    ApproverConfig, ApproverType, UpdateApprovalDecision, DelegateApprovalRequest,
    ApprovalSearchRequest, VotingStrategy, EscalationRule, EscalationType
)
from src.core.exceptions import WorkflowException


@pytest.fixture
def approval_service():
    """Create approval service instance"""
    return ApprovalService()


@pytest.fixture
def mock_db():
    """Create mock database session"""
    db = AsyncMock()
    return db


@pytest.fixture
def sample_approval_config():
    """Create sample approval configuration"""
    return ApprovalTaskConfig(
        approval_type=ApprovalType.SINGLE,
        title="Test Approval",
        description="Test approval description",
        approvers=[
            ApproverConfig(
                approver_type=ApproverType.USER,
                identifier="approver_1",
                name="Approver One",
                email="approver1@example.com"
            )
        ],
        approval_deadline_hours=24,
        send_initial_notification=True
    )


@pytest.fixture
def sample_create_request(sample_approval_config):
    """Create sample approval creation request"""
    return CreateApprovalRequest(
        workflow_instance_id="workflow_123",
        task_instance_id="task_456",
        title="Test Approval Request",
        description="This is a test approval",
        approval_config=sample_approval_config,
        context_data={"key": "value"},
        tags=["test", "approval"]
    )


class TestApprovalService:
    """Test approval service functionality"""
    
    @pytest.mark.asyncio
    async def test_create_approval_request(
        self, approval_service, mock_db, sample_create_request
    ):
        """Test creating an approval request"""
        # Mock workflow and task instances
        workflow_instance = MagicMock()
        workflow_instance.instance_id = "workflow_123"
        
        task_instance = MagicMock()
        task_instance.task_instance_id = "task_456"
        
        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            workflow_instance, task_instance
        ]
        
        # Create approval
        approval = await approval_service.create_approval_request(
            db=mock_db,
            user_id="user_123",
            request=sample_create_request
        )
        
        # Verify approval was created
        assert approval.workflow_instance_id == "workflow_123"
        assert approval.task_instance_id == "task_456"
        assert approval.title == "Test Approval Request"
        assert approval.status == ApprovalStatus.PENDING
        assert approval.requestor_id == "user_123"
        assert len(approval.approval_config.approvers) == 1
        assert approval.deadline_at is not None
    
    @pytest.mark.asyncio
    async def test_update_approval_decision(self, approval_service, mock_db):
        """Test updating an approval decision"""
        # Create an approval first
        approval_config = ApprovalTaskConfig(
            approval_type=ApprovalType.SINGLE,
            title="Test",
            description="Test",
            approvers=[
                ApproverConfig(
                    approver_type=ApproverType.USER,
                    identifier="approver_1",
                    name="Approver One"
                )
            ]
        )
        
        # Manually add approval to store
        approval_request = await approval_service.create_approval_request(
            db=mock_db,
            user_id="user_123",
            request=CreateApprovalRequest(
                workflow_instance_id="wf_123",
                task_instance_id="task_123",
                title="Test",
                description="Test",
                approval_config=approval_config
            )
        )
        
        # Make decision
        decision_update = UpdateApprovalDecision(
            decision=ApprovalStatus.APPROVED,
            comments="Looks good to me"
        )
        
        decision = await approval_service.update_approval_decision(
            request_id=approval_request.request_id,
            approver_id="approver_1",
            decision_update=decision_update
        )
        
        # Verify decision
        assert decision.decision == ApprovalStatus.APPROVED
        assert decision.comments == "Looks good to me"
        assert decision.approver_id == "approver_1"
        
        # Check approval status
        updated_approval = await approval_service.get_approval_request(
            approval_request.request_id
        )
        assert updated_approval.status == ApprovalStatus.APPROVED
    
    @pytest.mark.asyncio
    async def test_parallel_approval_voting(self, approval_service, mock_db):
        """Test parallel approval with voting"""
        # Create parallel approval with voting
        approval_config = ApprovalTaskConfig(
            approval_type=ApprovalType.VOTING,
            title="Voting Approval",
            description="Test voting",
            approvers=[
                ApproverConfig(
                    approver_type=ApproverType.USER,
                    identifier="approver_1",
                    name="Approver One",
                    vote_weight=1.0
                ),
                ApproverConfig(
                    approver_type=ApproverType.USER,
                    identifier="approver_2",
                    name="Approver Two",
                    vote_weight=1.0
                ),
                ApproverConfig(
                    approver_type=ApproverType.USER,
                    identifier="approver_3",
                    name="Approver Three",
                    vote_weight=2.0  # Double weight
                )
            ],
            voting_strategy=VotingStrategy.MAJORITY
        )
        
        approval_request = await approval_service.create_approval_request(
            db=mock_db,
            user_id="user_123",
            request=CreateApprovalRequest(
                workflow_instance_id="wf_123",
                task_instance_id="task_123",
                title="Voting Test",
                description="Test",
                approval_config=approval_config
            )
        )
        
        # First approver approves (weight 1.0)
        await approval_service.update_approval_decision(
            request_id=approval_request.request_id,
            approver_id="approver_1",
            decision_update=UpdateApprovalDecision(
                decision=ApprovalStatus.APPROVED
            )
        )
        
        # Still pending - need more votes
        approval = await approval_service.get_approval_request(
            approval_request.request_id
        )
        assert approval.status == ApprovalStatus.PENDING
        
        # Third approver approves (weight 2.0)
        await approval_service.update_approval_decision(
            request_id=approval_request.request_id,
            approver_id="approver_3",
            decision_update=UpdateApprovalDecision(
                decision=ApprovalStatus.APPROVED
            )
        )
        
        # Should be approved now (3.0 out of 4.0 total weight)
        approval = await approval_service.get_approval_request(
            approval_request.request_id
        )
        assert approval.status == ApprovalStatus.APPROVED
    
    @pytest.mark.asyncio
    async def test_delegate_approval(self, approval_service, mock_db):
        """Test delegating an approval"""
        # Create approval with delegation allowed
        approval_config = ApprovalTaskConfig(
            approval_type=ApprovalType.SINGLE,
            title="Test",
            description="Test",
            approvers=[
                ApproverConfig(
                    approver_type=ApproverType.USER,
                    identifier="approver_1",
                    name="Original Approver",
                    can_delegate=True
                )
            ]
        )
        
        approval_request = await approval_service.create_approval_request(
            db=mock_db,
            user_id="user_123",
            request=CreateApprovalRequest(
                workflow_instance_id="wf_123",
                task_instance_id="task_123",
                title="Test",
                description="Test",
                approval_config=approval_config
            )
        )
        
        # Delegate to another user
        new_approver = ApproverConfig(
            approver_type=ApproverType.USER,
            identifier="approver_2",
            name="Delegated Approver",
            email="approver2@example.com"
        )
        
        delegation_request = DelegateApprovalRequest(
            delegate_to=new_approver,
            delegation_reason="Out of office",
            retain_visibility=True
        )
        
        updated_approval = await approval_service.delegate_approval(
            request_id=approval_request.request_id,
            approver_id="approver_1",
            delegation=delegation_request
        )
        
        # Verify delegation
        assert len(updated_approval.approval_config.approvers) == 1
        assert updated_approval.approval_config.approvers[0].identifier == "approver_2"
        assert "delegations" in updated_approval.metadata
    
    @pytest.mark.asyncio
    async def test_escalate_approval(self, approval_service, mock_db):
        """Test escalating an approval"""
        # Create approval with escalation rule
        escalation_rule = EscalationRule(
            escalation_type=EscalationType.TIME_BASED,
            trigger_after_hours=1,
            escalate_to=ApproverConfig(
                approver_type=ApproverType.USER,
                identifier="manager_1",
                name="Manager"
            ),
            escalation_message="Urgent: Please review this approval"
        )
        
        approval_config = ApprovalTaskConfig(
            approval_type=ApprovalType.SINGLE,
            title="Test",
            description="Test",
            approvers=[
                ApproverConfig(
                    approver_type=ApproverType.USER,
                    identifier="approver_1",
                    name="Original Approver"
                )
            ],
            escalation_rules=[escalation_rule]
        )
        
        approval_request = await approval_service.create_approval_request(
            db=mock_db,
            user_id="user_123",
            request=CreateApprovalRequest(
                workflow_instance_id="wf_123",
                task_instance_id="task_123",
                title="Test",
                description="Test",
                approval_config=approval_config
            )
        )
        
        # Escalate the approval
        escalated_approval = await approval_service.escalate_approval(
            request_id=approval_request.request_id,
            escalation_rule=escalation_rule
        )
        
        # Verify escalation
        assert escalated_approval.status == ApprovalStatus.ESCALATED
        assert escalated_approval.current_escalation_level == 1
        assert len(escalated_approval.approval_config.approvers) == 2
        assert len(escalated_approval.escalation_history) == 1
    
    @pytest.mark.asyncio
    async def test_search_approvals(self, approval_service, mock_db):
        """Test searching for approvals"""
        # Create multiple approvals
        for i in range(5):
            await approval_service.create_approval_request(
                db=mock_db,
                user_id=f"user_{i}",
                request=CreateApprovalRequest(
                    workflow_instance_id=f"wf_{i}",
                    task_instance_id=f"task_{i}",
                    title=f"Approval {i}",
                    description=f"Test approval {i}",
                    approval_config=ApprovalTaskConfig(
                        approval_type=ApprovalType.SINGLE,
                        title=f"Config {i}",
                        description="Test",
                        approvers=[
                            ApproverConfig(
                                approver_type=ApproverType.USER,
                                identifier=f"approver_{i % 2}",  # Alternate approvers
                                name=f"Approver {i % 2}"
                            )
                        ]
                    ),
                    tags=["test"] if i % 2 == 0 else ["other"]
                )
            )
        
        # Search by approver
        search_request = ApprovalSearchRequest(
            approver_id="approver_0",
            page=1,
            page_size=10
        )
        
        results = await approval_service.search_approvals(search_request)
        assert results.total == 3  # approver_0 has approvals 0, 2, 4
        
        # Search by tags
        search_request = ApprovalSearchRequest(
            tags=["test"],
            page=1,
            page_size=10
        )
        
        results = await approval_service.search_approvals(search_request)
        assert results.total == 3  # Approvals 0, 2, 4 have "test" tag
    
    @pytest.mark.asyncio
    async def test_approval_dashboard(self, approval_service, mock_db):
        """Test getting approval dashboard"""
        # Create approvals for a user
        approver_config = ApproverConfig(
            approver_type=ApproverType.USER,
            identifier="user_123",
            name="Test User"
        )
        
        # Create pending approval
        await approval_service.create_approval_request(
            db=mock_db,
            user_id="other_user",
            request=CreateApprovalRequest(
                workflow_instance_id="wf_1",
                task_instance_id="task_1",
                title="Pending Approval",
                description="Test",
                approval_config=ApprovalTaskConfig(
                    approval_type=ApprovalType.SINGLE,
                    title="Test",
                    description="Test",
                    approvers=[approver_config]
                )
            )
        )
        
        # Get dashboard
        dashboard = await approval_service.get_approval_dashboard("user_123")
        
        assert dashboard.user_id == "user_123"
        assert dashboard.pending_count == 1
        assert len(dashboard.pending_approvals) == 1
    
    @pytest.mark.asyncio
    async def test_check_timeouts(self, approval_service, mock_db):
        """Test checking for approval timeouts"""
        # Create approval with short deadline
        approval_config = ApprovalTaskConfig(
            approval_type=ApprovalType.SINGLE,
            title="Test",
            description="Test",
            approvers=[
                ApproverConfig(
                    approver_type=ApproverType.USER,
                    identifier="approver_1",
                    name="Approver"
                )
            ],
            approval_deadline_hours=0,  # Already expired
            auto_reject_on_timeout=True
        )
        
        approval_request = await approval_service.create_approval_request(
            db=mock_db,
            user_id="user_123",
            request=CreateApprovalRequest(
                workflow_instance_id="wf_123",
                task_instance_id="task_123",
                title="Test",
                description="Test",
                approval_config=approval_config
            )
        )
        
        # Manually set deadline to past
        approval_request.deadline_at = datetime.utcnow() - timedelta(hours=1)
        
        # Check timeouts
        await approval_service.check_timeouts()
        
        # Verify approval was auto-rejected
        approval = await approval_service.get_approval_request(
            approval_request.request_id
        )
        assert approval.status == ApprovalStatus.REJECTED
        assert approval.final_decision == ApprovalStatus.REJECTED
        assert "Auto-rejected" in approval.final_comments
    
    @pytest.mark.asyncio
    async def test_sequential_approval(self, approval_service, mock_db):
        """Test sequential approval workflow"""
        # Create sequential approval
        approval_config = ApprovalTaskConfig(
            approval_type=ApprovalType.SEQUENTIAL,
            title="Sequential Approval",
            description="Test sequential",
            approvers=[
                ApproverConfig(
                    approver_type=ApproverType.USER,
                    identifier="approver_1",
                    name="Level 1 Approver"
                ),
                ApproverConfig(
                    approver_type=ApproverType.USER,
                    identifier="approver_2",
                    name="Level 2 Approver"
                ),
                ApproverConfig(
                    approver_type=ApproverType.USER,
                    identifier="approver_3",
                    name="Level 3 Approver"
                )
            ]
        )
        
        approval_request = await approval_service.create_approval_request(
            db=mock_db,
            user_id="user_123",
            request=CreateApprovalRequest(
                workflow_instance_id="wf_123",
                task_instance_id="task_123",
                title="Sequential Test",
                description="Test",
                approval_config=approval_config
            )
        )
        
        # First level approves
        await approval_service.update_approval_decision(
            request_id=approval_request.request_id,
            approver_id="approver_1",
            decision_update=UpdateApprovalDecision(
                decision=ApprovalStatus.APPROVED
            )
        )
        
        # Should still be pending
        approval = await approval_service.get_approval_request(
            approval_request.request_id
        )
        assert approval.status == ApprovalStatus.PENDING
        assert approval.current_level == 1
        
        # Second level rejects
        await approval_service.update_approval_decision(
            request_id=approval_request.request_id,
            approver_id="approver_2",
            decision_update=UpdateApprovalDecision(
                decision=ApprovalStatus.REJECTED,
                comments="Not approved"
            )
        )
        
        # Should be rejected
        approval = await approval_service.get_approval_request(
            approval_request.request_id
        )
        assert approval.status == ApprovalStatus.REJECTED
        assert approval.final_decision == ApprovalStatus.REJECTED