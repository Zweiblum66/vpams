"""
API routes for approval routing functionality
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from ..core.auth import get_current_user
from ..services.approval_routing_service import ApprovalRoutingService
from ..models.approval_schemas import ApprovalTaskConfig, ApproverConfig

router = APIRouter(prefix="/api/v1/approval-routing", tags=["approval-routing"])
routing_service = ApprovalRoutingService()


class RoutingContext(BaseModel):
    """Context for routing decision"""
    approval_type: str = Field(default="general", description="Type of approval")
    amount: Optional[float] = Field(None, description="Amount for expense approvals")
    department: Optional[str] = Field(None, description="Department of requestor")
    urgency: str = Field(default="normal", description="Urgency level: low, normal, high, critical")
    content_type: Optional[str] = Field(None, description="Type of content for content approvals")
    sensitivity: Optional[str] = Field(None, description="Sensitivity level")
    access_level: Optional[str] = Field(None, description="Access level for access requests")
    resource_type: Optional[str] = Field(None, description="Type of resource")
    budget: Optional[float] = Field(None, description="Project budget")
    scope: Optional[str] = Field(None, description="Project scope")
    departments: Optional[List[str]] = Field(default_factory=list, description="Involved departments")
    external_publish: Optional[bool] = Field(False, description="Whether content will be published externally")
    title: str = Field(..., description="Approval title")
    description: str = Field(..., description="Approval description")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class RoutingOverride(BaseModel):
    """Manual routing overrides"""
    approval_type: Optional[str] = None
    additional_approvers: Optional[List[Dict[str, Any]]] = None
    remove_approvers: Optional[List[str]] = None
    voting_strategy: Optional[str] = None
    deadline_hours: Optional[int] = None


class RouteApprovalRequest(BaseModel):
    """Request to route an approval"""
    context: RoutingContext
    override: Optional[RoutingOverride] = None


class RoutingTestRequest(BaseModel):
    """Request to test routing logic"""
    context: RoutingContext


class RoutingRuleResponse(BaseModel):
    """Routing rule response"""
    id: str
    type: str
    name: str
    condition: str
    routing: str
    deadline: str


class RoutingTestResponse(BaseModel):
    """Routing test response"""
    success: bool
    approval_type: Optional[str] = None
    approver_count: Optional[int] = None
    approvers: Optional[List[Dict[str, Any]]] = None
    deadline_hours: Optional[int] = None
    escalation_rules: Optional[int] = None
    voting_strategy: Optional[str] = None
    error: Optional[str] = None


class ApproverSuggestion(BaseModel):
    """Approver suggestion"""
    approver_type: str
    identifier: str
    name: str
    email: Optional[str] = None
    reason: Optional[str] = None


@router.post("/route", response_model=ApprovalTaskConfig)
async def route_approval(
    request: RouteApprovalRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Route an approval based on context and rules
    
    This endpoint determines the appropriate approvers and approval configuration
    based on the provided context (type, amount, department, etc.).
    """
    try:
        # Convert context to dict
        context_dict = request.context.dict()
        context_dict["requestor_id"] = current_user["user_id"]
        
        # Apply routing
        approval_config = await routing_service.route_approval(
            context=context_dict,
            routing_config=request.override.dict() if request.override else None
        )
        
        return approval_config
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/rules", response_model=List[RoutingRuleResponse])
async def get_routing_rules(
    rule_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Get configured routing rules
    
    Returns the list of routing rules, optionally filtered by type.
    """
    try:
        rules = await routing_service.get_routing_rules(rule_type)
        return rules
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/test", response_model=RoutingTestResponse)
async def test_routing(
    request: RoutingTestRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Test routing logic with given context
    
    This endpoint allows testing the routing logic without creating an actual approval.
    """
    try:
        context_dict = request.context.dict()
        result = await routing_service.test_routing(context_dict)
        return RoutingTestResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/suggest-approvers", response_model=List[ApproverSuggestion])
async def suggest_approvers(
    context: RoutingContext,
    max_suggestions: int = 5,
    current_user: dict = Depends(get_current_user)
):
    """
    Suggest potential approvers based on context
    
    Returns a list of suggested approvers that could be used for the given approval context.
    """
    try:
        context_dict = context.dict()
        suggestions = await routing_service.suggest_approvers(
            context_dict, 
            max_suggestions
        )
        
        return [
            ApproverSuggestion(
                approver_type=s.approver_type,
                identifier=s.identifier,
                name=s.name,
                email=s.email,
                reason=f"Suggested based on {context.approval_type} approval type"
            )
            for s in suggestions
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/departments", response_model=Dict[str, List[str]])
async def get_department_hierarchies(
    current_user: dict = Depends(get_current_user)
):
    """Get department hierarchies for routing"""
    return routing_service.department_hierarchy


@router.get("/approver-pools", response_model=Dict[str, List[Dict[str, Any]]])
async def get_approver_pools(
    current_user: dict = Depends(get_current_user)
):
    """Get configured approver pools"""
    pools = {}
    for pool_name, approvers in routing_service.approver_pools.items():
        pools[pool_name] = [
            {
                "approver_type": a.approver_type,
                "identifier": a.identifier,
                "name": a.name,
                "email": a.email
            }
            for a in approvers
        ]
    return pools


# Example routing configurations for common scenarios

@router.get("/examples", response_model=List[Dict[str, Any]])
async def get_routing_examples(
    current_user: dict = Depends(get_current_user)
):
    """Get example routing configurations"""
    return [
        {
            "name": "Small Expense Approval",
            "description": "Expense under $1,000",
            "context": {
                "approval_type": "expense",
                "amount": 500,
                "department": "engineering",
                "urgency": "normal",
                "title": "Team lunch expense",
                "description": "Monthly team lunch"
            },
            "expected_routing": "Single approval by Engineering Manager"
        },
        {
            "name": "Large Expense Approval",
            "description": "Expense over $50,000",
            "context": {
                "approval_type": "expense",
                "amount": 75000,
                "department": "engineering",
                "urgency": "normal",
                "title": "New server infrastructure",
                "description": "Purchase of new servers for production"
            },
            "expected_routing": "Sequential: Manager → Finance Manager → VP Engineering → CFO"
        },
        {
            "name": "Sensitive Content Approval",
            "description": "Legal or compliance content",
            "context": {
                "approval_type": "content",
                "content_type": "legal",
                "sensitivity": "high",
                "external_publish": True,
                "title": "Terms of Service Update",
                "description": "Updated terms of service for public website"
            },
            "expected_routing": "Sequential: Content Review → Legal Counsel → Marketing Manager"
        },
        {
            "name": "Admin Access Request",
            "description": "Request for admin access to sensitive systems",
            "context": {
                "approval_type": "access",
                "access_level": "admin",
                "resource_type": "sensitive",
                "department": "engineering",
                "title": "Production database admin access",
                "description": "Need admin access for database maintenance"
            },
            "expected_routing": "Sequential: IT Manager → Security Officer"
        },
        {
            "name": "Enterprise Project Approval",
            "description": "Large cross-department project",
            "context": {
                "approval_type": "project",
                "scope": "enterprise",
                "budget": 250000,
                "departments": ["engineering", "marketing", "operations"],
                "title": "Digital Transformation Initiative",
                "description": "Company-wide digital transformation project"
            },
            "expected_routing": "Voting: VP Engineering, VP Marketing, VP Operations, CFO (2/3 majority required)"
        }
    ]


@router.post("/validate-routing", response_model=Dict[str, Any])
async def validate_routing_config(
    config: ApprovalTaskConfig,
    current_user: dict = Depends(get_current_user)
):
    """
    Validate a routing configuration
    
    Checks if the provided approval configuration is valid and complete.
    """
    errors = []
    warnings = []
    
    # Validate approvers
    if not config.approvers:
        errors.append("At least one approver is required")
    
    # Check for duplicate approvers
    approver_ids = [a.identifier for a in config.approvers]
    if len(approver_ids) != len(set(approver_ids)):
        warnings.append("Duplicate approvers detected")
    
    # Validate approval type specific rules
    if config.approval_type == ApprovalType.VOTING:
        if not config.voting_strategy:
            errors.append("Voting strategy is required for voting approvals")
        if config.voting_strategy == VotingStrategy.CUSTOM_THRESHOLD and not config.approval_threshold:
            errors.append("Approval threshold is required for custom threshold voting")
    
    # Validate escalation rules
    for i, rule in enumerate(config.escalation_rules):
        if rule.escalation_type == EscalationType.TIME_BASED and not rule.trigger_after_hours:
            errors.append(f"Escalation rule {i+1}: trigger_after_hours is required for time-based escalation")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "approver_count": len(config.approvers),
        "has_escalation": len(config.escalation_rules) > 0,
        "estimated_completion_time": config.approval_deadline_hours or "No deadline set"
    }