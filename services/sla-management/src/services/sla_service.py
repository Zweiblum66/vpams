"""
Service Level Agreement (SLA) Management Service for MAMS platform.
"""
import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func

logger = structlog.get_logger()


class SLAType(Enum):
    """SLA agreement types."""
    UPTIME = "uptime"
    PERFORMANCE = "performance"
    SUPPORT = "support"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    DATA_RECOVERY = "data_recovery"
    AVAILABILITY = "availability"


class SLATier(Enum):
    """SLA service tiers."""
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    PREMIUM = "premium"


class SLAStatus(Enum):
    """SLA status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    PENDING = "pending"


class MetricType(Enum):
    """SLA metric types."""
    PERCENTAGE = "percentage"
    TIME = "time"
    COUNT = "count"
    BOOLEAN = "boolean"


@dataclass
class SLAMetric:
    """SLA metric definition."""
    metric_id: str
    name: str
    description: str
    type: MetricType
    target_value: float
    measurement_unit: str
    measurement_period: str  # hourly, daily, weekly, monthly, quarterly, yearly
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None
    calculation_method: str = "average"  # average, minimum, maximum, sum, count


@dataclass
class SLAPenalty:
    """SLA penalty definition."""
    penalty_id: str
    name: str
    description: str
    trigger_condition: str
    penalty_type: str  # credit, refund, termination_right
    penalty_amount: float
    penalty_unit: str  # percentage, fixed_amount, service_credits
    max_penalty_per_period: Optional[float] = None
    escalation_rules: List[str] = None


@dataclass
class SLANotification:
    """SLA notification configuration."""
    notification_id: str
    trigger_condition: str
    notification_type: str  # email, webhook, sms, slack
    recipients: List[str]
    escalation_delay: Optional[int] = None  # minutes
    template: str = ""
    enabled: bool = True


@dataclass
class SLAAgreement:
    """Complete SLA agreement."""
    agreement_id: str
    customer_id: str
    tier: SLATier
    name: str
    description: str
    effective_date: datetime
    expiration_date: Optional[datetime]
    status: SLAStatus
    metrics: List[SLAMetric]
    penalties: List[SLAPenalty]
    notifications: List[SLANotification]
    terms_and_conditions: str
    created_at: datetime
    updated_at: datetime
    version: str = "1.0"
    auto_renewal: bool = True
    billing_cycle: str = "monthly"


class SLAService:
    """Service for managing SLA agreements and monitoring."""
    
    def __init__(self):
        self.predefined_slas = self._initialize_predefined_slas()
    
    def _initialize_predefined_slas(self) -> Dict[SLATier, SLAAgreement]:
        """Initialize predefined SLA agreements for different tiers."""
        return {
            SLATier.BASIC: self._create_basic_sla(),
            SLATier.PROFESSIONAL: self._create_professional_sla(),
            SLATier.ENTERPRISE: self._create_enterprise_sla(),
            SLATier.PREMIUM: self._create_premium_sla()
        }
    
    def _create_basic_sla(self) -> SLAAgreement:
        """Create Basic tier SLA agreement."""
        metrics = [
            SLAMetric(
                metric_id="uptime_basic",
                name="System Uptime",
                description="Percentage of time the system is available and operational",
                type=MetricType.PERCENTAGE,
                target_value=99.0,
                measurement_unit="percentage",
                measurement_period="monthly",
                threshold_warning=98.5,
                threshold_critical=98.0
            ),
            SLAMetric(
                metric_id="response_time_basic",
                name="API Response Time",
                description="Average response time for API requests",
                type=MetricType.TIME,
                target_value=2000,
                measurement_unit="milliseconds",
                measurement_period="hourly",
                threshold_warning=3000,
                threshold_critical=5000
            ),
            SLAMetric(
                metric_id="support_response_basic",
                name="Support Response Time",
                description="Time to first response for support tickets",
                type=MetricType.TIME,
                target_value=24,
                measurement_unit="hours",
                measurement_period="daily",
                threshold_warning=36,
                threshold_critical=48
            )
        ]
        
        penalties = [
            SLAPenalty(
                penalty_id="uptime_penalty_basic",
                name="Uptime Penalty",
                description="Service credits for uptime below 99%",
                trigger_condition="uptime < 99%",
                penalty_type="credit",
                penalty_amount=5.0,
                penalty_unit="percentage",
                max_penalty_per_period=25.0
            )
        ]
        
        notifications = [
            SLANotification(
                notification_id="uptime_alert_basic",
                trigger_condition="uptime < 99%",
                notification_type="email",
                recipients=["customer@example.com"],
                template="uptime_breach_basic"
            )
        ]
        
        return SLAAgreement(
            agreement_id="basic_sla_template",
            customer_id="template",
            tier=SLATier.BASIC,
            name="MAMS Basic Service Level Agreement",
            description="Basic service level agreement for MAMS platform",
            effective_date=datetime.now(timezone.utc),
            expiration_date=None,
            status=SLAStatus.ACTIVE,
            metrics=metrics,
            penalties=penalties,
            notifications=notifications,
            terms_and_conditions=self._get_basic_terms(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
    
    def _create_professional_sla(self) -> SLAAgreement:
        """Create Professional tier SLA agreement."""
        metrics = [
            SLAMetric(
                metric_id="uptime_professional",
                name="System Uptime",
                description="Percentage of time the system is available and operational",
                type=MetricType.PERCENTAGE,
                target_value=99.5,
                measurement_unit="percentage",
                measurement_period="monthly",
                threshold_warning=99.0,
                threshold_critical=98.5
            ),
            SLAMetric(
                metric_id="response_time_professional",
                name="API Response Time",
                description="Average response time for API requests",
                type=MetricType.TIME,
                target_value=1000,
                measurement_unit="milliseconds",
                measurement_period="hourly",
                threshold_warning=1500,
                threshold_critical=2000
            ),
            SLAMetric(
                metric_id="support_response_professional",
                name="Support Response Time",
                description="Time to first response for support tickets",
                type=MetricType.TIME,
                target_value=8,
                measurement_unit="hours",
                measurement_period="daily",
                threshold_warning=12,
                threshold_critical=24
            ),
            SLAMetric(
                metric_id="data_backup_professional",
                name="Data Backup Success Rate",
                description="Percentage of successful data backups",
                type=MetricType.PERCENTAGE,
                target_value=99.9,
                measurement_unit="percentage",
                measurement_period="daily",
                threshold_warning=99.5,
                threshold_critical=99.0
            )
        ]
        
        penalties = [
            SLAPenalty(
                penalty_id="uptime_penalty_professional",
                name="Uptime Penalty",
                description="Service credits for uptime below 99.5%",
                trigger_condition="uptime < 99.5%",
                penalty_type="credit",
                penalty_amount=10.0,
                penalty_unit="percentage",
                max_penalty_per_period=50.0
            ),
            SLAPenalty(
                penalty_id="performance_penalty_professional",
                name="Performance Penalty",
                description="Service credits for response time breaches",
                trigger_condition="response_time > 2000ms",
                penalty_type="credit",
                penalty_amount=5.0,
                penalty_unit="percentage",
                max_penalty_per_period=25.0
            )
        ]
        
        notifications = [
            SLANotification(
                notification_id="uptime_alert_professional",
                trigger_condition="uptime < 99.5%",
                notification_type="email",
                recipients=["customer@example.com", "support@mams.example.com"],
                template="uptime_breach_professional"
            ),
            SLANotification(
                notification_id="performance_alert_professional",
                trigger_condition="response_time > 1500ms",
                notification_type="webhook",
                recipients=["https://customer.example.com/webhook"],
                template="performance_degradation"
            )
        ]
        
        return SLAAgreement(
            agreement_id="professional_sla_template",
            customer_id="template",
            tier=SLATier.PROFESSIONAL,
            name="MAMS Professional Service Level Agreement",
            description="Professional service level agreement for MAMS platform",
            effective_date=datetime.now(timezone.utc),
            expiration_date=None,
            status=SLAStatus.ACTIVE,
            metrics=metrics,
            penalties=penalties,
            notifications=notifications,
            terms_and_conditions=self._get_professional_terms(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
    
    def _create_enterprise_sla(self) -> SLAAgreement:
        """Create Enterprise tier SLA agreement."""
        metrics = [
            SLAMetric(
                metric_id="uptime_enterprise",
                name="System Uptime",
                description="Percentage of time the system is available and operational",
                type=MetricType.PERCENTAGE,
                target_value=99.9,
                measurement_unit="percentage",
                measurement_period="monthly",
                threshold_warning=99.7,
                threshold_critical=99.5
            ),
            SLAMetric(
                metric_id="response_time_enterprise",
                name="API Response Time",
                description="Average response time for API requests",
                type=MetricType.TIME,
                target_value=500,
                measurement_unit="milliseconds",
                measurement_period="hourly",
                threshold_warning=750,
                threshold_critical=1000
            ),
            SLAMetric(
                metric_id="support_response_enterprise",
                name="Support Response Time",
                description="Time to first response for support tickets",
                type=MetricType.TIME,
                target_value=2,
                measurement_unit="hours",
                measurement_period="daily",
                threshold_warning=4,
                threshold_critical=8
            ),
            SLAMetric(
                metric_id="data_backup_enterprise",
                name="Data Backup Success Rate",
                description="Percentage of successful data backups",
                type=MetricType.PERCENTAGE,
                target_value=99.99,
                measurement_unit="percentage",
                measurement_period="daily",
                threshold_warning=99.9,
                threshold_critical=99.8
            ),
            SLAMetric(
                metric_id="security_compliance_enterprise",
                name="Security Compliance Score",
                description="Overall security compliance score",
                type=MetricType.PERCENTAGE,
                target_value=95.0,
                measurement_unit="percentage",
                measurement_period="weekly",
                threshold_warning=90.0,
                threshold_critical=85.0
            )
        ]
        
        penalties = [
            SLAPenalty(
                penalty_id="uptime_penalty_enterprise",
                name="Uptime Penalty",
                description="Service credits for uptime below 99.9%",
                trigger_condition="uptime < 99.9%",
                penalty_type="credit",
                penalty_amount=15.0,
                penalty_unit="percentage",
                max_penalty_per_period=100.0
            ),
            SLAPenalty(
                penalty_id="performance_penalty_enterprise",
                name="Performance Penalty",
                description="Service credits for response time breaches",
                trigger_condition="response_time > 1000ms",
                penalty_type="credit",
                penalty_amount=10.0,
                penalty_unit="percentage",
                max_penalty_per_period=50.0
            ),
            SLAPenalty(
                penalty_id="support_penalty_enterprise",
                name="Support Response Penalty",
                description="Service credits for support response delays",
                trigger_condition="support_response > 8h",
                penalty_type="credit",
                penalty_amount=5.0,
                penalty_unit="percentage",
                max_penalty_per_period=25.0
            )
        ]
        
        notifications = [
            SLANotification(
                notification_id="uptime_alert_enterprise",
                trigger_condition="uptime < 99.9%",
                notification_type="email",
                recipients=["customer@example.com", "cto@customer.example.com"],
                escalation_delay=15,
                template="uptime_breach_enterprise"
            ),
            SLANotification(
                notification_id="performance_alert_enterprise",
                trigger_condition="response_time > 750ms",
                notification_type="slack",
                recipients=["#alerts"],
                template="performance_degradation_enterprise"
            )
        ]
        
        return SLAAgreement(
            agreement_id="enterprise_sla_template",
            customer_id="template",
            tier=SLATier.ENTERPRISE,
            name="MAMS Enterprise Service Level Agreement",
            description="Enterprise service level agreement for MAMS platform",
            effective_date=datetime.now(timezone.utc),
            expiration_date=None,
            status=SLAStatus.ACTIVE,
            metrics=metrics,
            penalties=penalties,
            notifications=notifications,
            terms_and_conditions=self._get_enterprise_terms(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
    
    def _create_premium_sla(self) -> SLAAgreement:
        """Create Premium tier SLA agreement."""
        metrics = [
            SLAMetric(
                metric_id="uptime_premium",
                name="System Uptime",
                description="Percentage of time the system is available and operational",
                type=MetricType.PERCENTAGE,
                target_value=99.99,
                measurement_unit="percentage",
                measurement_period="monthly",
                threshold_warning=99.95,
                threshold_critical=99.9
            ),
            SLAMetric(
                metric_id="response_time_premium",
                name="API Response Time",
                description="Average response time for API requests",
                type=MetricType.TIME,
                target_value=250,
                measurement_unit="milliseconds",
                measurement_period="hourly",
                threshold_warning=400,
                threshold_critical=500
            ),
            SLAMetric(
                metric_id="support_response_premium",
                name="Support Response Time",
                description="Time to first response for support tickets",
                type=MetricType.TIME,
                target_value=1,
                measurement_unit="hours",
                measurement_period="daily",
                threshold_warning=2,
                threshold_critical=4
            ),
            SLAMetric(
                metric_id="data_backup_premium",
                name="Data Backup Success Rate",
                description="Percentage of successful data backups",
                type=MetricType.PERCENTAGE,
                target_value=100.0,
                measurement_unit="percentage",
                measurement_period="daily",
                threshold_warning=99.99,
                threshold_critical=99.95
            ),
            SLAMetric(
                metric_id="security_compliance_premium",
                name="Security Compliance Score",
                description="Overall security compliance score",
                type=MetricType.PERCENTAGE,
                target_value=98.0,
                measurement_unit="percentage",
                measurement_period="weekly",
                threshold_warning=95.0,
                threshold_critical=90.0
            ),
            SLAMetric(
                metric_id="disaster_recovery_premium",
                name="Disaster Recovery RTO",
                description="Recovery Time Objective for disaster scenarios",
                type=MetricType.TIME,
                target_value=4,
                measurement_unit="hours",
                measurement_period="quarterly",
                threshold_warning=6,
                threshold_critical=8
            )
        ]
        
        penalties = [
            SLAPenalty(
                penalty_id="uptime_penalty_premium",
                name="Uptime Penalty",
                description="Service credits for uptime below 99.99%",
                trigger_condition="uptime < 99.99%",
                penalty_type="credit",
                penalty_amount=25.0,
                penalty_unit="percentage",
                max_penalty_per_period=100.0
            ),
            SLAPenalty(
                penalty_id="performance_penalty_premium",
                name="Performance Penalty",
                description="Service credits for response time breaches",
                trigger_condition="response_time > 500ms",
                penalty_type="credit",
                penalty_amount=15.0,
                penalty_unit="percentage",
                max_penalty_per_period=75.0
            ),
            SLAPenalty(
                penalty_id="support_penalty_premium",
                name="Support Response Penalty",
                description="Service credits for support response delays",
                trigger_condition="support_response > 4h",
                penalty_type="credit",
                penalty_amount=10.0,
                penalty_unit="percentage",
                max_penalty_per_period=50.0
            )
        ]
        
        notifications = [
            SLANotification(
                notification_id="uptime_alert_premium",
                trigger_condition="uptime < 99.99%",
                notification_type="email",
                recipients=["customer@example.com", "cto@customer.example.com", "ceo@customer.example.com"],
                escalation_delay=5,
                template="uptime_breach_premium"
            ),
            SLANotification(
                notification_id="performance_alert_premium",
                trigger_condition="response_time > 400ms",
                notification_type="sms",
                recipients=["+1234567890"],
                template="performance_degradation_premium"
            )
        ]
        
        return SLAAgreement(
            agreement_id="premium_sla_template",
            customer_id="template",
            tier=SLATier.PREMIUM,
            name="MAMS Premium Service Level Agreement",
            description="Premium service level agreement for MAMS platform with guaranteed 99.99% uptime",
            effective_date=datetime.now(timezone.utc),
            expiration_date=None,
            status=SLAStatus.ACTIVE,
            metrics=metrics,
            penalties=penalties,
            notifications=notifications,
            terms_and_conditions=self._get_premium_terms(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
    
    async def create_customer_sla(
        self,
        customer_id: str,
        tier: SLATier,
        custom_metrics: Optional[List[SLAMetric]] = None,
        custom_penalties: Optional[List[SLAPenalty]] = None,
        custom_notifications: Optional[List[SLANotification]] = None
    ) -> SLAAgreement:
        """Create a customized SLA agreement for a customer."""
        template = self.predefined_slas[tier]
        
        agreement = SLAAgreement(
            agreement_id=f"sla_{customer_id}_{uuid.uuid4().hex[:8]}",
            customer_id=customer_id,
            tier=tier,
            name=f"MAMS {tier.value.title()} SLA - {customer_id}",
            description=template.description,
            effective_date=datetime.now(timezone.utc),
            expiration_date=datetime.now(timezone.utc) + timedelta(days=365),
            status=SLAStatus.PENDING,
            metrics=custom_metrics or template.metrics,
            penalties=custom_penalties or template.penalties,
            notifications=custom_notifications or template.notifications,
            terms_and_conditions=template.terms_and_conditions,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        logger.info(
            "Created customer SLA agreement",
            customer_id=customer_id,
            agreement_id=agreement.agreement_id,
            tier=tier.value
        )
        
        return agreement
    
    async def activate_sla(self, agreement_id: str) -> bool:
        """Activate an SLA agreement."""
        # In a real implementation, this would update the database
        logger.info("SLA agreement activated", agreement_id=agreement_id)
        return True
    
    async def calculate_sla_compliance(
        self,
        agreement: SLAAgreement,
        period_start: datetime,
        period_end: datetime
    ) -> Dict[str, Any]:
        """Calculate SLA compliance for a given period."""
        compliance_results = {
            "agreement_id": agreement.agreement_id,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "metric_results": [],
            "overall_compliance": 0.0,
            "penalties_triggered": [],
            "total_credits": 0.0
        }
        
        total_metrics = len(agreement.metrics)
        compliant_metrics = 0
        
        for metric in agreement.metrics:
            # Simulate metric calculation
            actual_value = await self._simulate_metric_value(metric)
            
            is_compliant = self._check_metric_compliance(metric, actual_value)
            if is_compliant:
                compliant_metrics += 1
            
            metric_result = {
                "metric_id": metric.metric_id,
                "name": metric.name,
                "target_value": metric.target_value,
                "actual_value": actual_value,
                "compliant": is_compliant,
                "measurement_unit": metric.measurement_unit
            }
            compliance_results["metric_results"].append(metric_result)
            
            # Check for penalty triggers
            for penalty in agreement.penalties:
                if self._check_penalty_trigger(penalty, metric, actual_value):
                    penalty_amount = self._calculate_penalty_amount(penalty, metric, actual_value)
                    compliance_results["penalties_triggered"].append({
                        "penalty_id": penalty.penalty_id,
                        "name": penalty.name,
                        "amount": penalty_amount,
                        "unit": penalty.penalty_unit,
                        "triggered_by": metric.metric_id
                    })
                    compliance_results["total_credits"] += penalty_amount
        
        compliance_results["overall_compliance"] = (compliant_metrics / total_metrics) * 100
        
        return compliance_results
    
    async def _simulate_metric_value(self, metric: SLAMetric) -> float:
        """Simulate metric value for demonstration purposes."""
        import random
        
        if metric.type == MetricType.PERCENTAGE:
            # Generate value around target with some variance
            variance = 2.0  # ±2%
            return max(0, min(100, metric.target_value + random.uniform(-variance, variance)))
        elif metric.type == MetricType.TIME:
            # Generate time value with variance
            variance_percent = 0.3  # ±30%
            variance = metric.target_value * variance_percent
            return max(0, metric.target_value + random.uniform(-variance, variance))
        else:
            return metric.target_value
    
    def _check_metric_compliance(self, metric: SLAMetric, actual_value: float) -> bool:
        """Check if metric value meets SLA target."""
        if metric.type == MetricType.PERCENTAGE:
            return actual_value >= metric.target_value
        elif metric.type == MetricType.TIME:
            return actual_value <= metric.target_value
        else:
            return actual_value >= metric.target_value
    
    def _check_penalty_trigger(self, penalty: SLAPenalty, metric: SLAMetric, actual_value: float) -> bool:
        """Check if penalty should be triggered based on metric value."""
        # Simplified penalty trigger logic
        if "uptime" in penalty.penalty_id and metric.metric_id.startswith("uptime"):
            target_uptime = float(penalty.trigger_condition.split("<")[1].strip().replace("%", ""))
            return actual_value < target_uptime
        elif "response_time" in penalty.penalty_id and metric.metric_id.startswith("response_time"):
            target_time = float(penalty.trigger_condition.split(">")[1].strip().replace("ms", ""))
            return actual_value > target_time
        elif "support_response" in penalty.penalty_id and metric.metric_id.startswith("support_response"):
            target_time = float(penalty.trigger_condition.split(">")[1].strip().replace("h", ""))
            return actual_value > target_time
        
        return False
    
    def _calculate_penalty_amount(self, penalty: SLAPenalty, metric: SLAMetric, actual_value: float) -> float:
        """Calculate penalty amount based on breach severity."""
        # Simplified penalty calculation
        if penalty.penalty_unit == "percentage":
            return penalty.penalty_amount
        else:
            return penalty.penalty_amount
    
    def _get_basic_terms(self) -> str:
        """Get terms and conditions for Basic tier."""
        return """
MAMS Basic Service Level Agreement Terms and Conditions

1. SERVICE AVAILABILITY
   - Target uptime: 99.0% per calendar month
   - Planned maintenance windows excluded from uptime calculations
   - Maximum 7.2 hours downtime per month

2. PERFORMANCE STANDARDS
   - API response time: ≤2000ms average
   - Support response: ≤24 hours during business hours

3. SUPPORT COVERAGE
   - Business hours: Monday-Friday, 9 AM - 5 PM local time
   - Email support included
   - Community forum access

4. SERVICE CREDITS
   - 5% monthly fee credit for uptime < 99%
   - Maximum 25% credit per month
   - Credits applied to next billing cycle

5. LIMITATIONS
   - Basic monitoring and alerting
   - Standard backup retention (30 days)
   - Limited customization options

6. TERMINATION
   - Either party may terminate with 30 days notice
   - No penalty for early termination
        """
    
    def _get_professional_terms(self) -> str:
        """Get terms and conditions for Professional tier."""
        return """
MAMS Professional Service Level Agreement Terms and Conditions

1. SERVICE AVAILABILITY
   - Target uptime: 99.5% per calendar month
   - Planned maintenance windows excluded from uptime calculations
   - Maximum 3.6 hours downtime per month

2. PERFORMANCE STANDARDS
   - API response time: ≤1000ms average
   - Support response: ≤8 hours during business hours
   - Data backup success rate: ≥99.9%

3. SUPPORT COVERAGE
   - Extended hours: Monday-Friday, 6 AM - 10 PM local time
   - Email and phone support included
   - Priority support queue
   - Dedicated account manager

4. SERVICE CREDITS
   - 10% monthly fee credit for uptime < 99.5%
   - 5% monthly fee credit for performance breaches
   - Maximum 50% credit per month
   - Credits applied to next billing cycle

5. ENHANCED FEATURES
   - Advanced monitoring and alerting
   - Extended backup retention (90 days)
   - Customization options available
   - Integration support

6. TERMINATION
   - Either party may terminate with 60 days notice
   - Early termination fee may apply
        """
    
    def _get_enterprise_terms(self) -> str:
        """Get terms and conditions for Enterprise tier."""
        return """
MAMS Enterprise Service Level Agreement Terms and Conditions

1. SERVICE AVAILABILITY
   - Target uptime: 99.9% per calendar month
   - Planned maintenance windows excluded from uptime calculations
   - Maximum 43 minutes downtime per month

2. PERFORMANCE STANDARDS
   - API response time: ≤500ms average
   - Support response: ≤2 hours (24/7)
   - Data backup success rate: ≥99.99%
   - Security compliance score: ≥95%

3. SUPPORT COVERAGE
   - 24/7 support coverage
   - Multiple support channels (email, phone, chat, video)
   - Dedicated technical account manager
   - Escalation to engineering team
   - On-site support available

4. SERVICE CREDITS
   - 15% monthly fee credit for uptime < 99.9%
   - 10% monthly fee credit for performance breaches
   - 5% monthly fee credit for support delays
   - Maximum 100% credit per month
   - Credits applied immediately upon request

5. ENTERPRISE FEATURES
   - Real-time monitoring and alerting
   - Long-term backup retention (1 year)
   - Full customization and white-labeling
   - Dedicated infrastructure options
   - Compliance reporting and auditing

6. BUSINESS CONTINUITY
   - Disaster recovery planning included
   - Business continuity consulting
   - Risk assessment and mitigation

7. TERMINATION
   - Either party may terminate with 90 days notice
   - Negotiated early termination terms
        """
    
    def _get_premium_terms(self) -> str:
        """Get terms and conditions for Premium tier."""
        return """
MAMS Premium Service Level Agreement Terms and Conditions

1. SERVICE AVAILABILITY
   - Target uptime: 99.99% per calendar month
   - Planned maintenance windows excluded from uptime calculations
   - Maximum 4.3 minutes downtime per month

2. PERFORMANCE STANDARDS
   - API response time: ≤250ms average
   - Support response: ≤1 hour (24/7/365)
   - Data backup success rate: 100%
   - Security compliance score: ≥98%
   - Disaster recovery RTO: ≤4 hours

3. SUPPORT COVERAGE
   - 24/7/365 premium support
   - Dedicated support team
   - Named technical contacts
   - Direct escalation to C-level
   - Emergency hotline
   - On-site support guaranteed

4. SERVICE CREDITS
   - 25% monthly fee credit for uptime < 99.99%
   - 15% monthly fee credit for performance breaches
   - 10% monthly fee credit for support delays
   - Maximum 100% credit per month
   - Immediate credit processing
   - Additional compensation for severe breaches

5. PREMIUM FEATURES
   - Real-time monitoring with predictive analytics
   - Unlimited backup retention
   - Complete customization and white-labeling
   - Dedicated cloud infrastructure
   - Advanced compliance and security features
   - Custom integrations and development

6. BUSINESS CONTINUITY
   - Comprehensive disaster recovery
   - Business impact analysis
   - Continuous risk monitoring
   - Executive briefings and reporting

7. EXCLUSIVE SERVICES
   - Product roadmap influence
   - Beta feature access
   - Custom feature development
   - Strategic consulting

8. TERMINATION
   - Either party may terminate with 180 days notice
   - Custom termination terms negotiated
   - Transition assistance provided
        """