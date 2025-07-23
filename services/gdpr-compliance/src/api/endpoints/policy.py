"""API endpoints for policy engine management"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime

from ...core.deps import get_current_user, get_db
from ...core.exceptions import NotFoundError, ValidationError, PolicyViolationError
from ...db.models import User
from ...models.schemas import (
    PolicyDefinitionCreate, PolicyDefinitionUpdate, PolicyDefinitionResponse,
    PolicyRuleCreate, PolicyRuleUpdate, PolicyRuleResponse,
    PolicyEvaluationCreate, PolicyEvaluationResult,
    PolicyViolationResponse, PolicyViolationUpdate,
    PolicyAssignmentCreate, PolicyAssignmentResponse,
    PolicyTemplateCreate, PolicyTemplateResponse,
    PolicyScheduleCreate, PolicyScheduleResponse,
    PolicyMetrics, PolicySeverity
)
from ...services.policy_engine_service import PolicyEngineService

logger = logging.getLogger(__name__)
router = APIRouter()


# Policy Definition Management

@router.post("/policies", response_model=PolicyDefinitionResponse)
async def create_policy(
    policy_data: PolicyDefinitionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new policy definition.
    
    Requires: policy:create permission
    """
    try:
        # Check permissions
        if not current_user.has_permission("policy:create"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to create policies"
            )
        
        service = PolicyEngineService(db)
        policy = await service.create_policy(policy_data, str(current_user.id))
        
        logger.info(
            f"Policy created by user {current_user.id}",
            extra={
                "user_id": str(current_user.id),
                "policy_id": str(policy.id),
                "policy_name": policy.name
            }
        )
        
        return policy
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating policy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create policy"
        )


@router.get("/policies", response_model=List[PolicyDefinitionResponse])
async def list_policies(
    category: Optional[str] = Query(None, description="Filter by category"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    severity: Optional[PolicySeverity] = Query(None, description="Filter by severity"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List policy definitions with optional filtering.
    
    Requires: policy:view permission
    """
    try:
        if not current_user.has_permission("policy:view"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = PolicyEngineService(db)
        policies = await service.list_policies(
            category=category,
            is_active=is_active,
            severity=severity,
            limit=limit,
            offset=offset
        )
        
        return policies
        
    except Exception as e:
        logger.error(f"Error listing policies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list policies"
        )


@router.get("/policies/{policy_id}", response_model=PolicyDefinitionResponse)
async def get_policy(
    policy_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific policy definition.
    
    Requires: policy:view permission
    """
    try:
        if not current_user.has_permission("policy:view"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = PolicyEngineService(db)
        policy = await service.get_policy(str(policy_id))
        
        return policy
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting policy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get policy"
        )


@router.patch("/policies/{policy_id}", response_model=PolicyDefinitionResponse)
async def update_policy(
    policy_id: UUID,
    update_data: PolicyDefinitionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a policy definition.
    
    Requires: policy:update permission
    """
    try:
        if not current_user.has_permission("policy:update"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = PolicyEngineService(db)
        policy = await service.update_policy(str(policy_id), update_data)
        
        logger.info(
            f"Policy updated by user {current_user.id}",
            extra={
                "user_id": str(current_user.id),
                "policy_id": str(policy_id)
            }
        )
        
        return policy
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating policy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update policy"
        )


@router.delete("/policies/{policy_id}")
async def delete_policy(
    policy_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete (deactivate) a policy definition.
    
    Requires: policy:delete permission
    """
    try:
        if not current_user.has_permission("policy:delete"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = PolicyEngineService(db)
        await service.delete_policy(str(policy_id))
        
        logger.info(
            f"Policy deleted by user {current_user.id}",
            extra={
                "user_id": str(current_user.id),
                "policy_id": str(policy_id)
            }
        )
        
        return {"message": "Policy deactivated successfully"}
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting policy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete policy"
        )


# Policy Rule Management

@router.post("/policies/{policy_id}/rules", response_model=PolicyRuleResponse)
async def add_rule_to_policy(
    policy_id: UUID,
    rule_data: PolicyRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a rule to an existing policy.
    
    Requires: policy:update permission
    """
    try:
        if not current_user.has_permission("policy:update"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = PolicyEngineService(db)
        rule = await service.add_rule_to_policy(
            str(policy_id),
            rule_data,
            str(current_user.id)
        )
        
        return rule
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error adding rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add rule"
        )


@router.patch("/rules/{rule_id}", response_model=PolicyRuleResponse)
async def update_rule(
    rule_id: UUID,
    update_data: PolicyRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a policy rule.
    
    Requires: policy:update permission
    """
    try:
        if not current_user.has_permission("policy:update"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = PolicyEngineService(db)
        rule = await service.update_rule(str(rule_id), update_data)
        
        return rule
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update rule"
        )


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a policy rule.
    
    Requires: policy:update permission
    """
    try:
        if not current_user.has_permission("policy:update"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = PolicyEngineService(db)
        await service.delete_rule(str(rule_id))
        
        return {"message": "Rule deleted successfully"}
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete rule"
        )


# Policy Evaluation

@router.post("/policies/{policy_id}/evaluate", response_model=PolicyEvaluationResult)
async def evaluate_policy(
    policy_id: UUID,
    context: Dict[str, Any] = Body(..., description="Context data for evaluation"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Evaluate a policy against given context.
    
    Requires: policy:evaluate permission
    """
    try:
        if not current_user.has_permission("policy:evaluate"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = PolicyEngineService(db)
        result = await service.evaluate_policy(
            str(policy_id),
            context,
            str(current_user.id)
        )
        
        return result
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PolicyViolationError as e:
        # Return policy violation as a successful evaluation with fail result
        return PolicyEvaluationResult(
            policy_id=policy_id,
            result="fail",
            passed_rules=[],
            failed_rules=[],
            violations=[],
            metadata={"error": str(e)}
        )
    except Exception as e:
        logger.error(f"Error evaluating policy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to evaluate policy"
        )


@router.post("/evaluate", response_model=List[PolicyEvaluationResult])
async def evaluate_policies_for_entity(
    entity_type: str = Body(..., description="Type of entity"),
    entity_id: str = Body(..., description="Entity ID"),
    context: Dict[str, Any] = Body(..., description="Context data"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Evaluate all applicable policies for an entity.
    
    Requires: policy:evaluate permission
    """
    try:
        if not current_user.has_permission("policy:evaluate"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = PolicyEngineService(db)
        results = await service.evaluate_policies_for_entity(
            entity_type,
            entity_id,
            context,
            str(current_user.id)
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Error evaluating policies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to evaluate policies"
        )


# Policy Assignments

@router.post("/assignments", response_model=PolicyAssignmentResponse)
async def assign_policy(
    assignment_data: PolicyAssignmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Assign a policy to an entity.
    
    Requires: policy:assign permission
    """
    try:
        if not current_user.has_permission("policy:assign"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = PolicyEngineService(db)
        assignment = await service.assign_policy(
            assignment_data,
            str(current_user.id)
        )
        
        return assignment
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error assigning policy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign policy"
        )


@router.delete("/assignments/{policy_id}/{entity_type}/{entity_id}")
async def unassign_policy(
    policy_id: UUID,
    entity_type: str,
    entity_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove a policy assignment.
    
    Requires: policy:assign permission
    """
    try:
        if not current_user.has_permission("policy:assign"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = PolicyEngineService(db)
        await service.unassign_policy(str(policy_id), entity_type, entity_id)
        
        return {"message": "Policy unassigned successfully"}
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error unassigning policy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unassign policy"
        )


# Policy Templates

@router.get("/templates", response_model=List[PolicyTemplateResponse])
async def list_templates(
    category: Optional[str] = Query(None, description="Filter by category"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List available policy templates.
    
    Requires: policy:view permission
    """
    try:
        if not current_user.has_permission("policy:view"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = PolicyEngineService(db)
        templates = await service.list_templates(category)
        
        return templates
        
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list templates"
        )


@router.post("/templates", response_model=PolicyTemplateResponse)
async def create_template(
    template_data: PolicyTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new policy template.
    
    Requires: policy:admin permission
    """
    try:
        if not current_user.has_permission("policy:admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permissions required"
            )
        
        service = PolicyEngineService(db)
        template = await service.create_policy_template(
            template_data.name,
            template_data.description,
            template_data.template_data,
            str(current_user.id)
        )
        
        return template
        
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create template"
        )


@router.post("/templates/{template_id}/instantiate", response_model=PolicyDefinitionResponse)
async def create_policy_from_template(
    template_id: UUID,
    policy_name: str = Body(..., description="Name for the new policy"),
    parameters: Dict[str, Any] = Body({}, description="Template parameters"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a policy from a template.
    
    Requires: policy:create permission
    """
    try:
        if not current_user.has_permission("policy:create"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = PolicyEngineService(db)
        policy = await service.create_policy_from_template(
            str(template_id),
            policy_name,
            parameters,
            str(current_user.id)
        )
        
        return policy
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating policy from template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create policy from template"
        )


# Policy Violations

@router.get("/violations", response_model=List[PolicyViolationResponse])
async def list_violations(
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    severity: Optional[PolicySeverity] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List policy violations with filtering.
    
    Requires: policy:view permission
    """
    try:
        if not current_user.has_permission("policy:view"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = PolicyEngineService(db)
        violations = await service.list_violations(
            entity_type=entity_type,
            entity_id=entity_id,
            status=status,
            severity=severity,
            limit=limit,
            offset=offset
        )
        
        return violations
        
    except Exception as e:
        logger.error(f"Error listing violations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list violations"
        )


@router.patch("/violations/{violation_id}", response_model=PolicyViolationResponse)
async def update_violation(
    violation_id: UUID,
    update_data: PolicyViolationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update violation status.
    
    Requires: policy:manage permission
    """
    try:
        if not current_user.has_permission("policy:manage"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = PolicyEngineService(db)
        violation = await service.update_violation_status(
            str(violation_id),
            update_data.status,
            update_data.resolution_notes,
            str(current_user.id)
        )
        
        return violation
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating violation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update violation"
        )


# Policy Metrics

@router.get("/metrics", response_model=PolicyMetrics)
async def get_policy_metrics(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get policy engine metrics.
    
    Requires: policy:view permission
    """
    try:
        if not current_user.has_permission("policy:view"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = PolicyEngineService(db)
        metrics = await service.get_policy_metrics(start_date, end_date)
        
        return PolicyMetrics(**metrics)
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get metrics"
        )


# Policy Schedules

@router.post("/schedules", response_model=PolicyScheduleResponse)
async def create_policy_schedule(
    schedule_data: PolicyScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a scheduled policy evaluation.
    
    Requires: policy:schedule permission
    """
    try:
        if not current_user.has_permission("policy:schedule"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = PolicyEngineService(db)
        schedule = await service.create_policy_schedule(
            schedule_data,
            str(current_user.id)
        )
        
        return schedule
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating schedule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create schedule"
        )


# Initialize default templates

@router.post("/templates/defaults")
async def create_default_templates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create default policy templates.
    
    Requires: policy:admin permission
    """
    try:
        if not current_user.has_permission("policy:admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permissions required"
            )
        
        service = PolicyEngineService(db)
        templates = await service.create_default_templates(str(current_user.id))
        
        return {
            "message": f"Created {len(templates)} default templates",
            "templates": [t.name for t in templates]
        }
        
    except Exception as e:
        logger.error(f"Error creating default templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create default templates"
        )