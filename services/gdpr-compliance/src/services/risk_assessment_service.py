"""Risk Assessment Service for GDPR Compliance"""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload
import uuid

from ..db.models import (
    RiskAssessment, RiskFactor, RiskMitigationPlan, RiskIncident,
    RiskSeverity, RiskStatus, RiskCategory
)
from ..models.schemas import (
    RiskAssessmentCreate, RiskAssessmentUpdate, RiskAssessmentResponse,
    RiskFactorCreate, RiskFactorUpdate, RiskFactorResponse,
    RiskMitigationPlanCreate, RiskMitigationPlanUpdate, RiskMitigationPlanResponse,
    RiskIncidentCreate, RiskIncidentUpdate, RiskIncidentResponse,
    RiskMetricsResponse, RiskDashboardResponse
)
from ..core.exceptions import NotFoundError, ValidationError


class RiskAssessmentService:
    """Service for managing risk assessments"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # Risk Assessment CRUD Operations
    
    async def create_risk_assessment(
        self, 
        assessment_data: RiskAssessmentCreate, 
        created_by: str
    ) -> RiskAssessmentResponse:
        """Create a new risk assessment"""
        try:
            # Calculate risk score and severity
            risk_score = self._calculate_risk_score(
                assessment_data.likelihood_score, 
                assessment_data.impact_score
            )
            severity = self._determine_severity(risk_score)
            
            # Calculate next review date
            next_review_due = datetime.utcnow() + timedelta(days=assessment_data.review_frequency_days)
            
            # Create main assessment
            assessment = RiskAssessment(
                id=uuid.uuid4(),
                title=assessment_data.title,
                description=assessment_data.description,
                risk_category=assessment_data.risk_category,
                risk_source=assessment_data.risk_source,
                affected_assets=assessment_data.affected_assets,
                affected_data_types=assessment_data.affected_data_types,
                potential_impact=assessment_data.potential_impact,
                likelihood_score=assessment_data.likelihood_score,
                impact_score=assessment_data.impact_score,
                risk_score=risk_score,
                severity=severity,
                risk_owner=assessment_data.risk_owner,
                assigned_to=assessment_data.assigned_to,
                mitigation_strategy=assessment_data.mitigation_strategy,
                mitigation_actions=assessment_data.mitigation_actions,
                mitigation_deadline=assessment_data.mitigation_deadline,
                mitigation_cost_estimate=assessment_data.mitigation_cost_estimate,
                next_review_due=next_review_due,
                review_frequency_days=assessment_data.review_frequency_days,
                regulatory_requirements=assessment_data.regulatory_requirements,
                compliance_controls=assessment_data.compliance_controls,
                tags=assessment_data.tags,
                created_by=created_by
            )
            
            self.db.add(assessment)
            await self.db.flush()  # Get the ID
            
            # Create risk factors
            for factor_data in assessment_data.risk_factors:
                factor = RiskFactor(
                    id=uuid.uuid4(),
                    risk_assessment_id=assessment.id,
                    factor_name=factor_data.factor_name,
                    factor_description=factor_data.factor_description,
                    factor_type=factor_data.factor_type,
                    likelihood_contribution=factor_data.likelihood_contribution,
                    impact_contribution=factor_data.impact_contribution,
                    weight=factor_data.weight,
                    evidence=factor_data.evidence,
                    data_sources=factor_data.data_sources,
                    confidence_level=factor_data.confidence_level,
                    created_by=created_by
                )
                self.db.add(factor)
            
            # Create mitigation plans
            for plan_data in assessment_data.mitigation_plans:
                plan = RiskMitigationPlan(
                    id=uuid.uuid4(),
                    risk_assessment_id=assessment.id,
                    plan_name=plan_data.plan_name,
                    plan_description=plan_data.plan_description,
                    mitigation_type=plan_data.mitigation_type,
                    implementation_steps=plan_data.implementation_steps,
                    responsible_party=plan_data.responsible_party,
                    start_date=plan_data.start_date,
                    target_completion_date=plan_data.target_completion_date,
                    expected_risk_reduction=plan_data.expected_risk_reduction,
                    cost=plan_data.cost,
                    effort_hours=plan_data.effort_hours,
                    success_criteria=plan_data.success_criteria,
                    dependencies=plan_data.dependencies,
                    required_resources=plan_data.required_resources,
                    created_by=created_by
                )
                self.db.add(plan)
            
            await self.db.commit()
            await self.db.refresh(assessment)
            
            return await self._get_assessment_with_relations(assessment.id)
            
        except Exception as e:
            await self.db.rollback()
            raise ValidationError(f"Failed to create risk assessment: {str(e)}")
    
    async def get_risk_assessment(self, assessment_id: str) -> RiskAssessmentResponse:
        """Get a risk assessment by ID"""
        return await self._get_assessment_with_relations(assessment_id)
    
    async def update_risk_assessment(
        self, 
        assessment_id: str, 
        update_data: RiskAssessmentUpdate,
        updated_by: str
    ) -> RiskAssessmentResponse:
        """Update a risk assessment"""
        try:
            # Get existing assessment
            result = await self.db.execute(
                select(RiskAssessment).where(RiskAssessment.id == assessment_id)
            )
            assessment = result.scalar_one_or_none()
            
            if not assessment:
                raise NotFoundError(f"Risk assessment {assessment_id} not found")
            
            # Update fields
            update_dict = update_data.dict(exclude_unset=True)
            for field, value in update_dict.items():
                if hasattr(assessment, field):
                    setattr(assessment, field, value)
            
            # Recalculate risk score if likelihood or impact changed
            if update_data.likelihood_score is not None or update_data.impact_score is not None:
                likelihood = update_data.likelihood_score or assessment.likelihood_score
                impact = update_data.impact_score or assessment.impact_score
                assessment.risk_score = self._calculate_risk_score(likelihood, impact)
                assessment.severity = self._determine_severity(assessment.risk_score)
            
            assessment.updated_by = updated_by
            
            await self.db.commit()
            await self.db.refresh(assessment)
            
            return await self._get_assessment_with_relations(assessment.id)
            
        except NotFoundError:
            raise
        except Exception as e:
            await self.db.rollback()
            raise ValidationError(f"Failed to update risk assessment: {str(e)}")
    
    async def delete_risk_assessment(self, assessment_id: str) -> bool:
        """Delete a risk assessment"""
        try:
            result = await self.db.execute(
                select(RiskAssessment).where(RiskAssessment.id == assessment_id)
            )
            assessment = result.scalar_one_or_none()
            
            if not assessment:
                raise NotFoundError(f"Risk assessment {assessment_id} not found")
            
            await self.db.delete(assessment)
            await self.db.commit()
            return True
            
        except NotFoundError:
            raise
        except Exception as e:
            await self.db.rollback()
            raise ValidationError(f"Failed to delete risk assessment: {str(e)}")
    
    async def list_risk_assessments(
        self,
        category: Optional[RiskCategory] = None,
        severity: Optional[RiskSeverity] = None,
        status: Optional[RiskStatus] = None,
        risk_owner: Optional[str] = None,
        assigned_to: Optional[str] = None,
        overdue_reviews: bool = False,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> List[RiskAssessmentResponse]:
        """List risk assessments with filtering and sorting"""
        try:
            query = select(RiskAssessment).options(
                selectinload(RiskAssessment.risk_factors),
                selectinload(RiskAssessment.mitigation_plans)
            )
            
            # Apply filters
            if category:
                query = query.where(RiskAssessment.risk_category == category)
            if severity:
                query = query.where(RiskAssessment.severity == severity)
            if status:
                query = query.where(RiskAssessment.status == status)
            if risk_owner:
                query = query.where(RiskAssessment.risk_owner == risk_owner)
            if assigned_to:
                query = query.where(RiskAssessment.assigned_to == assigned_to)
            if overdue_reviews:
                query = query.where(RiskAssessment.next_review_due < datetime.utcnow())
            
            # Apply sorting
            sort_column = getattr(RiskAssessment, sort_by, RiskAssessment.created_at)
            if sort_order.lower() == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))
            
            # Apply pagination
            query = query.offset(offset).limit(limit)
            
            result = await self.db.execute(query)
            assessments = result.scalars().all()
            
            return [
                RiskAssessmentResponse.from_orm(assessment) 
                for assessment in assessments
            ]
            
        except Exception as e:
            raise ValidationError(f"Failed to list risk assessments: {str(e)}")
    
    # Risk Factor Operations
    
    async def add_risk_factor(
        self, 
        assessment_id: str, 
        factor_data: RiskFactorCreate,
        created_by: str
    ) -> RiskFactorResponse:
        """Add a risk factor to an assessment"""
        try:
            # Verify assessment exists
            result = await self.db.execute(
                select(RiskAssessment).where(RiskAssessment.id == assessment_id)
            )
            assessment = result.scalar_one_or_none()
            
            if not assessment:
                raise NotFoundError(f"Risk assessment {assessment_id} not found")
            
            factor = RiskFactor(
                id=uuid.uuid4(),
                risk_assessment_id=assessment_id,
                factor_name=factor_data.factor_name,
                factor_description=factor_data.factor_description,
                factor_type=factor_data.factor_type,
                likelihood_contribution=factor_data.likelihood_contribution,
                impact_contribution=factor_data.impact_contribution,
                weight=factor_data.weight,
                evidence=factor_data.evidence,
                data_sources=factor_data.data_sources,
                confidence_level=factor_data.confidence_level,
                created_by=created_by
            )
            
            self.db.add(factor)
            await self.db.commit()
            await self.db.refresh(factor)
            
            return RiskFactorResponse.from_orm(factor)
            
        except NotFoundError:
            raise
        except Exception as e:
            await self.db.rollback()
            raise ValidationError(f"Failed to add risk factor: {str(e)}")
    
    # Mitigation Plan Operations
    
    async def add_mitigation_plan(
        self, 
        assessment_id: str, 
        plan_data: RiskMitigationPlanCreate,
        created_by: str
    ) -> RiskMitigationPlanResponse:
        """Add a mitigation plan to an assessment"""
        try:
            # Verify assessment exists
            result = await self.db.execute(
                select(RiskAssessment).where(RiskAssessment.id == assessment_id)
            )
            assessment = result.scalar_one_or_none()
            
            if not assessment:
                raise NotFoundError(f"Risk assessment {assessment_id} not found")
            
            plan = RiskMitigationPlan(
                id=uuid.uuid4(),
                risk_assessment_id=assessment_id,
                plan_name=plan_data.plan_name,
                plan_description=plan_data.plan_description,
                mitigation_type=plan_data.mitigation_type,
                implementation_steps=plan_data.implementation_steps,
                responsible_party=plan_data.responsible_party,
                start_date=plan_data.start_date,
                target_completion_date=plan_data.target_completion_date,
                expected_risk_reduction=plan_data.expected_risk_reduction,
                cost=plan_data.cost,
                effort_hours=plan_data.effort_hours,
                success_criteria=plan_data.success_criteria,
                dependencies=plan_data.dependencies,
                required_resources=plan_data.required_resources,
                created_by=created_by
            )
            
            self.db.add(plan)
            await self.db.commit()
            await self.db.refresh(plan)
            
            return RiskMitigationPlanResponse.from_orm(plan)
            
        except NotFoundError:
            raise
        except Exception as e:
            await self.db.rollback()
            raise ValidationError(f"Failed to add mitigation plan: {str(e)}")
    
    async def update_mitigation_progress(
        self, 
        plan_id: str, 
        progress_percentage: float,
        status: Optional[str] = None,
        actual_completion_date: Optional[datetime] = None
    ) -> RiskMitigationPlanResponse:
        """Update mitigation plan progress"""
        try:
            result = await self.db.execute(
                select(RiskMitigationPlan).where(RiskMitigationPlan.id == plan_id)
            )
            plan = result.scalar_one_or_none()
            
            if not plan:
                raise NotFoundError(f"Mitigation plan {plan_id} not found")
            
            plan.progress_percentage = progress_percentage
            if status:
                plan.status = status
            if actual_completion_date:
                plan.actual_completion_date = actual_completion_date
            
            await self.db.commit()
            await self.db.refresh(plan)
            
            return RiskMitigationPlanResponse.from_orm(plan)
            
        except NotFoundError:
            raise
        except Exception as e:
            await self.db.rollback()
            raise ValidationError(f"Failed to update mitigation progress: {str(e)}")
    
    # Incident Management
    
    async def create_incident(
        self, 
        incident_data: RiskIncidentCreate,
        created_by: str
    ) -> RiskIncidentResponse:
        """Create a new risk incident"""
        try:
            incident = RiskIncident(
                id=uuid.uuid4(),
                incident_title=incident_data.incident_title,
                incident_description=incident_data.incident_description,
                incident_type=incident_data.incident_type,
                related_risk_assessment_id=incident_data.related_risk_assessment_id,
                was_risk_predicted=incident_data.was_risk_predicted,
                actual_impact_description=incident_data.actual_impact_description,
                financial_impact=incident_data.financial_impact,
                affected_records_count=incident_data.affected_records_count,
                affected_individuals_count=incident_data.affected_individuals_count,
                downtime_hours=incident_data.downtime_hours,
                incident_detected_at=incident_data.incident_detected_at,
                incident_occurred_at=incident_data.incident_occurred_at,
                response_team=incident_data.response_team,
                response_actions=incident_data.response_actions,
                regulatory_notification_required=incident_data.regulatory_notification_required,
                severity=incident_data.severity,
                created_by=created_by
            )
            
            self.db.add(incident)
            await self.db.commit()
            await self.db.refresh(incident)
            
            return RiskIncidentResponse.from_orm(incident)
            
        except Exception as e:
            await self.db.rollback()
            raise ValidationError(f"Failed to create incident: {str(e)}")
    
    # Analytics and Metrics
    
    async def get_risk_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> RiskMetricsResponse:
        """Get risk assessment metrics"""
        try:
            # Base query
            base_query = select(RiskAssessment)
            
            # Apply date filters
            if start_date:
                base_query = base_query.where(RiskAssessment.created_at >= start_date)
            if end_date:
                base_query = base_query.where(RiskAssessment.created_at <= end_date)
            
            # Total assessments
            total_result = await self.db.execute(
                select(func.count(RiskAssessment.id)).select_from(base_query.subquery())
            )
            total_assessments = total_result.scalar() or 0
            
            # Assessments by category
            category_result = await self.db.execute(
                select(
                    RiskAssessment.risk_category,
                    func.count(RiskAssessment.id)
                ).select_from(base_query.subquery()).group_by(RiskAssessment.risk_category)
            )
            assessments_by_category = dict(category_result.all())
            
            # Assessments by severity
            severity_result = await self.db.execute(
                select(
                    RiskAssessment.severity,
                    func.count(RiskAssessment.id)
                ).select_from(base_query.subquery()).group_by(RiskAssessment.severity)
            )
            assessments_by_severity = dict(severity_result.all())
            
            # Assessments by status
            status_result = await self.db.execute(
                select(
                    RiskAssessment.status,
                    func.count(RiskAssessment.id)
                ).select_from(base_query.subquery()).group_by(RiskAssessment.status)
            )
            assessments_by_status = dict(status_result.all())
            
            # Average risk score
            avg_score_result = await self.db.execute(
                select(func.avg(RiskAssessment.risk_score)).select_from(base_query.subquery())
            )
            average_risk_score = avg_score_result.scalar() or 0.0
            
            # High and critical risk counts
            high_risk_result = await self.db.execute(
                select(func.count(RiskAssessment.id)).where(
                    and_(
                        RiskAssessment.severity == RiskSeverity.HIGH,
                        base_query.whereclause if hasattr(base_query, 'whereclause') else True
                    )
                )
            )
            high_risk_count = high_risk_result.scalar() or 0
            
            critical_risk_result = await self.db.execute(
                select(func.count(RiskAssessment.id)).where(
                    and_(
                        RiskAssessment.severity == RiskSeverity.CRITICAL,
                        base_query.whereclause if hasattr(base_query, 'whereclause') else True
                    )
                )
            )
            critical_risk_count = critical_risk_result.scalar() or 0
            
            # Overdue reviews
            overdue_result = await self.db.execute(
                select(func.count(RiskAssessment.id)).where(
                    and_(
                        RiskAssessment.next_review_due < datetime.utcnow(),
                        base_query.whereclause if hasattr(base_query, 'whereclause') else True
                    )
                )
            )
            overdue_reviews = overdue_result.scalar() or 0
            
            # Active incidents
            active_incidents_result = await self.db.execute(
                select(func.count(RiskIncident.id)).where(
                    RiskIncident.status.in_(["open", "investigating"])
                )
            )
            active_incidents = active_incidents_result.scalar() or 0
            
            # Mitigation plans metrics
            completed_plans_result = await self.db.execute(
                select(func.count(RiskMitigationPlan.id)).where(
                    RiskMitigationPlan.status == "completed"
                )
            )
            mitigation_plans_completed = completed_plans_result.scalar() or 0
            
            overdue_plans_result = await self.db.execute(
                select(func.count(RiskMitigationPlan.id)).where(
                    and_(
                        RiskMitigationPlan.target_completion_date < datetime.utcnow(),
                        RiskMitigationPlan.status != "completed"
                    )
                )
            )
            mitigation_plans_overdue = overdue_plans_result.scalar() or 0
            
            return RiskMetricsResponse(
                total_assessments=total_assessments,
                assessments_by_category=assessments_by_category,
                assessments_by_severity=assessments_by_severity,
                assessments_by_status=assessments_by_status,
                average_risk_score=float(average_risk_score),
                high_risk_count=high_risk_count,
                critical_risk_count=critical_risk_count,
                overdue_reviews=overdue_reviews,
                active_incidents=active_incidents,
                mitigation_plans_completed=mitigation_plans_completed,
                mitigation_plans_overdue=mitigation_plans_overdue,
                period_start=start_date,
                period_end=end_date
            )
            
        except Exception as e:
            raise ValidationError(f"Failed to get risk metrics: {str(e)}")
    
    async def get_risk_dashboard(self) -> RiskDashboardResponse:
        """Get comprehensive risk dashboard data"""
        try:
            # Get basic metrics
            metrics = await self.get_risk_metrics()
            
            # Get top risks (highest scores)
            top_risks_result = await self.db.execute(
                select(RiskAssessment)
                .options(
                    selectinload(RiskAssessment.risk_factors),
                    selectinload(RiskAssessment.mitigation_plans)
                )
                .order_by(desc(RiskAssessment.risk_score))
                .limit(10)
            )
            top_risks = [
                RiskAssessmentResponse.from_orm(assessment)
                for assessment in top_risks_result.scalars().all()
            ]
            
            # Get recent incidents
            recent_incidents_result = await self.db.execute(
                select(RiskIncident)
                .order_by(desc(RiskIncident.created_at))
                .limit(10)
            )
            recent_incidents = [
                RiskIncidentResponse.from_orm(incident)
                for incident in recent_incidents_result.scalars().all()
            ]
            
            # Risk score distribution
            score_distribution = {
                "0-2": 0, "2-4": 0, "4-6": 0, "6-8": 0, "8-10": 0
            }
            
            # Category breakdown
            category_breakdown = dict(metrics.assessments_by_category)
            
            # Severity trends (simplified)
            severity_trends = {
                "7_days": [],
                "30_days": [],
                "90_days": []
            }
            
            # Mitigation progress
            mitigation_progress = {
                "total_plans": metrics.mitigation_plans_completed + metrics.mitigation_plans_overdue,
                "completed": metrics.mitigation_plans_completed,
                "overdue": metrics.mitigation_plans_overdue,
                "completion_rate": (
                    metrics.mitigation_plans_completed / 
                    max(1, metrics.mitigation_plans_completed + metrics.mitigation_plans_overdue)
                ) * 100
            }
            
            # Compliance gaps (simplified)
            compliance_gaps = []
            
            return RiskDashboardResponse(
                risk_score_distribution=score_distribution,
                category_breakdown=category_breakdown,
                severity_trends=severity_trends,
                top_risks=top_risks,
                recent_incidents=recent_incidents,
                mitigation_progress=mitigation_progress,
                compliance_gaps=compliance_gaps,
                metrics=metrics
            )
            
        except Exception as e:
            raise ValidationError(f"Failed to get risk dashboard: {str(e)}")
    
    # Helper Methods
    
    def _calculate_risk_score(self, likelihood: int, impact: int) -> float:
        """Calculate risk score from likelihood and impact"""
        # Standard risk matrix calculation: likelihood * impact
        # Scale from 1-25 to 0-10 for easier interpretation
        return (likelihood * impact) / 2.5
    
    def _determine_severity(self, risk_score: float) -> RiskSeverity:
        """Determine severity level from risk score"""
        if risk_score >= 8.0:
            return RiskSeverity.CRITICAL
        elif risk_score >= 6.0:
            return RiskSeverity.HIGH
        elif risk_score >= 4.0:
            return RiskSeverity.MEDIUM
        else:
            return RiskSeverity.LOW
    
    async def _get_assessment_with_relations(self, assessment_id: str) -> RiskAssessmentResponse:
        """Get assessment with all related entities"""
        result = await self.db.execute(
            select(RiskAssessment)
            .options(
                selectinload(RiskAssessment.risk_factors),
                selectinload(RiskAssessment.mitigation_plans)
            )
            .where(RiskAssessment.id == assessment_id)
        )
        assessment = result.scalar_one_or_none()
        
        if not assessment:
            raise NotFoundError(f"Risk assessment {assessment_id} not found")
        
        return RiskAssessmentResponse.from_orm(assessment)