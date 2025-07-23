"""Access Review Service for governance and compliance"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from uuid import UUID, uuid4

from ..db.models import (
    AccessReview, AccessReviewItem, AccessReviewSchedule, AccessReviewTemplate,
    AccessReviewCampaign, AccessReviewResponse, AccessReviewDecision,
    User
)
from ..models.schemas import (
    AccessReviewCreate, AccessReviewUpdate, AccessReviewResponse as AccessReviewResponseSchema,
    AccessReviewItemCreate, AccessReviewItemUpdate, AccessReviewItemResponse,
    AccessReviewScheduleCreate, AccessReviewScheduleResponse,
    AccessReviewCampaignCreate, AccessReviewCampaignResponse,
    AccessReviewTemplateCreate, AccessReviewTemplateResponse,
    AccessReviewDecisionCreate, AccessReviewDecisionResponse,
    AccessReviewMetrics, ReviewScheduleFrequency, ReviewStatus, ReviewDecision
)
from ..core.exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)


class AccessReviewService:
    """Service for managing access reviews and governance"""
    
    def __init__(self, db: AsyncSession):
        self.db = db

    # Access Review Management
    
    async def create_access_review(
        self,
        review_data: AccessReviewCreate,
        created_by: str
    ) -> AccessReviewResponseSchema:
        """Create a new access review"""
        try:
            # Calculate review period
            now = datetime.utcnow()
            review_end = now + timedelta(days=review_data.review_period_days)
            
            review = AccessReview(
                id=uuid4(),
                title=review_data.title,
                description=review_data.description,
                review_type=review_data.review_type,
                target_type=review_data.target_type,
                target_criteria=review_data.target_criteria,
                scope=review_data.scope,
                priority=review_data.priority,
                status=ReviewStatus.DRAFT,
                review_start_date=review_data.review_start_date or now,
                review_end_date=review_data.review_end_date or review_end,
                auto_approve_threshold=review_data.auto_approve_threshold,
                require_justification=review_data.require_justification,
                allow_bulk_decisions=review_data.allow_bulk_decisions,
                metadata=review_data.metadata,
                created_by=created_by
            )
            
            self.db.add(review)
            await self.db.commit()
            await self.db.refresh(review)
            
            logger.info(
                f"Access review created: {review.id}",
                extra={
                    "review_id": str(review.id),
                    "created_by": created_by,
                    "review_type": review_data.review_type
                }
            )
            
            return await self._format_review_response(review)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating access review: {e}")
            raise ValidationError(f"Failed to create access review: {str(e)}")

    async def get_access_review(self, review_id: str) -> AccessReviewResponseSchema:
        """Get access review by ID"""
        stmt = (
            select(AccessReview)
            .options(selectinload(AccessReview.items))
            .where(AccessReview.id == UUID(review_id))
        )
        result = await self.db.execute(stmt)
        review = result.scalar_one_or_none()
        
        if not review:
            raise NotFoundError(f"Access review not found: {review_id}")
        
        return await self._format_review_response(review)

    async def update_access_review(
        self,
        review_id: str,
        update_data: AccessReviewUpdate
    ) -> AccessReviewResponseSchema:
        """Update access review"""
        stmt = select(AccessReview).where(AccessReview.id == UUID(review_id))
        result = await self.db.execute(stmt)
        review = result.scalar_one_or_none()
        
        if not review:
            raise NotFoundError(f"Access review not found: {review_id}")
        
        # Update fields
        update_dict = update_data.dict(exclude_unset=True)
        for field, value in update_dict.items():
            if hasattr(review, field):
                setattr(review, field, value)
        
        review.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(review)
        
        return await self._format_review_response(review)

    async def delete_access_review(self, review_id: str) -> None:
        """Delete access review"""
        stmt = select(AccessReview).where(AccessReview.id == UUID(review_id))
        result = await self.db.execute(stmt)
        review = result.scalar_one_or_none()
        
        if not review:
            raise NotFoundError(f"Access review not found: {review_id}")
        
        await self.db.delete(review)
        await self.db.commit()

    async def list_access_reviews(
        self,
        review_type: Optional[str] = None,
        status: Optional[ReviewStatus] = None,
        priority: Optional[str] = None,
        assignee_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AccessReviewResponseSchema]:
        """List access reviews with filtering"""
        stmt = select(AccessReview)
        
        # Apply filters
        if review_type:
            stmt = stmt.where(AccessReview.review_type == review_type)
        if status:
            stmt = stmt.where(AccessReview.status == status)
        if priority:
            stmt = stmt.where(AccessReview.priority == priority)
        if assignee_id:
            stmt = stmt.where(AccessReview.assigned_to == assignee_id)
        
        stmt = stmt.offset(offset).limit(limit).order_by(AccessReview.created_at.desc())
        result = await self.db.execute(stmt)
        reviews = result.scalars().all()
        
        return [await self._format_review_response(review) for review in reviews]

    # Access Review Items
    
    async def add_review_item(
        self,
        review_id: str,
        item_data: AccessReviewItemCreate,
        created_by: str
    ) -> AccessReviewItemResponse:
        """Add item to access review"""
        # Verify review exists
        await self.get_access_review(review_id)
        
        item = AccessReviewItem(
            id=uuid4(),
            review_id=UUID(review_id),
            subject_type=item_data.subject_type,
            subject_id=item_data.subject_id,
            resource_type=item_data.resource_type,
            resource_id=item_data.resource_id,
            permission_type=item_data.permission_type,
            current_access_level=item_data.current_access_level,
            access_granted_date=item_data.access_granted_date,
            last_used_date=item_data.last_used_date,
            business_justification=item_data.business_justification,
            assigned_to=item_data.assigned_to,
            metadata=item_data.metadata,
            created_by=created_by
        )
        
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        
        return AccessReviewItemResponse.from_orm(item)

    async def update_review_item(
        self,
        item_id: str,
        update_data: AccessReviewItemUpdate
    ) -> AccessReviewItemResponse:
        """Update review item"""
        stmt = select(AccessReviewItem).where(AccessReviewItem.id == UUID(item_id))
        result = await self.db.execute(stmt)
        item = result.scalar_one_or_none()
        
        if not item:
            raise NotFoundError(f"Review item not found: {item_id}")
        
        # Update fields
        update_dict = update_data.dict(exclude_unset=True)
        for field, value in update_dict.items():
            if hasattr(item, field):
                setattr(item, field, value)
        
        item.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(item)
        
        return AccessReviewItemResponse.from_orm(item)

    # Review Decisions
    
    async def record_decision(
        self,
        item_id: str,
        decision_data: AccessReviewDecisionCreate,
        reviewer_id: str
    ) -> AccessReviewDecisionResponse:
        """Record a review decision"""
        # Verify item exists
        stmt = select(AccessReviewItem).where(AccessReviewItem.id == UUID(item_id))
        result = await self.db.execute(stmt)
        item = result.scalar_one_or_none()
        
        if not item:
            raise NotFoundError(f"Review item not found: {item_id}")
        
        decision = AccessReviewDecision(
            id=uuid4(),
            item_id=UUID(item_id),
            reviewer_id=reviewer_id,
            decision=decision_data.decision,
            justification=decision_data.justification,
            recommended_action=decision_data.recommended_action,
            new_access_level=decision_data.new_access_level,
            review_date=datetime.utcnow(),
            expiry_date=decision_data.expiry_date,
            comments=decision_data.comments,
            metadata=decision_data.metadata
        )
        
        # Update item status
        item.status = decision_data.decision.value if hasattr(decision_data.decision, 'value') else decision_data.decision
        item.reviewed_at = datetime.utcnow()
        item.reviewed_by = reviewer_id
        
        self.db.add(decision)
        await self.db.commit()
        await self.db.refresh(decision)
        
        logger.info(
            f"Review decision recorded: {decision.id}",
            extra={
                "item_id": item_id,
                "reviewer_id": reviewer_id,
                "decision": decision_data.decision
            }
        )
        
        return AccessReviewDecisionResponse.from_orm(decision)

    # Review Campaigns
    
    async def create_review_campaign(
        self,
        campaign_data: AccessReviewCampaignCreate,
        created_by: str
    ) -> AccessReviewCampaignResponse:
        """Create access review campaign"""
        campaign = AccessReviewCampaign(
            id=uuid4(),
            name=campaign_data.name,
            description=campaign_data.description,
            review_type=campaign_data.review_type,
            target_criteria=campaign_data.target_criteria,
            start_date=campaign_data.start_date,
            end_date=campaign_data.end_date,
            auto_generate_reviews=campaign_data.auto_generate_reviews,
            notification_settings=campaign_data.notification_settings,
            template_id=campaign_data.template_id,
            created_by=created_by
        )
        
        self.db.add(campaign)
        await self.db.commit()
        await self.db.refresh(campaign)
        
        return AccessReviewCampaignResponse.from_orm(campaign)

    # Review Schedules
    
    async def create_review_schedule(
        self,
        schedule_data: AccessReviewScheduleCreate,
        created_by: str
    ) -> AccessReviewScheduleResponse:
        """Create scheduled access review"""
        schedule = AccessReviewSchedule(
            id=uuid4(),
            name=schedule_data.name,
            description=schedule_data.description,
            review_type=schedule_data.review_type,
            frequency=schedule_data.frequency,
            cron_expression=schedule_data.cron_expression,
            target_criteria=schedule_data.target_criteria,
            auto_start=schedule_data.auto_start,
            review_duration_days=schedule_data.review_duration_days,
            template_id=schedule_data.template_id,
            next_run_date=schedule_data.next_run_date,
            notification_settings=schedule_data.notification_settings,
            is_active=schedule_data.is_active,
            created_by=created_by
        )
        
        self.db.add(schedule)
        await self.db.commit()
        await self.db.refresh(schedule)
        
        return AccessReviewScheduleResponse.from_orm(schedule)

    # Review Templates
    
    async def create_review_template(
        self,
        template_data: AccessReviewTemplateCreate,
        created_by: str
    ) -> AccessReviewTemplateResponse:
        """Create access review template"""
        template = AccessReviewTemplate(
            id=uuid4(),
            name=template_data.name,
            description=template_data.description,
            review_type=template_data.review_type,
            default_settings=template_data.default_settings,
            question_template=template_data.question_template,
            approval_workflow=template_data.approval_workflow,
            notification_template=template_data.notification_template,
            is_default=template_data.is_default,
            tags=template_data.tags,
            created_by=created_by
        )
        
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        
        return AccessReviewTemplateResponse.from_orm(template)

    async def list_review_templates(
        self,
        review_type: Optional[str] = None,
        is_default: Optional[bool] = None
    ) -> List[AccessReviewTemplateResponse]:
        """List review templates"""
        stmt = select(AccessReviewTemplate)
        
        if review_type:
            stmt = stmt.where(AccessReviewTemplate.review_type == review_type)
        if is_default is not None:
            stmt = stmt.where(AccessReviewTemplate.is_default == is_default)
        
        stmt = stmt.order_by(AccessReviewTemplate.name)
        result = await self.db.execute(stmt)
        templates = result.scalars().all()
        
        return [AccessReviewTemplateResponse.from_orm(template) for template in templates]

    # Bulk Operations
    
    async def bulk_approve_items(
        self,
        review_id: str,
        item_ids: List[str],
        reviewer_id: str,
        justification: str
    ) -> List[AccessReviewDecisionResponse]:
        """Bulk approve review items"""
        decisions = []
        
        for item_id in item_ids:
            decision_data = AccessReviewDecisionCreate(
                decision=ReviewDecision.APPROVED,
                justification=justification,
                recommended_action="maintain_access"
            )
            
            decision = await self.record_decision(item_id, decision_data, reviewer_id)
            decisions.append(decision)
        
        return decisions

    async def bulk_revoke_items(
        self,
        review_id: str,
        item_ids: List[str],
        reviewer_id: str,
        justification: str
    ) -> List[AccessReviewDecisionResponse]:
        """Bulk revoke access for review items"""
        decisions = []
        
        for item_id in item_ids:
            decision_data = AccessReviewDecisionCreate(
                decision=ReviewDecision.REVOKED,
                justification=justification,
                recommended_action="revoke_access"
            )
            
            decision = await self.record_decision(item_id, decision_data, reviewer_id)
            decisions.append(decision)
        
        return decisions

    # Analytics and Metrics
    
    async def get_review_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> AccessReviewMetrics:
        """Get access review metrics"""
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Total reviews
        total_reviews_stmt = (
            select(func.count(AccessReview.id))
            .where(
                and_(
                    AccessReview.created_at >= start_date,
                    AccessReview.created_at <= end_date
                )
            )
        )
        total_reviews_result = await self.db.execute(total_reviews_stmt)
        total_reviews = total_reviews_result.scalar() or 0
        
        # Active reviews
        active_reviews_stmt = (
            select(func.count(AccessReview.id))
            .where(AccessReview.status == ReviewStatus.IN_PROGRESS)
        )
        active_reviews_result = await self.db.execute(active_reviews_stmt)
        active_reviews = active_reviews_result.scalar() or 0
        
        # Completed reviews
        completed_reviews_stmt = (
            select(func.count(AccessReview.id))
            .where(AccessReview.status == ReviewStatus.COMPLETED)
        )
        completed_reviews_result = await self.db.execute(completed_reviews_stmt)
        completed_reviews = completed_reviews_result.scalar() or 0
        
        # Overdue reviews
        overdue_reviews_stmt = (
            select(func.count(AccessReview.id))
            .where(
                and_(
                    AccessReview.status.in_([ReviewStatus.IN_PROGRESS, ReviewStatus.PENDING]),
                    AccessReview.review_end_date < datetime.utcnow()
                )
            )
        )
        overdue_reviews_result = await self.db.execute(overdue_reviews_stmt)
        overdue_reviews = overdue_reviews_result.scalar() or 0
        
        # Items by decision
        decisions_stmt = (
            select(
                AccessReviewDecision.decision,
                func.count(AccessReviewDecision.id)
            )
            .where(
                and_(
                    AccessReviewDecision.review_date >= start_date,
                    AccessReviewDecision.review_date <= end_date
                )
            )
            .group_by(AccessReviewDecision.decision)
        )
        decisions_result = await self.db.execute(decisions_stmt)
        decisions_by_type = dict(decisions_result.all())
        
        # Average completion time
        completion_time_stmt = (
            select(
                func.avg(
                    func.extract('epoch', AccessReview.completed_at - AccessReview.created_at) / 86400
                )
            )
            .where(
                and_(
                    AccessReview.status == ReviewStatus.COMPLETED,
                    AccessReview.completed_at.isnot(None)
                )
            )
        )
        completion_time_result = await self.db.execute(completion_time_stmt)
        avg_completion_days = completion_time_result.scalar() or 0
        
        return AccessReviewMetrics(
            total_reviews=total_reviews,
            active_reviews=active_reviews,
            completed_reviews=completed_reviews,
            overdue_reviews=overdue_reviews,
            average_completion_days=float(avg_completion_days),
            decisions_by_type=decisions_by_type,
            period_start=start_date,
            period_end=end_date
        )

    # Helper Methods
    
    async def _format_review_response(self, review: AccessReview) -> AccessReviewResponseSchema:
        """Format access review for response"""
        # Get item counts
        total_items_stmt = (
            select(func.count(AccessReviewItem.id))
            .where(AccessReviewItem.review_id == review.id)
        )
        total_items_result = await self.db.execute(total_items_stmt)
        total_items = total_items_result.scalar() or 0
        
        reviewed_items_stmt = (
            select(func.count(AccessReviewItem.id))
            .where(
                and_(
                    AccessReviewItem.review_id == review.id,
                    AccessReviewItem.status != "pending"
                )
            )
        )
        reviewed_items_result = await self.db.execute(reviewed_items_stmt)
        reviewed_items = reviewed_items_result.scalar() or 0
        
        # Calculate progress
        progress_percentage = (reviewed_items / total_items * 100) if total_items > 0 else 0
        
        return AccessReviewResponseSchema(
            id=review.id,
            title=review.title,
            description=review.description,
            review_type=review.review_type,
            target_type=review.target_type,
            target_criteria=review.target_criteria,
            scope=review.scope,
            priority=review.priority,
            status=review.status,
            review_start_date=review.review_start_date,
            review_end_date=review.review_end_date,
            completed_at=review.completed_at,
            assigned_to=review.assigned_to,
            auto_approve_threshold=review.auto_approve_threshold,
            require_justification=review.require_justification,
            allow_bulk_decisions=review.allow_bulk_decisions,
            total_items=total_items,
            reviewed_items=reviewed_items,
            progress_percentage=progress_percentage,
            metadata=review.metadata,
            created_at=review.created_at,
            updated_at=review.updated_at,
            created_by=review.created_by
        )

    async def create_default_templates(self, created_by: str) -> List[AccessReviewTemplateResponse]:
        """Create default access review templates"""
        templates = [
            AccessReviewTemplateCreate(
                name="User Access Review",
                description="Standard user access review template",
                review_type="user_access",
                default_settings={
                    "review_period_days": 30,
                    "require_justification": True,
                    "allow_bulk_decisions": True,
                    "auto_approve_threshold": 0.8
                },
                question_template={
                    "questions": [
                        "Does this user still require access to this resource?",
                        "Is the current access level appropriate?",
                        "When was this access last used?"
                    ]
                },
                approval_workflow={
                    "steps": [
                        {"role": "manager", "required": True},
                        {"role": "security_admin", "required": False}
                    ]
                },
                is_default=True,
                tags=["user", "access", "standard"]
            ),
            AccessReviewTemplateCreate(
                name="Privileged Access Review",
                description="Review template for privileged access",
                review_type="privileged_access",
                default_settings={
                    "review_period_days": 14,
                    "require_justification": True,
                    "allow_bulk_decisions": False,
                    "auto_approve_threshold": 0.9
                },
                question_template={
                    "questions": [
                        "Is this privileged access still required?",
                        "Has the business justification changed?",
                        "Are there alternative lower-privilege solutions?"
                    ]
                },
                approval_workflow={
                    "steps": [
                        {"role": "security_admin", "required": True},
                        {"role": "compliance_officer", "required": True}
                    ]
                },
                is_default=True,
                tags=["privileged", "admin", "security"]
            ),
            AccessReviewTemplateCreate(
                name="Application Access Review",
                description="Review template for application access",
                review_type="application_access",
                default_settings={
                    "review_period_days": 21,
                    "require_justification": True,
                    "allow_bulk_decisions": True,
                    "auto_approve_threshold": 0.75
                },
                question_template={
                    "questions": [
                        "Does this user still need access to this application?",
                        "Is the access level appropriate for their role?",
                        "Are there any compliance concerns?"
                    ]
                },
                approval_workflow={
                    "steps": [
                        {"role": "app_owner", "required": True},
                        {"role": "manager", "required": False}
                    ]
                },
                is_default=True,
                tags=["application", "role-based", "compliance"]
            )
        ]
        
        created_templates = []
        for template_data in templates:
            template = await self.create_review_template(template_data, created_by)
            created_templates.append(template)
        
        return created_templates