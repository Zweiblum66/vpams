"""Compliance Automation API endpoints"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from pydantic import BaseModel, Field

from ...db.base import get_db
from ...core.exceptions import NotFoundError, ValidationError
from ...api.dependencies import get_current_user
from ...models.schemas import User
from ...services.compliance_automation_service import (
    ComplianceAutomationService, AutomationTriggerType, 
    ComplianceCheckType, AutomationActionType
)

router = APIRouter(prefix="/api/v1/compliance-automation", tags=["compliance-automation"])


# Pydantic Models for API

class AutomationRuleCreate(BaseModel):
    """Create automation rule schema"""
    rule_name: str = Field(..., min_length=1, max_length=255)
    trigger_type: AutomationTriggerType
    check_type: ComplianceCheckType
    actions: List[Dict[str, Any]] = Field(..., min_items=1)
    conditions: Dict[str, Any] = Field(default_factory=dict)
    schedule: Optional[str] = Field(None, description="Cron expression for scheduled rules")
    enabled: bool = Field(True)


class AutomationRuleResponse(BaseModel):
    """Automation rule response schema"""
    id: str
    name: str
    trigger_type: AutomationTriggerType
    check_type: ComplianceCheckType
    actions: List[Dict[str, Any]]
    conditions: Dict[str, Any]
    schedule: Optional[str]
    enabled: bool
    created_at: datetime
    last_executed: Optional[datetime]
    execution_count: int


class ComplianceStatusResponse(BaseModel):
    """Compliance status response schema"""
    overall_status: str
    risk_level: str
    active_violations: int
    checks_performed: int
    last_check: str
    violation_summary: Dict[str, Any]
    trends: Dict[str, Any]


class AutomationMetricsResponse(BaseModel):
    """Automation metrics response schema"""
    total_rules: int
    enabled_rules: int
    disabled_rules: int
    rules_by_type: Dict[str, int]
    execution_stats: Dict[str, Any]
    performance_metrics: Dict[str, Any]


class ExecutionResultResponse(BaseModel):
    """Execution result response schema"""
    executed_rules: int
    triggered_actions: int
    compliance_issues: List[Dict[str, Any]]
    automated_resolutions: List[Dict[str, Any]]
    execution_summary: Dict[str, Any]


# Automation Rule Management Endpoints

@router.post("/rules", response_model=Dict[str, str], status_code=status.HTTP_201_CREATED)
async def create_automation_rule(
    rule_data: AutomationRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new automation rule"""
    try:
        service = ComplianceAutomationService(db)
        rule_id = await service.register_automation_rule(
            rule_name=rule_data.rule_name,
            trigger_type=rule_data.trigger_type,
            check_type=rule_data.check_type,
            actions=rule_data.actions,
            conditions=rule_data.conditions,
            schedule=rule_data.schedule,
            enabled=rule_data.enabled
        )
        return {"rule_id": rule_id, "message": "Automation rule created successfully"}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create automation rule")


@router.get("/rules", response_model=List[AutomationRuleResponse])
async def list_automation_rules(
    enabled_only: bool = Query(False, description="Show only enabled rules"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all automation rules"""
    try:
        service = ComplianceAutomationService(db)
        rules = await service.get_automation_rules()
        
        if enabled_only:
            rules = [rule for rule in rules if rule["enabled"]]
        
        return [
            AutomationRuleResponse(
                id=rule["id"],
                name=rule["name"],
                trigger_type=rule["trigger_type"],
                check_type=rule["check_type"],
                actions=rule["actions"],
                conditions=rule["conditions"],
                schedule=rule["schedule"],
                enabled=rule["enabled"],
                created_at=rule["created_at"],
                last_executed=rule["last_executed"],
                execution_count=rule["execution_count"]
            )
            for rule in rules
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve automation rules")


@router.patch("/rules/{rule_id}/enable", response_model=Dict[str, str])
async def enable_automation_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Enable an automation rule"""
    try:
        service = ComplianceAutomationService(db)
        success = await service.enable_rule(rule_id)
        if not success:
            raise HTTPException(status_code=404, detail="Automation rule not found")
        return {"message": "Automation rule enabled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to enable automation rule")


@router.patch("/rules/{rule_id}/disable", response_model=Dict[str, str])
async def disable_automation_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Disable an automation rule"""
    try:
        service = ComplianceAutomationService(db)
        success = await service.disable_rule(rule_id)
        if not success:
            raise HTTPException(status_code=404, detail="Automation rule not found")
        return {"message": "Automation rule disabled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to disable automation rule")


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_automation_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an automation rule"""
    try:
        service = ComplianceAutomationService(db)
        success = await service.delete_rule(rule_id)
        if not success:
            raise HTTPException(status_code=404, detail="Automation rule not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to delete automation rule")


# Execution and Monitoring Endpoints

@router.post("/execute", response_model=ExecutionResultResponse)
async def execute_automation_checks(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Execute all automation checks immediately"""
    try:
        service = ComplianceAutomationService(db)
        
        # Execute in background for better performance
        def run_automation():
            import asyncio
            return asyncio.run(service.execute_automation_checks())
        
        background_tasks.add_task(run_automation)
        
        # For immediate response, run a quick check
        result = await service.execute_automation_checks()
        return ExecutionResultResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to execute automation checks")


@router.get("/status", response_model=ComplianceStatusResponse)
async def get_compliance_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current compliance status"""
    try:
        service = ComplianceAutomationService(db)
        status = await service.get_compliance_status()
        return ComplianceStatusResponse(**status)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve compliance status")


@router.get("/metrics", response_model=AutomationMetricsResponse)
async def get_automation_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get automation execution metrics"""
    try:
        service = ComplianceAutomationService(db)
        metrics = await service.get_automation_metrics()
        return AutomationMetricsResponse(**metrics)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve automation metrics")


# Setup and Configuration Endpoints

@router.post("/setup/default-rules", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def setup_default_rules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Setup default automation rules for GDPR compliance"""
    try:
        service = ComplianceAutomationService(db)
        rule_ids = await service.setup_default_automation_rules()
        return {
            "message": "Default automation rules created successfully",
            "rule_ids": rule_ids,
            "total_rules": len(rule_ids)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to setup default rules")


# Configuration Reference Endpoints

@router.get("/config/trigger-types", response_model=List[str])
async def get_trigger_types():
    """Get available automation trigger types"""
    return [trigger.value for trigger in AutomationTriggerType]


@router.get("/config/check-types", response_model=List[str])
async def get_check_types():
    """Get available compliance check types"""
    return [check.value for check in ComplianceCheckType]


@router.get("/config/action-types", response_model=List[str])
async def get_action_types():
    """Get available automation action types"""
    return [action.value for action in AutomationActionType]


@router.get("/config/templates", response_model=Dict[str, Any])
async def get_rule_templates():
    """Get predefined rule templates"""
    templates = {
        "gdpr_data_request_monitor": {
            "rule_name": "GDPR Data Request Monitor",
            "trigger_type": "scheduled",
            "check_type": "data_request_overdue",
            "actions": [
                {
                    "type": "send_notification",
                    "recipient": "privacy@company.com",
                    "subject": "GDPR Data Request Overdue"
                }
            ],
            "conditions": {"grace_period_hours": 60},
            "schedule": "0 */4 * * *"
        },
        "consent_expiry_warning": {
            "rule_name": "Consent Expiry Warning",
            "trigger_type": "scheduled",
            "check_type": "consent_expiry",
            "actions": [
                {
                    "type": "send_notification",
                    "recipient": "marketing@company.com",
                    "subject": "Consent Expiring Soon"
                }
            ],
            "conditions": {"warning_days": 30},
            "schedule": "0 9 * * *"
        },
        "high_risk_alert": {
            "rule_name": "High Risk Assessment Alert",
            "trigger_type": "threshold_based",
            "check_type": "risk_threshold_exceeded",
            "actions": [
                {
                    "type": "escalate_issue",
                    "escalate_to": "ciso@company.com",
                    "level": "executive"
                }
            ],
            "conditions": {"risk_score_threshold": 8.0},
            "schedule": "0 */2 * * *"
        },
        "access_review_overdue": {
            "rule_name": "Access Review Overdue Alert",
            "trigger_type": "deadline_based",
            "check_type": "access_review_overdue",
            "actions": [
                {
                    "type": "send_notification",
                    "recipient": "security@company.com",
                    "subject": "Access Review Overdue"
                }
            ],
            "conditions": {},
            "schedule": "0 10 * * 1"
        }
    }
    
    return {
        "templates": templates,
        "usage_notes": {
            "schedule_format": "Cron expression (minute hour day month weekday)",
            "condition_examples": {
                "grace_period_hours": "Hours before considering request overdue",
                "warning_days": "Days before expiry to send warning",
                "risk_score_threshold": "Risk score above which to trigger (0-10)"
            },
            "action_parameters": {
                "send_notification": ["recipient", "subject", "message"],
                "create_task": ["assignee", "title", "due_hours"],
                "escalate_issue": ["escalate_to", "level", "reason"]
            }
        }
    }


# Testing and Validation Endpoints

@router.post("/test/check/{check_type}", response_model=Dict[str, Any])
async def test_compliance_check(
    check_type: ComplianceCheckType,
    conditions: Dict[str, Any] = {},
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Test a specific compliance check"""
    try:
        service = ComplianceAutomationService(db)
        result = await service._perform_compliance_check(check_type, conditions)
        return {
            "check_type": check_type,
            "test_result": result,
            "test_timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to test compliance check: {str(e)}")


@router.post("/validate/rule", response_model=Dict[str, Any])
async def validate_automation_rule(
    rule_data: AutomationRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Validate an automation rule configuration"""
    try:
        validation_result = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "suggestions": []
        }
        
        # Validate schedule format if provided
        if rule_data.schedule:
            # Basic cron validation (simplified)
            parts = rule_data.schedule.split()
            if len(parts) != 5:
                validation_result["errors"].append("Schedule must be a valid cron expression with 5 parts")
                validation_result["valid"] = False
        
        # Validate actions
        for action in rule_data.actions:
            if "type" not in action:
                validation_result["errors"].append("Action must have a 'type' field")
                validation_result["valid"] = False
            elif action["type"] not in [a.value for a in AutomationActionType]:
                validation_result["errors"].append(f"Invalid action type: {action['type']}")
                validation_result["valid"] = False
        
        # Validate conditions based on check type
        if rule_data.check_type == ComplianceCheckType.DATA_REQUEST_OVERDUE:
            if "grace_period_hours" not in rule_data.conditions:
                validation_result["warnings"].append("Consider setting grace_period_hours for data request checks")
        
        # Add suggestions
        if rule_data.trigger_type == AutomationTriggerType.SCHEDULED and not rule_data.schedule:
            validation_result["suggestions"].append("Scheduled rules should have a schedule defined")
        
        return validation_result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to validate rule: {str(e)}")


# Health Check Endpoint

@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db)
):
    """Health check for compliance automation service"""
    try:
        # Test database connection
        await db.execute("SELECT 1")
        
        # Check automation service
        service = ComplianceAutomationService(db)
        metrics = await service.get_automation_metrics()
        
        return {
            "status": "healthy",
            "service": "compliance-automation",
            "automation_rules": metrics["total_rules"],
            "enabled_rules": metrics["enabled_rules"],
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )