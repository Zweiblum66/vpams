"""
Tests for approval routing service
"""

import pytest
from datetime import datetime
from typing import Dict, Any

from src.services.approval_routing_service import ApprovalRoutingService, RoutingRule
from src.models.approval_schemas import (
    ApprovalType, ApproverType, VotingStrategy, EscalationType
)


@pytest.fixture
def routing_service():
    """Create routing service instance"""
    return ApprovalRoutingService()


class TestApprovalRoutingService:
    """Test approval routing functionality"""
    
    @pytest.mark.asyncio
    async def test_route_small_expense(self, routing_service):
        """Test routing for small expense approval"""
        context = {
            "approval_type": "expense",
            "amount": 500,
            "department": "engineering",
            "urgency": "normal",
            "title": "Office supplies",
            "description": "Purchase of office supplies"
        }
        
        config = await routing_service.route_approval(context)
        
        assert config.approval_type == ApprovalType.SINGLE
        assert len(config.approvers) == 1
        assert config.approvers[0].identifier == "engineering_manager"
        assert config.approval_deadline_hours == 72
    
    @pytest.mark.asyncio
    async def test_route_medium_expense(self, routing_service):
        """Test routing for medium expense approval"""
        context = {
            "approval_type": "expense",
            "amount": 5000,
            "department": "marketing",
            "urgency": "normal",
            "title": "Marketing campaign",
            "description": "Digital marketing campaign"
        }
        
        config = await routing_service.route_approval(context)
        
        assert config.approval_type == ApprovalType.SEQUENTIAL
        assert len(config.approvers) == 2
        assert config.approvers[0].identifier == "marketing_manager"
        assert config.approvers[1].identifier == "finance_analyst"
    
    @pytest.mark.asyncio
    async def test_route_high_expense(self, routing_service):
        """Test routing for high expense approval"""
        context = {
            "approval_type": "expense",
            "amount": 25000,
            "department": "engineering",
            "urgency": "normal",
            "title": "Server upgrade",
            "description": "Production server upgrade"
        }
        
        config = await routing_service.route_approval(context)
        
        assert config.approval_type == ApprovalType.SEQUENTIAL
        assert len(config.approvers) == 3
        assert config.approvers[0].identifier == "engineering_manager"
        assert config.approvers[1].identifier == "finance_manager"
        assert config.approvers[2].identifier == "vp_engineering"
    
    @pytest.mark.asyncio
    async def test_route_very_high_expense(self, routing_service):
        """Test routing for very high expense approval"""
        context = {
            "approval_type": "expense",
            "amount": 75000,
            "department": "operations",
            "urgency": "normal",
            "title": "Infrastructure investment",
            "description": "Major infrastructure upgrade"
        }
        
        config = await routing_service.route_approval(context)
        
        assert config.approval_type == ApprovalType.SEQUENTIAL
        assert len(config.approvers) == 4
        assert config.approvers[3].identifier == "cfo"
    
    @pytest.mark.asyncio
    async def test_route_executive_expense(self, routing_service):
        """Test routing for executive-level expense approval"""
        context = {
            "approval_type": "expense",
            "amount": 150000,
            "department": "executive",
            "urgency": "normal",
            "title": "Acquisition",
            "description": "Company acquisition"
        }
        
        config = await routing_service.route_approval(context)
        
        assert config.approval_type == ApprovalType.SEQUENTIAL
        assert len(config.approvers) >= 4
        assert config.approvers[-1].identifier == "ceo"
    
    @pytest.mark.asyncio
    async def test_route_content_standard(self, routing_service):
        """Test routing for standard content approval"""
        context = {
            "approval_type": "content",
            "content_type": "blog",
            "sensitivity": "normal",
            "title": "Blog post",
            "description": "Monthly blog post"
        }
        
        config = await routing_service.route_approval(context)
        
        assert len(config.approvers) >= 1
        assert config.approvers[0].identifier == "content_review_team"
    
    @pytest.mark.asyncio
    async def test_route_content_sensitive(self, routing_service):
        """Test routing for sensitive content approval"""
        context = {
            "approval_type": "content",
            "content_type": "legal",
            "sensitivity": "high",
            "title": "Legal document",
            "description": "Legal compliance document"
        }
        
        config = await routing_service.route_approval(context)
        
        assert config.approval_type == ApprovalType.SEQUENTIAL
        assert len(config.approvers) >= 2
        assert any(a.identifier == "legal_counsel" for a in config.approvers)
    
    @pytest.mark.asyncio
    async def test_route_content_marketing(self, routing_service):
        """Test routing for marketing content approval"""
        context = {
            "approval_type": "content",
            "content_type": "marketing",
            "external_publish": True,
            "title": "Marketing campaign",
            "description": "External marketing campaign"
        }
        
        config = await routing_service.route_approval(context)
        
        assert config.approval_type == ApprovalType.PARALLEL
        assert config.voting_strategy == VotingStrategy.MAJORITY
        assert any(a.identifier == "marketing_lead" for a in config.approvers)
        assert any(a.identifier == "marketing_manager" for a in config.approvers)
    
    @pytest.mark.asyncio
    async def test_route_access_standard(self, routing_service):
        """Test routing for standard access request"""
        context = {
            "approval_type": "access",
            "access_level": "read",
            "resource_type": "general",
            "department": "engineering",
            "title": "Read access",
            "description": "Read access to documentation"
        }
        
        config = await routing_service.route_approval(context)
        
        assert config.approval_type == ApprovalType.SINGLE
        assert len(config.approvers) == 1
        assert config.approval_deadline_hours == 24
    
    @pytest.mark.asyncio
    async def test_route_access_admin(self, routing_service):
        """Test routing for admin access request"""
        context = {
            "approval_type": "access",
            "access_level": "admin",
            "resource_type": "sensitive",
            "department": "it",
            "title": "Admin access",
            "description": "Admin access to production systems"
        }
        
        config = await routing_service.route_approval(context)
        
        assert config.approval_type == ApprovalType.SEQUENTIAL
        assert len(config.approvers) >= 2
        assert any(a.identifier == "security_officer" for a in config.approvers)
    
    @pytest.mark.asyncio
    async def test_route_project_small(self, routing_service):
        """Test routing for small project approval"""
        context = {
            "approval_type": "project",
            "scope": "small",
            "budget": 5000,
            "departments": ["engineering"],
            "title": "Small project",
            "description": "Department improvement project"
        }
        
        config = await routing_service.route_approval(context)
        
        assert config.approval_type == ApprovalType.SINGLE
        assert len(config.approvers) == 1
        assert config.approvers[0].identifier == "engineering_lead"
    
    @pytest.mark.asyncio
    async def test_route_project_department(self, routing_service):
        """Test routing for department project approval"""
        context = {
            "approval_type": "project",
            "scope": "department",
            "budget": 25000,
            "departments": ["marketing"],
            "title": "Department project",
            "description": "Marketing department initiative"
        }
        
        config = await routing_service.route_approval(context)
        
        assert config.approval_type == ApprovalType.SEQUENTIAL
        assert len(config.approvers) >= 2
        assert config.approvers[0].identifier == "marketing_manager"
        assert config.approvers[1].identifier == "vp_marketing"
        # Should include finance for budget > 10k
        assert any(a.identifier == "finance_analyst" for a in config.approvers)
    
    @pytest.mark.asyncio
    async def test_route_project_enterprise(self, routing_service):
        """Test routing for enterprise project approval"""
        context = {
            "approval_type": "project",
            "scope": "enterprise",
            "budget": 200000,
            "departments": ["engineering", "marketing", "operations"],
            "title": "Enterprise project",
            "description": "Company-wide transformation"
        }
        
        config = await routing_service.route_approval(context)
        
        assert config.approval_type == ApprovalType.VOTING
        assert config.voting_strategy == VotingStrategy.MAJORITY
        assert config.approval_threshold == 0.66
        assert len(config.approvers) >= 3
        assert any(a.identifier == "cfo" for a in config.approvers)
    
    @pytest.mark.asyncio
    async def test_urgency_escalation(self, routing_service):
        """Test escalation rules based on urgency"""
        # High urgency
        context = {
            "approval_type": "expense",
            "amount": 500,
            "department": "engineering",
            "urgency": "high",
            "title": "Urgent expense",
            "description": "Urgent purchase"
        }
        
        config = await routing_service.route_approval(context)
        
        assert len(config.escalation_rules) == 1
        assert config.escalation_rules[0].escalation_type == EscalationType.TIME_BASED
        assert config.escalation_rules[0].trigger_after_hours == 24
        
        # Critical urgency
        context["urgency"] = "critical"
        config = await routing_service.route_approval(context)
        
        assert len(config.escalation_rules) == 1
        assert config.escalation_rules[0].trigger_after_hours == 4
        assert config.escalation_rules[0].escalate_to.identifier == "ceo"
    
    @pytest.mark.asyncio
    async def test_routing_overrides(self, routing_service):
        """Test applying routing overrides"""
        context = {
            "approval_type": "expense",
            "amount": 500,
            "department": "engineering",
            "title": "Expense",
            "description": "Test expense"
        }
        
        overrides = {
            "approval_type": "sequential",
            "additional_approvers": [
                {
                    "approver_type": "user",
                    "identifier": "john.doe",
                    "name": "John Doe"
                }
            ],
            "deadline_hours": 48
        }
        
        config = await routing_service.route_approval(context, overrides)
        
        assert config.approval_type == ApprovalType.SEQUENTIAL
        assert len(config.approvers) == 2
        assert config.approvers[1].identifier == "john.doe"
        assert config.approval_deadline_hours == 48
    
    @pytest.mark.asyncio
    async def test_get_routing_rules(self, routing_service):
        """Test getting routing rules"""
        rules = await routing_service.get_routing_rules()
        
        assert len(rules) > 0
        assert all("id" in rule for rule in rules)
        assert all("type" in rule for rule in rules)
        assert all("condition" in rule for rule in rules)
        
        # Filter by type
        expense_rules = await routing_service.get_routing_rules("expense")
        assert all(rule["type"] == "expense" for rule in expense_rules)
    
    @pytest.mark.asyncio
    async def test_test_routing(self, routing_service):
        """Test the routing test functionality"""
        test_context = {
            "approval_type": "expense",
            "amount": 15000,
            "department": "finance",
            "title": "Test",
            "description": "Test"
        }
        
        result = await routing_service.test_routing(test_context)
        
        assert result["success"] is True
        assert result["approval_type"] == "sequential"
        assert result["approver_count"] == 3
        assert "approvers" in result
        assert "deadline_hours" in result
        assert "voting_strategy" in result
    
    @pytest.mark.asyncio
    async def test_suggest_approvers(self, routing_service):
        """Test approver suggestions"""
        context = {
            "department": "engineering",
            "approval_type": "expense"
        }
        
        suggestions = await routing_service.suggest_approvers(context, max_suggestions=3)
        
        assert len(suggestions) <= 3
        assert all(hasattr(s, "identifier") for s in suggestions)
        assert all(hasattr(s, "name") for s in suggestions)
        
        # Should include department hierarchy
        identifiers = [s.identifier for s in suggestions]
        assert any(id in identifiers for id in ["team_lead", "engineering_manager"])
    
    @pytest.mark.asyncio
    async def test_default_routing(self, routing_service):
        """Test default routing for unknown approval types"""
        context = {
            "approval_type": "unknown_type",
            "department": "operations",
            "title": "Unknown",
            "description": "Unknown approval type"
        }
        
        config = await routing_service.route_approval(context)
        
        assert config.approval_type == ApprovalType.SINGLE
        assert len(config.approvers) == 1
        assert config.approvers[0].identifier == "ops_manager"
    
    def test_routing_rule_matching(self):
        """Test routing rule condition matching"""
        rule = RoutingRule(
            rule_id="test_rule",
            name="Test Rule",
            conditions={
                "amount": {"operator": "greater_than", "value": 1000},
                "department": "engineering"
            },
            actions={
                "add_approver": {
                    "approver_type": "role",
                    "identifier": "finance_manager",
                    "name": "Finance Manager"
                }
            }
        )
        
        # Should match
        context1 = {"amount": 1500, "department": "engineering"}
        assert rule.matches(context1) is True
        
        # Should not match - amount too low
        context2 = {"amount": 500, "department": "engineering"}
        assert rule.matches(context2) is False
        
        # Should not match - wrong department
        context3 = {"amount": 1500, "department": "marketing"}
        assert rule.matches(context3) is False
    
    @pytest.mark.asyncio
    async def test_financial_access_routing(self, routing_service):
        """Test special routing for financial resource access"""
        context = {
            "approval_type": "access",
            "access_level": "read",
            "resource_type": "financial",
            "department": "accounting",
            "title": "Financial data access",
            "description": "Access to financial reports"
        }
        
        config = await routing_service.route_approval(context)
        
        # Should include finance approver for financial resources
        assert any(a.identifier == "finance_manager" for a in config.approvers)