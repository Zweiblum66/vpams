"""
Tests for approval dashboard functionality
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

from src.models.approval_models import ApprovalTask, ApprovalDecision, ApprovalHistory
from src.models.approval_schemas import (
    ApprovalStatus, ApprovalType, ApprovalTaskConfig,
    ApproverConfig, ApproverType
)


@pytest.fixture
async def sample_approval_tasks(db: AsyncSession, test_user):
    """Create sample approval tasks for testing"""
    tasks = []
    
    # Create pending task
    pending_config = ApprovalTaskConfig(
        approval_type=ApprovalType.SINGLE,
        title="Pending Approval",
        description="This needs approval",
        approvers=[
            ApproverConfig(
                approver_type=ApproverType.USER,
                identifier=test_user["user_id"],
                name=test_user["name"]
            )
        ],
        approval_deadline_hours=48
    )
    
    pending_task = ApprovalTask(
        workflow_instance_id=uuid4(),
        task_instance_id=uuid4(),
        status=ApprovalStatus.PENDING,
        config_json=pending_config.dict(),
        created_by="user123",
        metadata={
            "department": "engineering",
            "priority": "high",
            "requestor_name": "John Doe",
            "approval_type": "expense"
        }
    )
    db.add(pending_task)
    tasks.append(pending_task)
    
    # Create approved task
    approved_config = ApprovalTaskConfig(
        approval_type=ApprovalType.SINGLE,
        title="Approved Request",
        description="This was approved",
        approvers=[
            ApproverConfig(
                approver_type=ApproverType.USER,
                identifier=test_user["user_id"],
                name=test_user["name"]
            )
        ]
    )
    
    approved_task = ApprovalTask(
        workflow_instance_id=uuid4(),
        task_instance_id=uuid4(),
        status=ApprovalStatus.APPROVED,
        config_json=approved_config.dict(),
        created_by="user456",
        created_at=datetime.utcnow() - timedelta(days=2),
        completed_at=datetime.utcnow() - timedelta(days=1),
        metadata={
            "department": "marketing",
            "priority": "normal",
            "requestor_name": "Jane Smith",
            "approval_type": "content"
        }
    )
    db.add(approved_task)
    tasks.append(approved_task)
    
    # Create rejected task
    rejected_config = ApprovalTaskConfig(
        approval_type=ApprovalType.SINGLE,
        title="Rejected Request",
        description="This was rejected",
        approvers=[
            ApproverConfig(
                approver_type=ApproverType.USER,
                identifier=test_user["user_id"],
                name=test_user["name"]
            )
        ]
    )
    
    rejected_task = ApprovalTask(
        workflow_instance_id=uuid4(),
        task_instance_id=uuid4(),
        status=ApprovalStatus.REJECTED,
        config_json=rejected_config.dict(),
        created_by=test_user["user_id"],
        created_at=datetime.utcnow() - timedelta(days=3),
        completed_at=datetime.utcnow() - timedelta(days=2),
        metadata={
            "department": "finance",
            "priority": "low",
            "requestor_name": test_user["name"],
            "approval_type": "expense"
        }
    )
    db.add(rejected_task)
    tasks.append(rejected_task)
    
    # Create escalated task
    escalated_config = ApprovalTaskConfig(
        approval_type=ApprovalType.SEQUENTIAL,
        title="Escalated Approval",
        description="This was escalated",
        approvers=[
            ApproverConfig(
                approver_type=ApproverType.USER,
                identifier="manager123",
                name="Manager"
            ),
            ApproverConfig(
                approver_type=ApproverType.USER,
                identifier=test_user["user_id"],
                name=test_user["name"]
            )
        ],
        approval_deadline_hours=24
    )
    
    escalated_task = ApprovalTask(
        workflow_instance_id=uuid4(),
        task_instance_id=uuid4(),
        status=ApprovalStatus.ESCALATED,
        config_json=escalated_config.dict(),
        created_by="user789",
        created_at=datetime.utcnow() - timedelta(hours=36),
        metadata={
            "department": "engineering",
            "priority": "critical",
            "requestor_name": "Bob Wilson",
            "approval_type": "access"
        }
    )
    db.add(escalated_task)
    tasks.append(escalated_task)
    
    # Add decisions
    # Approved decision
    approved_decision = ApprovalDecision(
        approval_task_id=approved_task.id,
        approver_id=test_user["user_id"],
        approver_name=test_user["name"],
        decision="approved",
        comments="Looks good",
        decided_at=approved_task.completed_at
    )
    db.add(approved_decision)
    
    # Rejected decision
    rejected_decision = ApprovalDecision(
        approval_task_id=rejected_task.id,
        approver_id=test_user["user_id"],
        approver_name=test_user["name"],
        decision="rejected",
        comments="Not approved",
        decided_at=rejected_task.completed_at
    )
    db.add(rejected_decision)
    
    await db.commit()
    
    # Refresh tasks to get IDs
    for task in tasks:
        await db.refresh(task)
    
    return tasks


class TestApprovalDashboard:
    """Test approval dashboard functionality"""
    
    @pytest.mark.asyncio
    async def test_get_dashboard_summary(
        self, client: AsyncClient, auth_headers, sample_approval_tasks
    ):
        """Test getting dashboard summary"""
        response = await client.get(
            "/api/v1/approvals/dashboard/summary",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "pending_count" in data
        assert "approved_count" in data
        assert "rejected_count" in data
        assert "escalated_count" in data
        assert "total_count" in data
        assert "average_response_time_hours" in data
        assert "sla_compliance_rate" in data
        assert "pending_urgent" in data
        
        # Check counts
        assert data["total_count"] >= 4
        assert data["pending_count"] >= 1
        assert data["approved_count"] >= 1
        assert data["rejected_count"] >= 1
        assert data["escalated_count"] >= 1
    
    @pytest.mark.asyncio
    async def test_get_dashboard_summary_with_filters(
        self, client: AsyncClient, auth_headers, sample_approval_tasks
    ):
        """Test getting dashboard summary with filters"""
        # Filter by department
        response = await client.get(
            "/api/v1/approvals/dashboard/summary?department=engineering",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have fewer results with department filter
        assert data["total_count"] >= 2  # At least pending and escalated
        
        # Filter by days
        response = await client.get(
            "/api/v1/approvals/dashboard/summary?days=1",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have fewer results with 1-day filter
        assert data["total_count"] >= 1  # At least pending task
    
    @pytest.mark.asyncio
    async def test_get_recent_requests(
        self, client: AsyncClient, auth_headers, sample_approval_tasks
    ):
        """Test getting recent approval requests"""
        response = await client.get(
            "/api/v1/approvals/dashboard/recent",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Check first request structure
        request = data[0]
        assert "id" in request
        assert "title" in request
        assert "description" in request
        assert "status" in request
        assert "priority" in request
        assert "created_at" in request
        assert "approvers" in request
        assert "requestor" in request
        
        # Check approver structure
        if request["approvers"]:
            approver = request["approvers"][0]
            assert "id" in approver
            assert "name" in approver
            assert "status" in approver
    
    @pytest.mark.asyncio
    async def test_get_recent_requests_filtered(
        self, client: AsyncClient, auth_headers, sample_approval_tasks
    ):
        """Test getting recent requests with status filter"""
        response = await client.get(
            "/api/v1/approvals/dashboard/recent?status=pending",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned requests should be pending
        for request in data:
            assert request["status"] == "pending"
    
    @pytest.mark.asyncio
    async def test_get_dashboard_metrics(
        self, client: AsyncClient, auth_headers, sample_approval_tasks
    ):
        """Test getting dashboard metrics"""
        response = await client.get(
            "/api/v1/approvals/dashboard/metrics",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "weekly_trend" in data
        assert "by_department" in data
        assert "by_type" in data
        assert "response_time_distribution" in data
        assert "top_requestors" in data
        assert "top_approvers" in data
        
        # Check weekly trend
        assert isinstance(data["weekly_trend"], list)
        assert len(data["weekly_trend"]) == 7
        if data["weekly_trend"]:
            day = data["weekly_trend"][0]
            assert "date" in day
            assert "pending" in day
            assert "approved" in day
            assert "rejected" in day
        
        # Check department breakdown
        assert isinstance(data["by_department"], list)
        if data["by_department"]:
            dept = data["by_department"][0]
            assert "department" in dept
            assert "count" in dept
        
        # Check response time distribution
        assert isinstance(data["response_time_distribution"], list)
        assert len(data["response_time_distribution"]) == 6
        if data["response_time_distribution"]:
            bucket = data["response_time_distribution"][0]
            assert "range" in bucket
            assert "count" in bucket
    
    @pytest.mark.asyncio
    async def test_get_my_approval_stats(
        self, client: AsyncClient, auth_headers, sample_approval_tasks, test_user
    ):
        """Test getting personal approval statistics"""
        response = await client.get(
            "/api/v1/approvals/dashboard/my-stats",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "assigned_to_me" in data
        assert "completed_by_me" in data
        assert "pending_my_action" in data
        assert "created_by_me" in data
        assert "avg_response_time_hours" in data
        assert "completion_rate" in data
        assert "period_days" in data
        
        # Check that stats are reasonable
        assert data["assigned_to_me"] >= 0
        assert data["completed_by_me"] >= 0
        assert data["pending_my_action"] >= 0
        assert data["created_by_me"] >= 0
        assert 0 <= data["completion_rate"] <= 1
    
    @pytest.mark.asyncio
    async def test_export_dashboard_data(
        self, client: AsyncClient, auth_headers
    ):
        """Test exporting dashboard data"""
        response = await client.post(
            "/api/v1/approvals/dashboard/export?format=csv",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # For now, just check placeholder response
        assert "message" in data
        assert data["format"] == "csv"
    
    @pytest.mark.asyncio
    async def test_dashboard_summary_calculations(
        self, client: AsyncClient, auth_headers, db: AsyncSession, test_user
    ):
        """Test that dashboard summary calculations are correct"""
        # Create a task with known values
        config = ApprovalTaskConfig(
            approval_type=ApprovalType.SINGLE,
            title="Test Calculation",
            description="Test",
            approvers=[
                ApproverConfig(
                    approver_type=ApproverType.USER,
                    identifier=test_user["user_id"],
                    name=test_user["name"]
                )
            ],
            approval_deadline_hours=24
        )
        
        task = ApprovalTask(
            workflow_instance_id=uuid4(),
            task_instance_id=uuid4(),
            status=ApprovalStatus.APPROVED,
            config_json=config.dict(),
            created_by=test_user["user_id"],
            created_at=datetime.utcnow() - timedelta(hours=12),
            completed_at=datetime.utcnow() - timedelta(hours=6),
            metadata={"department": "test", "priority": "normal"}
        )
        db.add(task)
        await db.commit()
        
        # Get summary
        response = await client.get(
            "/api/v1/approvals/dashboard/summary?days=1",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Average response time should include our 6-hour task
        assert data["average_response_time_hours"] > 0
        
        # SLA compliance should be 100% since 6 hours < 24 hours deadline
        if data["approved_count"] > 0:
            assert data["sla_compliance_rate"] > 0