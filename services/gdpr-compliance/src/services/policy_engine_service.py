"""Policy Engine Service for governance and compliance rules"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, case
from sqlalchemy.orm import selectinload
import json
import re
from enum import Enum

from ..db.models import (
    PolicyDefinition, PolicyRule, PolicyEvaluation, PolicyViolation,
    PolicyAssignment, PolicyTemplate, PolicySchedule
)
from ..models.schemas import (
    PolicyDefinitionCreate, PolicyDefinitionUpdate, PolicyDefinitionResponse,
    PolicyRuleCreate, PolicyRuleUpdate, PolicyRuleResponse,
    PolicyEvaluationCreate, PolicyEvaluationResult,
    PolicyViolationResponse, PolicyAssignmentCreate, PolicyAssignmentResponse,
    PolicyTemplateResponse, PolicyScheduleCreate, PolicyScheduleResponse,
    PolicyCondition, PolicyAction, PolicySeverity, PolicyStatus,
    EvaluationResult, RuleOperator, RuleDataType
)
from ..core.exceptions import NotFoundError, ValidationError, PolicyViolationError

logger = logging.getLogger(__name__)


class PolicyOperatorEvaluator:
    """Evaluates policy rule conditions with various operators"""
    
    @staticmethod
    def evaluate(value: Any, operator: RuleOperator, target_value: Any, data_type: RuleDataType) -> bool:
        """Evaluate a condition based on operator and data type"""
        try:
            # Convert values based on data type
            if data_type == RuleDataType.STRING:
                value = str(value) if value is not None else ""
                target_value = str(target_value) if target_value is not None else ""
            elif data_type == RuleDataType.NUMBER:
                value = float(value) if value is not None else 0
                target_value = float(target_value) if target_value is not None else 0
            elif data_type == RuleDataType.BOOLEAN:
                value = bool(value) if value is not None else False
                target_value = bool(target_value) if target_value is not None else False
            elif data_type == RuleDataType.DATE:
                if isinstance(value, str):
                    value = datetime.fromisoformat(value)
                if isinstance(target_value, str):
                    target_value = datetime.fromisoformat(target_value)
            elif data_type == RuleDataType.ARRAY:
                value = value if isinstance(value, list) else []
                target_value = target_value if isinstance(target_value, list) else []
            
            # Apply operator
            if operator == RuleOperator.EQUALS:
                return value == target_value
            elif operator == RuleOperator.NOT_EQUALS:
                return value != target_value
            elif operator == RuleOperator.GREATER_THAN:
                return value > target_value
            elif operator == RuleOperator.LESS_THAN:
                return value < target_value
            elif operator == RuleOperator.GREATER_THAN_OR_EQUAL:
                return value >= target_value
            elif operator == RuleOperator.LESS_THAN_OR_EQUAL:
                return value <= target_value
            elif operator == RuleOperator.CONTAINS:
                if data_type == RuleDataType.STRING:
                    return target_value.lower() in value.lower()
                elif data_type == RuleDataType.ARRAY:
                    return target_value in value
                return False
            elif operator == RuleOperator.NOT_CONTAINS:
                if data_type == RuleDataType.STRING:
                    return target_value.lower() not in value.lower()
                elif data_type == RuleDataType.ARRAY:
                    return target_value not in value
                return True
            elif operator == RuleOperator.STARTS_WITH:
                return value.lower().startswith(target_value.lower())
            elif operator == RuleOperator.ENDS_WITH:
                return value.lower().endswith(target_value.lower())
            elif operator == RuleOperator.REGEX_MATCH:
                return bool(re.match(target_value, value))
            elif operator == RuleOperator.IN:
                return value in target_value
            elif operator == RuleOperator.NOT_IN:
                return value not in target_value
            else:
                return False
                
        except Exception as e:
            logger.warning(f"Error evaluating condition: {e}")
            return False


class PolicyEngineService:
    """Service for managing and evaluating governance policies"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.evaluator = PolicyOperatorEvaluator()
    
    # Policy Definition Management
    
    async def create_policy(
        self,
        policy_data: PolicyDefinitionCreate,
        created_by: str
    ) -> PolicyDefinitionResponse:
        """Create a new policy definition"""
        try:
            # Validate policy data
            if not policy_data.rules:
                raise ValidationError("Policy must have at least one rule")
            
            # Create policy
            policy = PolicyDefinition(
                name=policy_data.name,
                description=policy_data.description,
                category=policy_data.category,
                severity=policy_data.severity,
                is_active=policy_data.is_active,
                metadata=policy_data.metadata or {},
                created_by=created_by
            )
            
            self.db.add(policy)
            await self.db.flush()
            
            # Create rules
            for rule_data in policy_data.rules:
                rule = PolicyRule(
                    policy_id=policy.id,
                    name=rule_data.name,
                    description=rule_data.description,
                    condition=rule_data.condition.dict(),
                    action=rule_data.action.dict() if rule_data.action else None,
                    order_index=rule_data.order_index,
                    is_active=rule_data.is_active,
                    created_by=created_by
                )
                self.db.add(rule)
            
            await self.db.commit()
            await self.db.refresh(policy)
            
            # Load relationships
            await self.db.execute(
                select(PolicyDefinition)
                .options(selectinload(PolicyDefinition.rules))
                .where(PolicyDefinition.id == policy.id)
            )
            
            logger.info(f"Created policy: {policy.name} (ID: {policy.id})")
            
            return PolicyDefinitionResponse.from_orm(policy)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating policy: {e}")
            raise
    
    async def get_policy(self, policy_id: str) -> PolicyDefinitionResponse:
        """Get a policy by ID"""
        query = select(PolicyDefinition).options(
            selectinload(PolicyDefinition.rules),
            selectinload(PolicyDefinition.assignments)
        ).where(PolicyDefinition.id == policy_id)
        
        result = await self.db.execute(query)
        policy = result.scalar_one_or_none()
        
        if not policy:
            raise NotFoundError(f"Policy {policy_id} not found")
        
        return PolicyDefinitionResponse.from_orm(policy)
    
    async def list_policies(
        self,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
        severity: Optional[PolicySeverity] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[PolicyDefinitionResponse]:
        """List policies with optional filtering"""
        query = select(PolicyDefinition).options(
            selectinload(PolicyDefinition.rules)
        )
        
        # Apply filters
        conditions = []
        if category:
            conditions.append(PolicyDefinition.category == category)
        if is_active is not None:
            conditions.append(PolicyDefinition.is_active == is_active)
        if severity:
            conditions.append(PolicyDefinition.severity == severity)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(PolicyDefinition.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        policies = result.scalars().all()
        
        return [PolicyDefinitionResponse.from_orm(p) for p in policies]
    
    async def update_policy(
        self,
        policy_id: str,
        update_data: PolicyDefinitionUpdate
    ) -> PolicyDefinitionResponse:
        """Update a policy definition"""
        policy = await self.db.get(PolicyDefinition, policy_id)
        if not policy:
            raise NotFoundError(f"Policy {policy_id} not found")
        
        # Update fields
        for field, value in update_data.dict(exclude_unset=True).items():
            if field != 'rules':
                setattr(policy, field, value)
        
        policy.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(policy)
        
        return await self.get_policy(policy_id)
    
    async def delete_policy(self, policy_id: str) -> None:
        """Delete a policy (soft delete by deactivating)"""
        policy = await self.db.get(PolicyDefinition, policy_id)
        if not policy:
            raise NotFoundError(f"Policy {policy_id} not found")
        
        policy.is_active = False
        policy.updated_at = datetime.utcnow()
        
        await self.db.commit()
        
        logger.info(f"Deactivated policy: {policy_id}")
    
    # Policy Rule Management
    
    async def add_rule_to_policy(
        self,
        policy_id: str,
        rule_data: PolicyRuleCreate,
        created_by: str
    ) -> PolicyRuleResponse:
        """Add a rule to an existing policy"""
        policy = await self.db.get(PolicyDefinition, policy_id)
        if not policy:
            raise NotFoundError(f"Policy {policy_id} not found")
        
        rule = PolicyRule(
            policy_id=policy_id,
            name=rule_data.name,
            description=rule_data.description,
            condition=rule_data.condition.dict(),
            action=rule_data.action.dict() if rule_data.action else None,
            order_index=rule_data.order_index,
            is_active=rule_data.is_active,
            created_by=created_by
        )
        
        self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)
        
        logger.info(f"Added rule {rule.name} to policy {policy_id}")
        
        return PolicyRuleResponse.from_orm(rule)
    
    async def update_rule(
        self,
        rule_id: str,
        update_data: PolicyRuleUpdate
    ) -> PolicyRuleResponse:
        """Update a policy rule"""
        rule = await self.db.get(PolicyRule, rule_id)
        if not rule:
            raise NotFoundError(f"Rule {rule_id} not found")
        
        # Update fields
        for field, value in update_data.dict(exclude_unset=True).items():
            if field == 'condition' and value:
                setattr(rule, field, value.dict())
            elif field == 'action' and value:
                setattr(rule, field, value.dict())
            else:
                setattr(rule, field, value)
        
        rule.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(rule)
        
        return PolicyRuleResponse.from_orm(rule)
    
    async def delete_rule(self, rule_id: str) -> None:
        """Delete a policy rule"""
        rule = await self.db.get(PolicyRule, rule_id)
        if not rule:
            raise NotFoundError(f"Rule {rule_id} not found")
        
        await self.db.delete(rule)
        await self.db.commit()
        
        logger.info(f"Deleted rule: {rule_id}")
    
    # Policy Evaluation
    
    async def evaluate_policy(
        self,
        policy_id: str,
        context: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> PolicyEvaluationResult:
        """Evaluate a policy against given context"""
        try:
            # Get policy with rules
            policy = await self.get_policy(policy_id)
            
            if not policy.is_active:
                return PolicyEvaluationResult(
                    policy_id=policy_id,
                    result=EvaluationResult.SKIPPED,
                    passed_rules=[],
                    failed_rules=[],
                    violations=[],
                    metadata={"reason": "Policy is inactive"}
                )
            
            # Evaluate each rule
            passed_rules = []
            failed_rules = []
            violations = []
            
            for rule in sorted(policy.rules, key=lambda r: r.order_index):
                if not rule.is_active:
                    continue
                
                # Evaluate rule condition
                rule_passed = await self._evaluate_rule_condition(
                    rule.condition,
                    context
                )
                
                if rule_passed:
                    passed_rules.append(rule.id)
                else:
                    failed_rules.append(rule.id)
                    
                    # Create violation if rule failed
                    violation = await self._create_violation(
                        policy,
                        rule,
                        context,
                        user_id
                    )
                    violations.append(violation)
                    
                    # Execute action if defined
                    if rule.action:
                        await self._execute_rule_action(rule.action, context)
            
            # Determine overall result
            if not failed_rules:
                result = EvaluationResult.PASS
            elif policy.severity in [PolicySeverity.CRITICAL, PolicySeverity.HIGH]:
                result = EvaluationResult.FAIL
            else:
                result = EvaluationResult.WARNING
            
            # Create evaluation record
            evaluation = PolicyEvaluation(
                policy_id=policy_id,
                entity_type=context.get('entity_type', 'unknown'),
                entity_id=context.get('entity_id'),
                result=result,
                passed_rules=passed_rules,
                failed_rules=failed_rules,
                context=context,
                evaluated_by=user_id
            )
            
            self.db.add(evaluation)
            await self.db.commit()
            
            logger.info(
                f"Policy evaluation: {policy.name} - Result: {result}",
                extra={
                    "policy_id": policy_id,
                    "result": result,
                    "failed_rules": len(failed_rules)
                }
            )
            
            return PolicyEvaluationResult(
                policy_id=policy_id,
                policy_name=policy.name,
                result=result,
                passed_rules=passed_rules,
                failed_rules=failed_rules,
                violations=[PolicyViolationResponse.from_orm(v) for v in violations],
                metadata={
                    "severity": policy.severity,
                    "category": policy.category,
                    "evaluation_time": datetime.utcnow()
                }
            )
            
        except Exception as e:
            logger.error(f"Error evaluating policy: {e}")
            raise
    
    async def evaluate_policies_for_entity(
        self,
        entity_type: str,
        entity_id: str,
        context: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> List[PolicyEvaluationResult]:
        """Evaluate all applicable policies for an entity"""
        # Get assigned policies for entity
        assigned_policies = await self._get_assigned_policies(entity_type, entity_id)
        
        # Get global policies for entity type
        global_policies = await self.list_policies(
            category=entity_type,
            is_active=True
        )
        
        # Combine and deduplicate
        all_policies = list({p.id: p for p in assigned_policies + global_policies}.values())
        
        # Evaluate each policy
        results = []
        for policy in all_policies:
            result = await self.evaluate_policy(
                policy.id,
                {**context, 'entity_type': entity_type, 'entity_id': entity_id},
                user_id
            )
            results.append(result)
        
        return results
    
    async def _evaluate_rule_condition(
        self,
        condition: Dict[str, Any],
        context: Dict[str, Any]
    ) -> bool:
        """Evaluate a rule condition against context"""
        try:
            condition_obj = PolicyCondition(**condition)
            
            # Get value from context using field path
            field_value = self._get_field_value(condition_obj.field, context)
            
            # Evaluate using operator
            result = self.evaluator.evaluate(
                field_value,
                condition_obj.operator,
                condition_obj.value,
                condition_obj.data_type
            )
            
            # Handle compound conditions
            if condition_obj.and_conditions:
                for sub_condition in condition_obj.and_conditions:
                    if not await self._evaluate_rule_condition(sub_condition.dict(), context):
                        result = False
                        break
            
            if condition_obj.or_conditions and not result:
                for sub_condition in condition_obj.or_conditions:
                    if await self._evaluate_rule_condition(sub_condition.dict(), context):
                        result = True
                        break
            
            return result
            
        except Exception as e:
            logger.warning(f"Error evaluating condition: {e}")
            return False
    
    def _get_field_value(self, field_path: str, context: Dict[str, Any]) -> Any:
        """Get value from context using dot notation path"""
        parts = field_path.split('.')
        value = context
        
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
            
            if value is None:
                return None
        
        return value
    
    async def _create_violation(
        self,
        policy: PolicyDefinitionResponse,
        rule: PolicyRuleResponse,
        context: Dict[str, Any],
        user_id: Optional[str]
    ) -> PolicyViolation:
        """Create a policy violation record"""
        violation = PolicyViolation(
            policy_id=policy.id,
            rule_id=rule.id,
            entity_type=context.get('entity_type', 'unknown'),
            entity_id=context.get('entity_id'),
            severity=policy.severity,
            description=f"Policy '{policy.name}' violated: {rule.name}",
            context=context,
            detected_by=user_id,
            status='open'
        )
        
        self.db.add(violation)
        await self.db.flush()
        
        return violation
    
    async def _execute_rule_action(
        self,
        action: Dict[str, Any],
        context: Dict[str, Any]
    ) -> None:
        """Execute a rule action"""
        try:
            action_obj = PolicyAction(**action)
            
            if action_obj.type == 'notification':
                # Send notification (implement notification service integration)
                logger.info(f"Sending notification: {action_obj.parameters}")
            
            elif action_obj.type == 'block':
                # Block the action
                raise PolicyViolationError(
                    action_obj.parameters.get('message', 'Action blocked by policy')
                )
            
            elif action_obj.type == 'remediate':
                # Execute remediation (implement based on specific needs)
                logger.info(f"Executing remediation: {action_obj.parameters}")
            
            elif action_obj.type == 'log':
                # Log the event
                logger.warning(
                    f"Policy action logged: {action_obj.parameters.get('message', 'Policy action')}",
                    extra=context
                )
            
            elif action_obj.type == 'webhook':
                # Call webhook (implement webhook service)
                logger.info(f"Calling webhook: {action_obj.parameters.get('url')}")
            
        except Exception as e:
            logger.error(f"Error executing rule action: {e}")
    
    # Policy Assignments
    
    async def assign_policy(
        self,
        assignment_data: PolicyAssignmentCreate,
        assigned_by: str
    ) -> PolicyAssignmentResponse:
        """Assign a policy to an entity"""
        # Verify policy exists
        policy = await self.db.get(PolicyDefinition, assignment_data.policy_id)
        if not policy:
            raise NotFoundError(f"Policy {assignment_data.policy_id} not found")
        
        # Check for existing assignment
        existing = await self.db.execute(
            select(PolicyAssignment).where(
                and_(
                    PolicyAssignment.policy_id == assignment_data.policy_id,
                    PolicyAssignment.entity_type == assignment_data.entity_type,
                    PolicyAssignment.entity_id == assignment_data.entity_id
                )
            )
        )
        
        if existing.scalar_one_or_none():
            raise ValidationError("Policy already assigned to this entity")
        
        assignment = PolicyAssignment(
            policy_id=assignment_data.policy_id,
            entity_type=assignment_data.entity_type,
            entity_id=assignment_data.entity_id,
            parameters=assignment_data.parameters or {},
            assigned_by=assigned_by
        )
        
        self.db.add(assignment)
        await self.db.commit()
        await self.db.refresh(assignment)
        
        logger.info(
            f"Assigned policy {assignment_data.policy_id} to "
            f"{assignment_data.entity_type}/{assignment_data.entity_id}"
        )
        
        return PolicyAssignmentResponse.from_orm(assignment)
    
    async def unassign_policy(
        self,
        policy_id: str,
        entity_type: str,
        entity_id: str
    ) -> None:
        """Remove a policy assignment"""
        result = await self.db.execute(
            select(PolicyAssignment).where(
                and_(
                    PolicyAssignment.policy_id == policy_id,
                    PolicyAssignment.entity_type == entity_type,
                    PolicyAssignment.entity_id == entity_id
                )
            )
        )
        
        assignment = result.scalar_one_or_none()
        if not assignment:
            raise NotFoundError("Policy assignment not found")
        
        await self.db.delete(assignment)
        await self.db.commit()
        
        logger.info(f"Unassigned policy {policy_id} from {entity_type}/{entity_id}")
    
    async def _get_assigned_policies(
        self,
        entity_type: str,
        entity_id: str
    ) -> List[PolicyDefinitionResponse]:
        """Get policies assigned to an entity"""
        query = select(PolicyDefinition).join(PolicyAssignment).options(
            selectinload(PolicyDefinition.rules)
        ).where(
            and_(
                PolicyAssignment.entity_type == entity_type,
                PolicyAssignment.entity_id == entity_id,
                PolicyDefinition.is_active == True
            )
        )
        
        result = await self.db.execute(query)
        policies = result.scalars().all()
        
        return [PolicyDefinitionResponse.from_orm(p) for p in policies]
    
    # Policy Templates
    
    async def create_policy_template(
        self,
        name: str,
        description: str,
        template_data: Dict[str, Any],
        created_by: str
    ) -> PolicyTemplateResponse:
        """Create a policy template for reuse"""
        template = PolicyTemplate(
            name=name,
            description=description,
            template_data=template_data,
            category=template_data.get('category', 'general'),
            created_by=created_by
        )
        
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        
        logger.info(f"Created policy template: {name}")
        
        return PolicyTemplateResponse.from_orm(template)
    
    async def list_templates(
        self,
        category: Optional[str] = None
    ) -> List[PolicyTemplateResponse]:
        """List available policy templates"""
        query = select(PolicyTemplate)
        
        if category:
            query = query.where(PolicyTemplate.category == category)
        
        query = query.order_by(PolicyTemplate.name)
        
        result = await self.db.execute(query)
        templates = result.scalars().all()
        
        return [PolicyTemplateResponse.from_orm(t) for t in templates]
    
    async def create_policy_from_template(
        self,
        template_id: str,
        policy_name: str,
        parameters: Dict[str, Any],
        created_by: str
    ) -> PolicyDefinitionResponse:
        """Create a policy from a template"""
        template = await self.db.get(PolicyTemplate, template_id)
        if not template:
            raise NotFoundError(f"Template {template_id} not found")
        
        # Apply parameters to template
        policy_data = self._apply_template_parameters(
            template.template_data,
            parameters
        )
        
        # Update name and description
        policy_data['name'] = policy_name
        if 'description' not in parameters:
            policy_data['description'] = f"Created from template: {template.name}"
        
        # Create policy
        return await self.create_policy(
            PolicyDefinitionCreate(**policy_data),
            created_by
        )
    
    def _apply_template_parameters(
        self,
        template_data: Dict[str, Any],
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply parameters to template placeholders"""
        import copy
        data = copy.deepcopy(template_data)
        
        # Replace placeholders in string values
        def replace_placeholders(obj):
            if isinstance(obj, str):
                for key, value in parameters.items():
                    placeholder = f"{{{{{key}}}}}"
                    obj = obj.replace(placeholder, str(value))
                return obj
            elif isinstance(obj, dict):
                return {k: replace_placeholders(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_placeholders(item) for item in obj]
            return obj
        
        return replace_placeholders(data)
    
    # Policy Scheduling
    
    async def create_policy_schedule(
        self,
        schedule_data: PolicyScheduleCreate,
        created_by: str
    ) -> PolicyScheduleResponse:
        """Create a schedule for policy evaluation"""
        # Verify policy exists
        policy = await self.db.get(PolicyDefinition, schedule_data.policy_id)
        if not policy:
            raise NotFoundError(f"Policy {schedule_data.policy_id} not found")
        
        schedule = PolicySchedule(
            policy_id=schedule_data.policy_id,
            entity_type=schedule_data.entity_type,
            entity_id=schedule_data.entity_id,
            cron_expression=schedule_data.cron_expression,
            is_active=schedule_data.is_active,
            context=schedule_data.context or {},
            created_by=created_by
        )
        
        self.db.add(schedule)
        await self.db.commit()
        await self.db.refresh(schedule)
        
        logger.info(f"Created policy schedule for {policy.name}")
        
        return PolicyScheduleResponse.from_orm(schedule)
    
    async def get_due_schedules(self) -> List[PolicyScheduleResponse]:
        """Get policy schedules that are due for execution"""
        now = datetime.utcnow()
        
        query = select(PolicySchedule).where(
            and_(
                PolicySchedule.is_active == True,
                or_(
                    PolicySchedule.last_run.is_(None),
                    PolicySchedule.next_run <= now
                )
            )
        )
        
        result = await self.db.execute(query)
        schedules = result.scalars().all()
        
        return [PolicyScheduleResponse.from_orm(s) for s in schedules]
    
    async def update_schedule_execution(
        self,
        schedule_id: str,
        execution_time: datetime,
        next_run: datetime
    ) -> None:
        """Update schedule after execution"""
        schedule = await self.db.get(PolicySchedule, schedule_id)
        if not schedule:
            return
        
        schedule.last_run = execution_time
        schedule.next_run = next_run
        schedule.execution_count += 1
        
        await self.db.commit()
    
    # Violation Management
    
    async def list_violations(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        status: Optional[str] = None,
        severity: Optional[PolicySeverity] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[PolicyViolationResponse]:
        """List policy violations with filtering"""
        query = select(PolicyViolation).options(
            selectinload(PolicyViolation.policy),
            selectinload(PolicyViolation.rule)
        )
        
        conditions = []
        if entity_type:
            conditions.append(PolicyViolation.entity_type == entity_type)
        if entity_id:
            conditions.append(PolicyViolation.entity_id == entity_id)
        if status:
            conditions.append(PolicyViolation.status == status)
        if severity:
            conditions.append(PolicyViolation.severity == severity)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(PolicyViolation.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        violations = result.scalars().all()
        
        return [PolicyViolationResponse.from_orm(v) for v in violations]
    
    async def update_violation_status(
        self,
        violation_id: str,
        status: str,
        resolution_notes: Optional[str] = None,
        resolved_by: Optional[str] = None
    ) -> PolicyViolationResponse:
        """Update violation status"""
        violation = await self.db.get(PolicyViolation, violation_id)
        if not violation:
            raise NotFoundError(f"Violation {violation_id} not found")
        
        violation.status = status
        if resolution_notes:
            violation.resolution_notes = resolution_notes
        if resolved_by:
            violation.resolved_by = resolved_by
        if status in ['resolved', 'dismissed']:
            violation.resolved_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(violation)
        
        return PolicyViolationResponse.from_orm(violation)
    
    # Reporting and Analytics
    
    async def get_policy_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get policy engine metrics"""
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Total policies
        total_policies = await self.db.scalar(
            select(func.count(PolicyDefinition.id))
        )
        
        # Active policies
        active_policies = await self.db.scalar(
            select(func.count(PolicyDefinition.id)).where(
                PolicyDefinition.is_active == True
            )
        )
        
        # Evaluations in period
        evaluations = await self.db.scalar(
            select(func.count(PolicyEvaluation.id)).where(
                and_(
                    PolicyEvaluation.created_at >= start_date,
                    PolicyEvaluation.created_at <= end_date
                )
            )
        )
        
        # Evaluation results
        result_counts = await self.db.execute(
            select(
                PolicyEvaluation.result,
                func.count(PolicyEvaluation.id)
            ).where(
                and_(
                    PolicyEvaluation.created_at >= start_date,
                    PolicyEvaluation.created_at <= end_date
                )
            ).group_by(PolicyEvaluation.result)
        )
        
        results = {result: count for result, count in result_counts}
        
        # Violations by severity
        violation_counts = await self.db.execute(
            select(
                PolicyViolation.severity,
                func.count(PolicyViolation.id)
            ).where(
                and_(
                    PolicyViolation.created_at >= start_date,
                    PolicyViolation.created_at <= end_date
                )
            ).group_by(PolicyViolation.severity)
        )
        
        violations_by_severity = {sev: count for sev, count in violation_counts}
        
        # Most violated policies
        top_violated = await self.db.execute(
            select(
                PolicyDefinition.name,
                func.count(PolicyViolation.id).label('violation_count')
            ).join(PolicyViolation).where(
                and_(
                    PolicyViolation.created_at >= start_date,
                    PolicyViolation.created_at <= end_date
                )
            ).group_by(PolicyDefinition.name).order_by(
                func.count(PolicyViolation.id).desc()
            ).limit(10)
        )
        
        return {
            "total_policies": total_policies or 0,
            "active_policies": active_policies or 0,
            "evaluations": {
                "total": evaluations or 0,
                "results": results
            },
            "violations": {
                "by_severity": violations_by_severity,
                "top_violated_policies": [
                    {"policy": name, "count": count}
                    for name, count in top_violated
                ]
            },
            "period": {
                "start": start_date,
                "end": end_date
            }
        }
    
    # Default Policy Templates
    
    async def create_default_templates(self, created_by: str) -> List[PolicyTemplateResponse]:
        """Create default policy templates"""
        templates = []
        
        # Data Retention Policy Template
        retention_template = await self.create_policy_template(
            name="Data Retention Compliance",
            description="Ensure data is retained according to configured policies",
            template_data={
                "name": "Data Retention Policy - {{data_type}}",
                "description": "Enforce retention period for {{data_type}} data",
                "category": "data_governance",
                "severity": "high",
                "rules": [
                    {
                        "name": "Check retention period",
                        "description": "Verify data is within retention period",
                        "condition": {
                            "field": "data.age_days",
                            "operator": "less_than_or_equal",
                            "value": "{{retention_days}}",
                            "data_type": "number"
                        },
                        "order_index": 1,
                        "is_active": True
                    }
                ]
            },
            created_by=created_by
        )
        templates.append(retention_template)
        
        # Access Control Policy Template
        access_template = await self.create_policy_template(
            name="Access Control Policy",
            description="Enforce access control rules for sensitive data",
            template_data={
                "name": "Access Control - {{resource_type}}",
                "description": "Control access to {{resource_type}} resources",
                "category": "access_control",
                "severity": "critical",
                "rules": [
                    {
                        "name": "Check user permissions",
                        "description": "Verify user has required permissions",
                        "condition": {
                            "field": "user.permissions",
                            "operator": "contains",
                            "value": "{{required_permission}}",
                            "data_type": "array"
                        },
                        "action": {
                            "type": "block",
                            "parameters": {
                                "message": "Access denied: Missing required permission"
                            }
                        },
                        "order_index": 1,
                        "is_active": True
                    }
                ]
            },
            created_by=created_by
        )
        templates.append(access_template)
        
        # Data Quality Policy Template
        quality_template = await self.create_policy_template(
            name="Data Quality Standards",
            description="Ensure data meets quality standards",
            template_data={
                "name": "Data Quality - {{data_entity}}",
                "description": "Validate {{data_entity}} data quality",
                "category": "data_quality",
                "severity": "medium",
                "rules": [
                    {
                        "name": "Check required fields",
                        "description": "Ensure all required fields are present",
                        "condition": {
                            "field": "data.{{required_field}}",
                            "operator": "not_equals",
                            "value": None,
                            "data_type": "string"
                        },
                        "order_index": 1,
                        "is_active": True
                    },
                    {
                        "name": "Validate format",
                        "description": "Check field format is valid",
                        "condition": {
                            "field": "data.{{field_name}}",
                            "operator": "regex_match",
                            "value": "{{validation_pattern}}",
                            "data_type": "string"
                        },
                        "order_index": 2,
                        "is_active": True
                    }
                ]
            },
            created_by=created_by
        )
        templates.append(quality_template)
        
        # Privacy Policy Template
        privacy_template = await self.create_policy_template(
            name="Privacy Protection",
            description="Ensure PII is handled according to privacy rules",
            template_data={
                "name": "Privacy Policy - {{data_category}}",
                "description": "Protect privacy for {{data_category}} data",
                "category": "privacy",
                "severity": "high",
                "rules": [
                    {
                        "name": "Check encryption",
                        "description": "Verify PII is encrypted",
                        "condition": {
                            "field": "data.encryption_status",
                            "operator": "equals",
                            "value": "encrypted",
                            "data_type": "string"
                        },
                        "action": {
                            "type": "remediate",
                            "parameters": {
                                "action": "encrypt_data"
                            }
                        },
                        "order_index": 1,
                        "is_active": True
                    },
                    {
                        "name": "Check consent",
                        "description": "Verify user consent for data processing",
                        "condition": {
                            "field": "user.consents",
                            "operator": "contains",
                            "value": "{{consent_type}}",
                            "data_type": "array"
                        },
                        "order_index": 2,
                        "is_active": True
                    }
                ]
            },
            created_by=created_by
        )
        templates.append(privacy_template)
        
        logger.info(f"Created {len(templates)} default policy templates")
        
        return templates