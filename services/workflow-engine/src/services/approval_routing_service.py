"""
Approval routing service for dynamic approver assignment
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
import json

from ..models.approval_schemas import (
    ApproverConfig, ApproverType, ApprovalTaskConfig, ApprovalType,
    EscalationRule, EscalationType, VotingStrategy
)
from ..core.exceptions import WorkflowException

logger = logging.getLogger(__name__)


class ApprovalRoutingService:
    """Service for routing approvals to appropriate approvers"""
    
    def __init__(self):
        # In-memory storage for routing rules (in production, use database)
        self.routing_rules: Dict[str, List[RoutingRule]] = {}
        self.approver_pools: Dict[str, List[ApproverConfig]] = {}
        self.department_hierarchy: Dict[str, List[str]] = {}
        self._init_default_data()
    
    def _init_default_data(self):
        """Initialize default routing data"""
        # Default department hierarchy
        self.department_hierarchy = {
            "engineering": ["team_lead", "engineering_manager", "vp_engineering", "cto"],
            "marketing": ["marketing_lead", "marketing_manager", "vp_marketing", "cmo"],
            "finance": ["finance_analyst", "finance_manager", "cfo"],
            "operations": ["ops_lead", "ops_manager", "coo"],
            "executive": ["ceo"]
        }
        
        # Default approver pools
        self.approver_pools = {
            "finance_approvers": [
                ApproverConfig(
                    approver_type=ApproverType.ROLE,
                    identifier="finance_analyst",
                    name="Finance Analyst",
                    email="finance.analyst@example.com"
                ),
                ApproverConfig(
                    approver_type=ApproverType.ROLE,
                    identifier="finance_manager",
                    name="Finance Manager",
                    email="finance.manager@example.com"
                ),
                ApproverConfig(
                    approver_type=ApproverType.ROLE,
                    identifier="cfo",
                    name="Chief Financial Officer",
                    email="cfo@example.com"
                )
            ],
            "content_approvers": [
                ApproverConfig(
                    approver_type=ApproverType.GROUP,
                    identifier="content_review_team",
                    name="Content Review Team",
                    email="content.review@example.com"
                ),
                ApproverConfig(
                    approver_type=ApproverType.ROLE,
                    identifier="content_manager",
                    name="Content Manager",
                    email="content.manager@example.com"
                )
            ],
            "legal_approvers": [
                ApproverConfig(
                    approver_type=ApproverType.ROLE,
                    identifier="legal_counsel",
                    name="Legal Counsel",
                    email="legal@example.com"
                )
            ]
        }
    
    async def route_approval(
        self,
        context: Dict[str, Any],
        routing_config: Optional[Dict[str, Any]] = None
    ) -> ApprovalTaskConfig:
        """
        Route approval based on context and rules
        
        Args:
            context: Approval context containing relevant data
            routing_config: Optional routing configuration
            
        Returns:
            ApprovalTaskConfig with determined approvers and settings
        """
        try:
            # Extract routing criteria from context
            amount = context.get("amount", 0)
            approval_type = context.get("approval_type", "general")
            department = context.get("department", "general")
            urgency = context.get("urgency", "normal")
            content_type = context.get("content_type")
            
            # Determine approval configuration
            approval_config = ApprovalTaskConfig(
                approval_type=ApprovalType.SEQUENTIAL,
                title=context.get("title", "Approval Request"),
                description=context.get("description", ""),
                approvers=[],
                escalation_rules=[]
            )
            
            # Route based on type
            if approval_type == "expense":
                approval_config = await self._route_expense_approval(
                    amount, department, urgency, approval_config
                )
            elif approval_type == "content":
                approval_config = await self._route_content_approval(
                    content_type, context, approval_config
                )
            elif approval_type == "access":
                approval_config = await self._route_access_approval(
                    context, approval_config
                )
            elif approval_type == "project":
                approval_config = await self._route_project_approval(
                    context, approval_config
                )
            else:
                # Default routing
                approval_config = await self._route_default_approval(
                    context, approval_config
                )
            
            # Apply routing config overrides if provided
            if routing_config:
                approval_config = self._apply_routing_overrides(
                    approval_config, routing_config
                )
            
            # Add escalation rules based on urgency
            if urgency == "high":
                approval_config.escalation_rules.append(
                    EscalationRule(
                        escalation_type=EscalationType.TIME_BASED,
                        trigger_after_hours=24,
                        escalate_to=self._get_escalation_approver(department),
                        escalation_message="High urgency approval requires attention"
                    )
                )
            elif urgency == "critical":
                approval_config.escalation_rules.append(
                    EscalationRule(
                        escalation_type=EscalationType.TIME_BASED,
                        trigger_after_hours=4,
                        escalate_to=self._get_executive_approver(),
                        escalation_message="Critical approval requires immediate attention"
                    )
                )
            
            logger.info(
                f"Routed approval with {len(approval_config.approvers)} approvers"
            )
            return approval_config
            
        except Exception as e:
            logger.error(f"Failed to route approval: {e}")
            raise WorkflowException(f"Failed to route approval: {e}")
    
    async def _route_expense_approval(
        self,
        amount: float,
        department: str,
        urgency: str,
        config: ApprovalTaskConfig
    ) -> ApprovalTaskConfig:
        """Route expense approval based on amount and department"""
        # Amount-based routing
        if amount < 1000:
            # Single approver - department manager
            config.approval_type = ApprovalType.SINGLE
            config.approvers = [
                self._get_department_approver(department, "manager")
            ]
        elif amount < 10000:
            # Sequential approval - manager then finance
            config.approval_type = ApprovalType.SEQUENTIAL
            config.approvers = [
                self._get_department_approver(department, "manager"),
                self.approver_pools["finance_approvers"][0]  # Finance analyst
            ]
        elif amount < 50000:
            # Sequential approval - manager, finance manager, department head
            config.approval_type = ApprovalType.SEQUENTIAL
            config.approvers = [
                self._get_department_approver(department, "manager"),
                self.approver_pools["finance_approvers"][1],  # Finance manager
                self._get_department_approver(department, "vp")
            ]
        else:
            # High-value approval - includes CFO
            config.approval_type = ApprovalType.SEQUENTIAL
            config.approvers = [
                self._get_department_approver(department, "manager"),
                self.approver_pools["finance_approvers"][1],  # Finance manager
                self._get_department_approver(department, "vp"),
                self.approver_pools["finance_approvers"][2]   # CFO
            ]
            
            # For very high amounts, add CEO
            if amount >= 100000:
                config.approvers.append(self._get_executive_approver())
        
        # Set deadline based on urgency
        if urgency == "critical":
            config.approval_deadline_hours = 4
        elif urgency == "high":
            config.approval_deadline_hours = 24
        else:
            config.approval_deadline_hours = 72
        
        return config
    
    async def _route_content_approval(
        self,
        content_type: str,
        context: Dict[str, Any],
        config: ApprovalTaskConfig
    ) -> ApprovalTaskConfig:
        """Route content approval based on type and sensitivity"""
        sensitivity = context.get("sensitivity", "normal")
        
        # Base content approvers
        config.approvers = [self.approver_pools["content_approvers"][0]]  # Review team
        
        if sensitivity == "high" or content_type in ["legal", "compliance"]:
            # Add legal review
            config.approval_type = ApprovalType.SEQUENTIAL
            config.approvers.append(self.approver_pools["legal_approvers"][0])
        
        if content_type == "marketing":
            # Parallel approval for marketing content
            config.approval_type = ApprovalType.PARALLEL
            config.approvers.extend([
                self._get_department_approver("marketing", "lead"),
                self.approver_pools["content_approvers"][1]  # Content manager
            ])
            config.voting_strategy = VotingStrategy.MAJORITY
        
        if context.get("external_publish", False):
            # External content needs additional approval
            config.approvers.append(
                self._get_department_approver("marketing", "manager")
            )
        
        return config
    
    async def _route_access_approval(
        self,
        context: Dict[str, Any],
        config: ApprovalTaskConfig
    ) -> ApprovalTaskConfig:
        """Route access request approval"""
        access_level = context.get("access_level", "read")
        resource_type = context.get("resource_type", "general")
        
        if access_level == "admin" or resource_type == "sensitive":
            # High-level access needs multiple approvals
            config.approval_type = ApprovalType.SEQUENTIAL
            config.approvers = [
                self._get_department_approver(
                    context.get("department", "it"), "manager"
                ),
                ApproverConfig(
                    approver_type=ApproverType.ROLE,
                    identifier="security_officer",
                    name="Security Officer",
                    email="security@example.com"
                )
            ]
            
            if resource_type == "financial":
                config.approvers.append(self.approver_pools["finance_approvers"][1])
        else:
            # Standard access - single approval
            config.approval_type = ApprovalType.SINGLE
            config.approvers = [
                self._get_department_approver(
                    context.get("department", "it"), "lead"
                )
            ]
        
        # Quick turnaround for access requests
        config.approval_deadline_hours = 24
        
        return config
    
    async def _route_project_approval(
        self,
        context: Dict[str, Any],
        config: ApprovalTaskConfig
    ) -> ApprovalTaskConfig:
        """Route project approval based on scope and budget"""
        budget = context.get("budget", 0)
        scope = context.get("scope", "small")
        departments = context.get("departments", [])
        
        if scope == "enterprise" or budget > 100000:
            # Large project - voting by department heads
            config.approval_type = ApprovalType.VOTING
            config.voting_strategy = VotingStrategy.MAJORITY
            config.approval_threshold = 0.66  # 2/3 majority
            
            # Add VPs from involved departments
            for dept in departments[:5]:  # Limit to 5 departments
                config.approvers.append(
                    self._get_department_approver(dept, "vp")
                )
            
            # Add CFO for budget approval
            if budget > 50000:
                config.approvers.append(self.approver_pools["finance_approvers"][2])
        elif scope == "department":
            # Department project - sequential approval
            config.approval_type = ApprovalType.SEQUENTIAL
            primary_dept = departments[0] if departments else "general"
            config.approvers = [
                self._get_department_approver(primary_dept, "manager"),
                self._get_department_approver(primary_dept, "vp")
            ]
            
            if budget > 10000:
                config.approvers.append(self.approver_pools["finance_approvers"][0])
        else:
            # Small project - single approval
            config.approval_type = ApprovalType.SINGLE
            primary_dept = departments[0] if departments else "general"
            config.approvers = [
                self._get_department_approver(primary_dept, "lead")
            ]
        
        return config
    
    async def _route_default_approval(
        self,
        context: Dict[str, Any],
        config: ApprovalTaskConfig
    ) -> ApprovalTaskConfig:
        """Default routing for general approvals"""
        department = context.get("department", "general")
        
        config.approval_type = ApprovalType.SINGLE
        config.approvers = [
            self._get_department_approver(department, "manager")
        ]
        
        return config
    
    def _get_department_approver(
        self,
        department: str,
        level: str
    ) -> ApproverConfig:
        """Get approver for department at specified level"""
        hierarchy = self.department_hierarchy.get(department, ["manager"])
        
        level_map = {
            "lead": 0,
            "manager": 1,
            "vp": 2,
            "c_level": 3
        }
        
        level_index = level_map.get(level, 1)
        if level_index >= len(hierarchy):
            level_index = len(hierarchy) - 1
        
        role = hierarchy[level_index]
        
        return ApproverConfig(
            approver_type=ApproverType.ROLE,
            identifier=role,
            name=role.replace("_", " ").title(),
            email=f"{role}@example.com"
        )
    
    def _get_escalation_approver(self, department: str) -> ApproverConfig:
        """Get escalation approver for department"""
        # Escalate to department VP or C-level
        hierarchy = self.department_hierarchy.get(department, ["manager"])
        escalation_role = hierarchy[-2] if len(hierarchy) > 1 else hierarchy[-1]
        
        return ApproverConfig(
            approver_type=ApproverType.ROLE,
            identifier=escalation_role,
            name=escalation_role.replace("_", " ").title(),
            email=f"{escalation_role}@example.com"
        )
    
    def _get_executive_approver(self) -> ApproverConfig:
        """Get executive approver"""
        return ApproverConfig(
            approver_type=ApproverType.ROLE,
            identifier="ceo",
            name="Chief Executive Officer",
            email="ceo@example.com"
        )
    
    def _apply_routing_overrides(
        self,
        config: ApprovalTaskConfig,
        overrides: Dict[str, Any]
    ) -> ApprovalTaskConfig:
        """Apply routing configuration overrides"""
        if "approval_type" in overrides:
            config.approval_type = ApprovalType(overrides["approval_type"])
        
        if "additional_approvers" in overrides:
            for approver_data in overrides["additional_approvers"]:
                config.approvers.append(
                    ApproverConfig(**approver_data)
                )
        
        if "remove_approvers" in overrides:
            # Remove approvers by identifier
            remove_ids = set(overrides["remove_approvers"])
            config.approvers = [
                a for a in config.approvers 
                if a.identifier not in remove_ids
            ]
        
        if "voting_strategy" in overrides:
            config.voting_strategy = VotingStrategy(overrides["voting_strategy"])
        
        if "deadline_hours" in overrides:
            config.approval_deadline_hours = overrides["deadline_hours"]
        
        return config
    
    async def get_routing_rules(self, rule_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get configured routing rules"""
        rules = []
        
        # Convert routing logic to rules format for display
        rules.extend([
            {
                "id": "expense_low",
                "type": "expense",
                "name": "Low Value Expense",
                "condition": "amount < 1000",
                "routing": "Single approval by department manager",
                "deadline": "72 hours"
            },
            {
                "id": "expense_medium",
                "type": "expense",
                "name": "Medium Value Expense",
                "condition": "1000 <= amount < 10000",
                "routing": "Sequential: Manager → Finance Analyst",
                "deadline": "72 hours"
            },
            {
                "id": "expense_high",
                "type": "expense",
                "name": "High Value Expense",
                "condition": "10000 <= amount < 50000",
                "routing": "Sequential: Manager → Finance Manager → Department VP",
                "deadline": "72 hours"
            },
            {
                "id": "expense_very_high",
                "type": "expense",
                "name": "Very High Value Expense",
                "condition": "amount >= 50000",
                "routing": "Sequential: Manager → Finance Manager → Department VP → CFO",
                "deadline": "72 hours"
            },
            {
                "id": "content_standard",
                "type": "content",
                "name": "Standard Content",
                "condition": "sensitivity = normal",
                "routing": "Content Review Team",
                "deadline": "48 hours"
            },
            {
                "id": "content_sensitive",
                "type": "content",
                "name": "Sensitive Content",
                "condition": "sensitivity = high OR type IN (legal, compliance)",
                "routing": "Sequential: Content Review → Legal Counsel",
                "deadline": "48 hours"
            },
            {
                "id": "access_standard",
                "type": "access",
                "name": "Standard Access",
                "condition": "access_level = read",
                "routing": "Department Lead",
                "deadline": "24 hours"
            },
            {
                "id": "access_admin",
                "type": "access",
                "name": "Admin Access",
                "condition": "access_level = admin OR resource_type = sensitive",
                "routing": "Sequential: Department Manager → Security Officer",
                "deadline": "24 hours"
            }
        ])
        
        if rule_type:
            rules = [r for r in rules if r["type"] == rule_type]
        
        return rules
    
    async def test_routing(
        self,
        test_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Test routing with given context"""
        try:
            config = await self.route_approval(test_context)
            
            return {
                "success": True,
                "approval_type": config.approval_type,
                "approver_count": len(config.approvers),
                "approvers": [
                    {
                        "type": a.approver_type,
                        "identifier": a.identifier,
                        "name": a.name
                    }
                    for a in config.approvers
                ],
                "deadline_hours": config.approval_deadline_hours,
                "escalation_rules": len(config.escalation_rules),
                "voting_strategy": config.voting_strategy
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def suggest_approvers(
        self,
        context: Dict[str, Any],
        max_suggestions: int = 5
    ) -> List[ApproverConfig]:
        """Suggest potential approvers based on context"""
        suggestions = []
        
        department = context.get("department")
        approval_type = context.get("approval_type")
        
        # Add department hierarchy suggestions
        if department and department in self.department_hierarchy:
            for role in self.department_hierarchy[department][:max_suggestions]:
                suggestions.append(
                    ApproverConfig(
                        approver_type=ApproverType.ROLE,
                        identifier=role,
                        name=role.replace("_", " ").title(),
                        email=f"{role}@example.com"
                    )
                )
        
        # Add relevant pool suggestions
        if approval_type == "expense":
            suggestions.extend(self.approver_pools.get("finance_approvers", []))
        elif approval_type == "content":
            suggestions.extend(self.approver_pools.get("content_approvers", []))
        
        # Limit to max suggestions
        return suggestions[:max_suggestions]


class RoutingRule:
    """Represents a routing rule"""
    
    def __init__(
        self,
        rule_id: str,
        name: str,
        conditions: Dict[str, Any],
        actions: Dict[str, Any],
        priority: int = 0
    ):
        self.rule_id = rule_id
        self.name = name
        self.conditions = conditions
        self.actions = actions
        self.priority = priority
    
    def matches(self, context: Dict[str, Any]) -> bool:
        """Check if rule matches the context"""
        for key, value in self.conditions.items():
            if key not in context:
                return False
            
            context_value = context[key]
            
            # Handle different condition types
            if isinstance(value, dict):
                # Complex condition
                operator = value.get("operator", "equals")
                compare_value = value.get("value")
                
                if operator == "equals" and context_value != compare_value:
                    return False
                elif operator == "greater_than" and context_value <= compare_value:
                    return False
                elif operator == "less_than" and context_value >= compare_value:
                    return False
                elif operator == "in" and context_value not in compare_value:
                    return False
                elif operator == "contains" and compare_value not in context_value:
                    return False
            else:
                # Simple equality
                if context_value != value:
                    return False
        
        return True
    
    def apply(self, config: ApprovalTaskConfig) -> ApprovalTaskConfig:
        """Apply rule actions to approval config"""
        for action, value in self.actions.items():
            if action == "add_approver":
                config.approvers.append(ApproverConfig(**value))
            elif action == "set_approval_type":
                config.approval_type = ApprovalType(value)
            elif action == "set_deadline":
                config.approval_deadline_hours = value
            elif action == "add_escalation":
                config.escalation_rules.append(EscalationRule(**value))
        
        return config