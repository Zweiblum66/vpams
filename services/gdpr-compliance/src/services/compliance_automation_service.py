"""Compliance Automation Service for GDPR Compliance"""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload
import uuid
from enum import Enum

from ..db.models import (
    DataRequest, Consent, RiskAssessment, RiskSeverity, RiskStatus,
    PolicyEvaluation, PolicyViolation, AccessReview, AccessReviewStatus,
    DataLineageNode, DataClassification, DataRetentionPolicy
)
from ..models.schemas import (
    RiskAssessmentCreate, RiskCategory, RiskSeverity as RiskSeveritySchema
)
from ..core.exceptions import NotFoundError, ValidationError


class AutomationTriggerType(str, Enum):
    """Types of automation triggers"""
    SCHEDULED = "scheduled"
    EVENT_DRIVEN = "event_driven"
    THRESHOLD_BASED = "threshold_based"
    DEADLINE_BASED = "deadline_based"


class ComplianceCheckType(str, Enum):
    """Types of compliance checks"""
    DATA_REQUEST_OVERDUE = "data_request_overdue"
    CONSENT_EXPIRY = "consent_expiry"
    RETENTION_POLICY_VIOLATION = "retention_policy_violation"
    ACCESS_REVIEW_OVERDUE = "access_review_overdue"
    POLICY_VIOLATION = "policy_violation"
    RISK_THRESHOLD_EXCEEDED = "risk_threshold_exceeded"
    DATA_CLASSIFICATION_MISSING = "data_classification_missing"
    GDPR_DEADLINE_APPROACHING = "gdpr_deadline_approaching"


class AutomationActionType(str, Enum):
    """Types of automation actions"""
    SEND_NOTIFICATION = "send_notification"
    CREATE_TASK = "create_task"
    ESCALATE_ISSUE = "escalate_issue"
    AUTO_APPROVE = "auto_approve"
    AUTO_REJECT = "auto_reject"
    GENERATE_REPORT = "generate_report"
    CREATE_RISK_ASSESSMENT = "create_risk_assessment"
    ARCHIVE_DATA = "archive_data"
    DELETE_DATA = "delete_data"
    EXTEND_DEADLINE = "extend_deadline"


class ComplianceAutomationService:
    """Service for automated compliance monitoring and workflows"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.automation_rules = []
        self.compliance_checks = {}
    
    # Core Automation Engine
    
    async def register_automation_rule(
        self,
        rule_name: str,
        trigger_type: AutomationTriggerType,
        check_type: ComplianceCheckType,
        actions: List[Dict[str, Any]],
        conditions: Dict[str, Any],
        schedule: Optional[str] = None,
        enabled: bool = True
    ) -> str:
        """Register a new automation rule"""
        rule_id = str(uuid.uuid4())
        
        automation_rule = {
            "id": rule_id,
            "name": rule_name,
            "trigger_type": trigger_type,
            "check_type": check_type,
            "actions": actions,
            "conditions": conditions,
            "schedule": schedule,
            "enabled": enabled,
            "created_at": datetime.utcnow(),
            "last_executed": None,
            "execution_count": 0
        }
        
        self.automation_rules.append(automation_rule)
        return rule_id
    
    async def execute_automation_checks(self) -> Dict[str, Any]:
        """Execute all enabled automation rules"""
        results = {
            "executed_rules": 0,
            "triggered_actions": 0,
            "compliance_issues": [],
            "automated_resolutions": [],
            "execution_summary": {}
        }
        
        for rule in self.automation_rules:
            if not rule["enabled"]:
                continue
            
            try:
                # Execute the rule
                rule_result = await self._execute_rule(rule)
                
                if rule_result["triggered"]:
                    results["triggered_actions"] += len(rule_result["actions_executed"])
                    results["compliance_issues"].extend(rule_result["issues_found"])
                    results["automated_resolutions"].extend(rule_result["resolutions"])
                
                results["execution_summary"][rule["name"]] = rule_result
                results["executed_rules"] += 1
                
                # Update rule execution info
                rule["last_executed"] = datetime.utcnow()
                rule["execution_count"] += 1
                
            except Exception as e:
                results["execution_summary"][rule["name"]] = {
                    "triggered": False,
                    "error": str(e),
                    "execution_time": datetime.utcnow().isoformat()
                }
        
        return results
    
    async def _execute_rule(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific automation rule"""
        result = {
            "triggered": False,
            "issues_found": [],
            "actions_executed": [],
            "resolutions": [],
            "execution_time": datetime.utcnow().isoformat()
        }
        
        # Perform the compliance check
        check_result = await self._perform_compliance_check(
            rule["check_type"], 
            rule["conditions"]
        )
        
        if check_result["violations"]:
            result["triggered"] = True
            result["issues_found"] = check_result["violations"]
            
            # Execute actions for each violation
            for violation in check_result["violations"]:
                for action_config in rule["actions"]:
                    action_result = await self._execute_action(action_config, violation)
                    result["actions_executed"].append(action_result)
                    
                    if action_result["success"]:
                        result["resolutions"].append({
                            "violation": violation,
                            "action": action_config["type"],
                            "result": action_result
                        })
        
        return result
    
    async def _perform_compliance_check(
        self, 
        check_type: ComplianceCheckType, 
        conditions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform a specific compliance check"""
        violations = []
        
        if check_type == ComplianceCheckType.DATA_REQUEST_OVERDUE:
            violations = await self._check_overdue_data_requests(conditions)
        
        elif check_type == ComplianceCheckType.CONSENT_EXPIRY:
            violations = await self._check_consent_expiry(conditions)
        
        elif check_type == ComplianceCheckType.RETENTION_POLICY_VIOLATION:
            violations = await self._check_retention_violations(conditions)
        
        elif check_type == ComplianceCheckType.ACCESS_REVIEW_OVERDUE:
            violations = await self._check_overdue_access_reviews(conditions)
        
        elif check_type == ComplianceCheckType.POLICY_VIOLATION:
            violations = await self._check_policy_violations(conditions)
        
        elif check_type == ComplianceCheckType.RISK_THRESHOLD_EXCEEDED:
            violations = await self._check_risk_thresholds(conditions)
        
        elif check_type == ComplianceCheckType.DATA_CLASSIFICATION_MISSING:
            violations = await self._check_missing_classifications(conditions)
        
        elif check_type == ComplianceCheckType.GDPR_DEADLINE_APPROACHING:
            violations = await self._check_gdpr_deadlines(conditions)
        
        return {
            "check_type": check_type,
            "violations": violations,
            "total_violations": len(violations)
        }
    
    # Specific Compliance Checks
    
    async def _check_overdue_data_requests(self, conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for overdue data requests"""
        grace_period_hours = conditions.get("grace_period_hours", 72)  # GDPR: 72 hours
        cutoff_time = datetime.utcnow() - timedelta(hours=grace_period_hours)
        
        result = await self.db.execute(
            select(DataRequest).where(
                and_(
                    DataRequest.created_at < cutoff_time,
                    DataRequest.status.in_(["pending", "processing"])
                )
            )
        )
        overdue_requests = result.scalars().all()
        
        violations = []
        for request in overdue_requests:
            hours_overdue = (datetime.utcnow() - request.created_at).total_seconds() / 3600
            violations.append({
                "type": "data_request_overdue",
                "request_id": str(request.id),
                "request_type": request.request_type,
                "user_id": request.user_id,
                "hours_overdue": round(hours_overdue, 2),
                "created_at": request.created_at.isoformat(),
                "severity": "high" if hours_overdue > 168 else "medium"  # >7 days = high
            })
        
        return violations
    
    async def _check_consent_expiry(self, conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for expiring consents"""
        warning_days = conditions.get("warning_days", 30)
        warning_date = datetime.utcnow() + timedelta(days=warning_days)
        
        result = await self.db.execute(
            select(Consent).where(
                and_(
                    Consent.expiry_date <= warning_date,
                    Consent.expiry_date > datetime.utcnow(),
                    Consent.status == "active"
                )
            )
        )
        expiring_consents = result.scalars().all()
        
        violations = []
        for consent in expiring_consents:
            days_until_expiry = (consent.expiry_date - datetime.utcnow()).days
            violations.append({
                "type": "consent_expiry",
                "consent_id": str(consent.id),
                "user_id": consent.user_id,
                "purpose": consent.purpose,
                "expiry_date": consent.expiry_date.isoformat(),
                "days_until_expiry": days_until_expiry,
                "severity": "high" if days_until_expiry <= 7 else "medium"
            })
        
        return violations
    
    async def _check_retention_violations(self, conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for data retention policy violations"""
        violations = []
        
        # This would check against data retention policies
        # For now, returning empty list as retention policy logic would be complex
        
        return violations
    
    async def _check_overdue_access_reviews(self, conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for overdue access reviews"""
        result = await self.db.execute(
            select(AccessReview).where(
                and_(
                    AccessReview.due_date < datetime.utcnow(),
                    AccessReview.status.in_([AccessReviewStatus.PENDING, AccessReviewStatus.IN_PROGRESS])
                )
            )
        )
        overdue_reviews = result.scalars().all()
        
        violations = []
        for review in overdue_reviews:
            days_overdue = (datetime.utcnow() - review.due_date).days
            violations.append({
                "type": "access_review_overdue",
                "review_id": str(review.id),
                "review_name": review.review_name,
                "reviewer": review.reviewer,
                "due_date": review.due_date.isoformat(),
                "days_overdue": days_overdue,
                "severity": "critical" if days_overdue > 30 else "high"
            })
        
        return violations
    
    async def _check_policy_violations(self, conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for unresolved policy violations"""
        result = await self.db.execute(
            select(PolicyViolation).where(
                PolicyViolation.resolution_status == "open"
            )
        )
        open_violations = result.scalars().all()
        
        violations = []
        for violation in open_violations:
            age_days = (datetime.utcnow() - violation.detected_at).days
            violations.append({
                "type": "policy_violation",
                "violation_id": str(violation.id),
                "policy_id": str(violation.policy_id),
                "violation_type": violation.violation_type,
                "detected_at": violation.detected_at.isoformat(),
                "age_days": age_days,
                "severity": violation.severity
            })
        
        return violations
    
    async def _check_risk_thresholds(self, conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for risks exceeding thresholds"""
        risk_score_threshold = conditions.get("risk_score_threshold", 7.0)
        
        result = await self.db.execute(
            select(RiskAssessment).where(
                and_(
                    RiskAssessment.risk_score >= risk_score_threshold,
                    RiskAssessment.status.in_([RiskStatus.IDENTIFIED, RiskStatus.ANALYZING])
                )
            )
        )
        high_risks = result.scalars().all()
        
        violations = []
        for risk in high_risks:
            violations.append({
                "type": "risk_threshold_exceeded",
                "risk_id": str(risk.id),
                "title": risk.title,
                "risk_score": risk.risk_score,
                "severity": risk.severity.value,
                "category": risk.risk_category.value,
                "identified_at": risk.identified_at.isoformat(),
                "severity": "critical"
            })
        
        return violations
    
    async def _check_missing_classifications(self, conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for data without proper classification"""
        # This would check for unclassified sensitive data
        # Simplified implementation
        violations = []
        return violations
    
    async def _check_gdpr_deadlines(self, conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for approaching GDPR deadlines"""
        warning_hours = conditions.get("warning_hours", 24)
        
        # Check for data requests approaching 72-hour deadline
        deadline_approaches = datetime.utcnow() + timedelta(hours=warning_hours)
        gdpr_deadline = datetime.utcnow() + timedelta(hours=72)
        
        result = await self.db.execute(
            select(DataRequest).where(
                and_(
                    DataRequest.created_at <= deadline_approaches,
                    DataRequest.created_at > gdpr_deadline - timedelta(hours=72),
                    DataRequest.status.in_(["pending", "processing"])
                )
            )
        )
        approaching_deadline = result.scalars().all()
        
        violations = []
        for request in approaching_deadline:
            hours_remaining = 72 - (datetime.utcnow() - request.created_at).total_seconds() / 3600
            violations.append({
                "type": "gdpr_deadline_approaching",
                "request_id": str(request.id),
                "request_type": request.request_type,
                "user_id": request.user_id,
                "hours_remaining": round(hours_remaining, 2),
                "deadline": (request.created_at + timedelta(hours=72)).isoformat(),
                "severity": "critical" if hours_remaining < 6 else "high"
            })
        
        return violations
    
    # Automation Actions
    
    async def _execute_action(
        self, 
        action_config: Dict[str, Any], 
        violation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute an automation action"""
        action_type = action_config["type"]
        
        try:
            if action_type == AutomationActionType.SEND_NOTIFICATION:
                return await self._send_notification(action_config, violation)
            
            elif action_type == AutomationActionType.CREATE_TASK:
                return await self._create_task(action_config, violation)
            
            elif action_type == AutomationActionType.ESCALATE_ISSUE:
                return await self._escalate_issue(action_config, violation)
            
            elif action_type == AutomationActionType.CREATE_RISK_ASSESSMENT:
                return await self._create_risk_assessment(action_config, violation)
            
            elif action_type == AutomationActionType.GENERATE_REPORT:
                return await self._generate_report(action_config, violation)
            
            elif action_type == AutomationActionType.EXTEND_DEADLINE:
                return await self._extend_deadline(action_config, violation)
            
            else:
                return {
                    "action_type": action_type,
                    "success": False,
                    "error": f"Unknown action type: {action_type}"
                }
        
        except Exception as e:
            return {
                "action_type": action_type,
                "success": False,
                "error": str(e)
            }
    
    async def _send_notification(
        self, 
        action_config: Dict[str, Any], 
        violation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send notification action"""
        # In a real implementation, this would integrate with email/SMS/Slack
        notification = {
            "recipient": action_config.get("recipient"),
            "subject": action_config.get("subject", f"Compliance Alert: {violation['type']}"),
            "message": action_config.get("message", f"Compliance violation detected: {violation}"),
            "priority": violation.get("severity", "medium"),
            "sent_at": datetime.utcnow().isoformat()
        }
        
        return {
            "action_type": "send_notification",
            "success": True,
            "details": notification
        }
    
    async def _create_task(
        self, 
        action_config: Dict[str, Any], 
        violation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create task action"""
        task = {
            "title": action_config.get("title", f"Resolve {violation['type']}"),
            "description": action_config.get("description", f"Compliance violation: {violation}"),
            "assignee": action_config.get("assignee"),
            "priority": violation.get("severity", "medium"),
            "due_date": (datetime.utcnow() + timedelta(hours=action_config.get("due_hours", 24))).isoformat(),
            "created_at": datetime.utcnow().isoformat(),
            "violation_data": violation
        }
        
        return {
            "action_type": "create_task",
            "success": True,
            "details": task
        }
    
    async def _escalate_issue(
        self, 
        action_config: Dict[str, Any], 
        violation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Escalate issue action"""
        escalation = {
            "escalated_to": action_config.get("escalate_to"),
            "escalation_level": action_config.get("level", "manager"),
            "reason": f"Automated escalation for {violation['type']}",
            "violation_data": violation,
            "escalated_at": datetime.utcnow().isoformat()
        }
        
        return {
            "action_type": "escalate_issue",
            "success": True,
            "details": escalation
        }
    
    async def _create_risk_assessment(
        self, 
        action_config: Dict[str, Any], 
        violation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create risk assessment action"""
        # This would create an actual risk assessment
        risk_data = {
            "title": f"Automated Risk Assessment: {violation['type']}",
            "description": f"Risk assessment created due to compliance violation: {violation}",
            "risk_category": action_config.get("category", RiskCategory.COMPLIANCE_VIOLATION),
            "likelihood_score": action_config.get("likelihood_score", 4),
            "impact_score": action_config.get("impact_score", 4),
            "created_at": datetime.utcnow().isoformat(),
            "source_violation": violation
        }
        
        return {
            "action_type": "create_risk_assessment",
            "success": True,
            "details": risk_data
        }
    
    async def _generate_report(
        self, 
        action_config: Dict[str, Any], 
        violation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate report action"""
        report = {
            "report_type": action_config.get("report_type", "compliance_violation"),
            "report_data": violation,
            "generated_at": datetime.utcnow().isoformat(),
            "format": action_config.get("format", "json")
        }
        
        return {
            "action_type": "generate_report",
            "success": True,
            "details": report
        }
    
    async def _extend_deadline(
        self, 
        action_config: Dict[str, Any], 
        violation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extend deadline action"""
        extension = {
            "original_deadline": violation.get("deadline"),
            "extension_hours": action_config.get("extension_hours", 24),
            "new_deadline": (datetime.utcnow() + timedelta(hours=action_config.get("extension_hours", 24))).isoformat(),
            "reason": action_config.get("reason", "Automated deadline extension"),
            "extended_at": datetime.utcnow().isoformat()
        }
        
        return {
            "action_type": "extend_deadline",
            "success": True,
            "details": extension
        }
    
    # Compliance Monitoring Dashboard
    
    async def get_compliance_status(self) -> Dict[str, Any]:
        """Get overall compliance status"""
        try:
            # Execute all checks without actions to get current status
            status = {
                "overall_status": "compliant",
                "risk_level": "low",
                "active_violations": 0,
                "checks_performed": 0,
                "last_check": datetime.utcnow().isoformat(),
                "violation_summary": {},
                "trends": {}
            }
            
            all_violations = []
            for rule in self.automation_rules:
                if rule["enabled"]:
                    check_result = await self._perform_compliance_check(
                        rule["check_type"], 
                        rule["conditions"]
                    )
                    all_violations.extend(check_result["violations"])
                    status["checks_performed"] += 1
            
            # Analyze violations
            status["active_violations"] = len(all_violations)
            
            if all_violations:
                # Categorize violations
                violation_types = {}
                severity_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
                
                for violation in all_violations:
                    v_type = violation["type"]
                    severity = violation.get("severity", "medium")
                    
                    violation_types[v_type] = violation_types.get(v_type, 0) + 1
                    severity_counts[severity] += 1
                
                status["violation_summary"] = {
                    "by_type": violation_types,
                    "by_severity": severity_counts
                }
                
                # Determine overall status
                if severity_counts["critical"] > 0:
                    status["overall_status"] = "non_compliant"
                    status["risk_level"] = "critical"
                elif severity_counts["high"] > 0:
                    status["overall_status"] = "at_risk"
                    status["risk_level"] = "high"
                elif severity_counts["medium"] > 0:
                    status["overall_status"] = "needs_attention"
                    status["risk_level"] = "medium"
            
            return status
            
        except Exception as e:
            raise ValidationError(f"Failed to get compliance status: {str(e)}")
    
    async def get_automation_metrics(self) -> Dict[str, Any]:
        """Get automation execution metrics"""
        total_rules = len(self.automation_rules)
        enabled_rules = len([r for r in self.automation_rules if r["enabled"]])
        
        metrics = {
            "total_rules": total_rules,
            "enabled_rules": enabled_rules,
            "disabled_rules": total_rules - enabled_rules,
            "rules_by_type": {},
            "execution_stats": {},
            "performance_metrics": {}
        }
        
        # Analyze rules by type
        for rule in self.automation_rules:
            check_type = rule["check_type"]
            metrics["rules_by_type"][check_type] = metrics["rules_by_type"].get(check_type, 0) + 1
            
            # Execution stats
            if rule["last_executed"]:
                rule_name = rule["name"]
                metrics["execution_stats"][rule_name] = {
                    "last_executed": rule["last_executed"].isoformat(),
                    "execution_count": rule["execution_count"]
                }
        
        return metrics
    
    # Rule Management
    
    async def get_automation_rules(self) -> List[Dict[str, Any]]:
        """Get all automation rules"""
        return self.automation_rules
    
    async def enable_rule(self, rule_id: str) -> bool:
        """Enable an automation rule"""
        for rule in self.automation_rules:
            if rule["id"] == rule_id:
                rule["enabled"] = True
                return True
        return False
    
    async def disable_rule(self, rule_id: str) -> bool:
        """Disable an automation rule"""
        for rule in self.automation_rules:
            if rule["id"] == rule_id:
                rule["enabled"] = False
                return True
        return False
    
    async def delete_rule(self, rule_id: str) -> bool:
        """Delete an automation rule"""
        for i, rule in enumerate(self.automation_rules):
            if rule["id"] == rule_id:
                del self.automation_rules[i]
                return True
        return False
    
    # Default Rules Setup
    
    async def setup_default_automation_rules(self) -> List[str]:
        """Setup default automation rules for GDPR compliance"""
        rule_ids = []
        
        # Rule 1: Overdue Data Requests
        rule_ids.append(await self.register_automation_rule(
            rule_name="GDPR Data Request Deadline Monitor",
            trigger_type=AutomationTriggerType.SCHEDULED,
            check_type=ComplianceCheckType.DATA_REQUEST_OVERDUE,
            actions=[
                {
                    "type": AutomationActionType.SEND_NOTIFICATION,
                    "recipient": "privacy@company.com",
                    "subject": "URGENT: GDPR Data Request Overdue"
                },
                {
                    "type": AutomationActionType.CREATE_TASK,
                    "assignee": "privacy_officer",
                    "due_hours": 6
                }
            ],
            conditions={"grace_period_hours": 60},  # Alert 12 hours before deadline
            schedule="0 */4 * * *"  # Every 4 hours
        ))
        
        # Rule 2: Consent Expiry Warning
        rule_ids.append(await self.register_automation_rule(
            rule_name="Consent Expiry Warning",
            trigger_type=AutomationTriggerType.SCHEDULED,
            check_type=ComplianceCheckType.CONSENT_EXPIRY,
            actions=[
                {
                    "type": AutomationActionType.SEND_NOTIFICATION,
                    "recipient": "marketing@company.com",
                    "subject": "Consent Expiring Soon"
                }
            ],
            conditions={"warning_days": 30},
            schedule="0 9 * * *"  # Daily at 9 AM
        ))
        
        # Rule 3: High Risk Assessment Alert
        rule_ids.append(await self.register_automation_rule(
            rule_name="High Risk Assessment Alert",
            trigger_type=AutomationTriggerType.THRESHOLD_BASED,
            check_type=ComplianceCheckType.RISK_THRESHOLD_EXCEEDED,
            actions=[
                {
                    "type": AutomationActionType.ESCALATE_ISSUE,
                    "escalate_to": "ciso@company.com",
                    "level": "executive"
                },
                {
                    "type": AutomationActionType.CREATE_TASK,
                    "assignee": "risk_manager",
                    "due_hours": 24
                }
            ],
            conditions={"risk_score_threshold": 8.0},
            schedule="0 */2 * * *"  # Every 2 hours
        ))
        
        # Rule 4: Access Review Overdue
        rule_ids.append(await self.register_automation_rule(
            rule_name="Access Review Overdue Alert",
            trigger_type=AutomationTriggerType.DEADLINE_BASED,
            check_type=ComplianceCheckType.ACCESS_REVIEW_OVERDUE,
            actions=[
                {
                    "type": AutomationActionType.SEND_NOTIFICATION,
                    "recipient": "security@company.com",
                    "subject": "Access Review Overdue"
                },
                {
                    "type": AutomationActionType.ESCALATE_ISSUE,
                    "escalate_to": "security_manager",
                    "level": "manager"
                }
            ],
            conditions={},
            schedule="0 10 * * 1"  # Weekly on Monday at 10 AM
        ))
        
        # Rule 5: GDPR Deadline Approaching
        rule_ids.append(await self.register_automation_rule(
            rule_name="GDPR Deadline Critical Alert",
            trigger_type=AutomationTriggerType.DEADLINE_BASED,
            check_type=ComplianceCheckType.GDPR_DEADLINE_APPROACHING,
            actions=[
                {
                    "type": AutomationActionType.SEND_NOTIFICATION,
                    "recipient": "privacy@company.com",
                    "subject": "CRITICAL: GDPR Deadline Approaching"
                },
                {
                    "type": AutomationActionType.ESCALATE_ISSUE,
                    "escalate_to": "dpo@company.com",
                    "level": "executive"
                }
            ],
            conditions={"warning_hours": 12},
            schedule="0 * * * *"  # Every hour
        ))
        
        return rule_ids