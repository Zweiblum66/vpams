"""API endpoints for access review management"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime

from ...core.deps import get_current_user, get_db
from ...core.exceptions import NotFoundError, ValidationError
from ...db.models import User
from ...models.schemas import (
    AccessReviewCreate, AccessReviewUpdate, AccessReviewResponse,
    AccessReviewItemCreate, AccessReviewItemUpdate, AccessReviewItemResponse,
    AccessReviewDecisionCreate, AccessReviewDecisionResponse,
    AccessReviewScheduleCreate, AccessReviewScheduleResponse,
    AccessReviewCampaignCreate, AccessReviewCampaignResponse,
    AccessReviewTemplateCreate, AccessReviewTemplateResponse,
    AccessReviewMetrics, ReviewStatus, ReviewDecision,
    BulkReviewRequest, BulkReviewResponse
)
from ...services.access_review_service import AccessReviewService

logger = logging.getLogger(__name__)
router = APIRouter()


# Access Review Management

@router.post("/reviews", response_model=AccessReviewResponse)
async def create_access_review(
    review_data: AccessReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new access review.
    
    Requires: access_review:create permission
    """
    try:
        if not current_user.has_permission("access_review:create"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to create access reviews"
            )
        
        service = AccessReviewService(db)
        review = await service.create_access_review(review_data, str(current_user.id))
        
        logger.info(
            f"Access review created by user {current_user.id}",
            extra={
                "user_id": str(current_user.id),
                "review_id": str(review.id),
                "review_type": review_data.review_type
            }
        )
        
        return review
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating access review: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create access review"
        )


@router.get("/reviews", response_model=List[AccessReviewResponse])
async def list_access_reviews(
    review_type: Optional[str] = Query(None, description="Filter by review type"),
    status: Optional[ReviewStatus] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    assignee_id: Optional[str] = Query(None, description="Filter by assignee"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List access reviews with optional filtering.
    
    Requires: access_review:view permission
    """
    try:
        if not current_user.has_permission("access_review:view"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = AccessReviewService(db)
        reviews = await service.list_access_reviews(
            review_type=review_type,
            status=status,
            priority=priority,
            assignee_id=assignee_id,
            limit=limit,
            offset=offset
        )
        
        return reviews
        
    except Exception as e:
        logger.error(f"Error listing access reviews: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list access reviews"
        )


@router.get("/reviews/{review_id}", response_model=AccessReviewResponse)
async def get_access_review(
    review_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific access review.
    
    Requires: access_review:view permission
    """
    try:
        if not current_user.has_permission("access_review:view"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = AccessReviewService(db)
        review = await service.get_access_review(str(review_id))
        
        return review
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting access review: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get access review"
        )


@router.patch("/reviews/{review_id}", response_model=AccessReviewResponse)
async def update_access_review(
    review_id: UUID,
    update_data: AccessReviewUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update an access review.
    
    Requires: access_review:update permission
    """
    try:
        if not current_user.has_permission("access_review:update"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = AccessReviewService(db)
        review = await service.update_access_review(str(review_id), update_data)
        
        logger.info(
            f"Access review updated by user {current_user.id}",
            extra={
                "user_id": str(current_user.id),
                "review_id": str(review_id)
            }
        )
        
        return review
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating access review: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update access review"
        )


@router.delete("/reviews/{review_id}")
async def delete_access_review(
    review_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an access review.
    
    Requires: access_review:delete permission
    """
    try:
        if not current_user.has_permission("access_review:delete"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = AccessReviewService(db)
        await service.delete_access_review(str(review_id))
        
        logger.info(
            f"Access review deleted by user {current_user.id}",
            extra={
                "user_id": str(current_user.id),
                "review_id": str(review_id)
            }
        )
        
        return {"message": "Access review deleted successfully"}
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting access review: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete access review"
        )


# Review Items Management

@router.post("/reviews/{review_id}/items", response_model=AccessReviewItemResponse)
async def add_review_item(
    review_id: UUID,
    item_data: AccessReviewItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add an item to an access review.
    
    Requires: access_review:update permission
    """
    try:
        if not current_user.has_permission("access_review:update"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = AccessReviewService(db)
        item = await service.add_review_item(
            str(review_id),
            item_data,
            str(current_user.id)
        )
        
        return item
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error adding review item: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add review item"
        )


@router.patch("/items/{item_id}", response_model=AccessReviewItemResponse)
async def update_review_item(
    item_id: UUID,
    update_data: AccessReviewItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a review item.
    
    Requires: access_review:update permission
    """
    try:
        if not current_user.has_permission("access_review:update"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = AccessReviewService(db)
        item = await service.update_review_item(str(item_id), update_data)
        
        return item
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating review item: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update review item"
        )


# Review Decisions

@router.post("/items/{item_id}/decisions", response_model=AccessReviewDecisionResponse)
async def record_review_decision(
    item_id: UUID,
    decision_data: AccessReviewDecisionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Record a review decision for an item.
    
    Requires: access_review:review permission
    """
    try:
        if not current_user.has_permission("access_review:review"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to make review decisions"
            )
        
        service = AccessReviewService(db)
        decision = await service.record_decision(
            str(item_id),
            decision_data,
            str(current_user.id)
        )
        
        return decision
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error recording decision: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record decision"
        )


# Bulk Operations

@router.post("/reviews/{review_id}/bulk-approve", response_model=BulkReviewResponse)
async def bulk_approve_items(
    review_id: UUID,
    bulk_request: BulkReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Bulk approve review items.
    
    Requires: access_review:review permission
    """
    try:
        if not current_user.has_permission("access_review:review"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = AccessReviewService(db)
        decisions = await service.bulk_approve_items(
            str(review_id),
            bulk_request.item_ids,
            str(current_user.id),
            bulk_request.justification
        )
        
        return BulkReviewResponse(
            processed_items=len(bulk_request.item_ids),
            successful_items=len(decisions),
            failed_items=len(bulk_request.item_ids) - len(decisions),
            decisions=decisions
        )
        
    except Exception as e:
        logger.error(f"Error bulk approving items: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to bulk approve items"
        )


@router.post("/reviews/{review_id}/bulk-revoke", response_model=BulkReviewResponse)
async def bulk_revoke_items(
    review_id: UUID,
    bulk_request: BulkReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Bulk revoke access for review items.
    
    Requires: access_review:review permission
    """
    try:
        if not current_user.has_permission("access_review:review"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = AccessReviewService(db)
        decisions = await service.bulk_revoke_items(
            str(review_id),
            bulk_request.item_ids,
            str(current_user.id),
            bulk_request.justification
        )
        
        return BulkReviewResponse(
            processed_items=len(bulk_request.item_ids),
            successful_items=len(decisions),
            failed_items=len(bulk_request.item_ids) - len(decisions),
            decisions=decisions
        )
        
    except Exception as e:
        logger.error(f"Error bulk revoking items: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to bulk revoke items"
        )


# Review Templates

@router.get("/templates", response_model=List[AccessReviewTemplateResponse])
async def list_review_templates(
    review_type: Optional[str] = Query(None, description="Filter by review type"),
    is_default: Optional[bool] = Query(None, description="Filter by default status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List available access review templates.
    
    Requires: access_review:view permission
    """
    try:
        if not current_user.has_permission("access_review:view"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = AccessReviewService(db)
        templates = await service.list_review_templates(
            review_type=review_type,
            is_default=is_default
        )
        
        return templates
        
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list templates"
        )


@router.post("/templates", response_model=AccessReviewTemplateResponse)
async def create_review_template(
    template_data: AccessReviewTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new access review template.
    
    Requires: access_review:admin permission
    """
    try:
        if not current_user.has_permission("access_review:admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permissions required"
            )
        
        service = AccessReviewService(db)
        template = await service.create_review_template(
            template_data,
            str(current_user.id)
        )
        
        return template
        
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create template"
        )


# Review Schedules

@router.post("/schedules", response_model=AccessReviewScheduleResponse)
async def create_review_schedule(
    schedule_data: AccessReviewScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a scheduled access review.
    
    Requires: access_review:schedule permission
    """
    try:
        if not current_user.has_permission("access_review:schedule"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = AccessReviewService(db)
        schedule = await service.create_review_schedule(
            schedule_data,
            str(current_user.id)
        )
        
        return schedule
        
    except Exception as e:
        logger.error(f"Error creating schedule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create schedule"
        )


# Review Campaigns

@router.post("/campaigns", response_model=AccessReviewCampaignResponse)
async def create_review_campaign(
    campaign_data: AccessReviewCampaignCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create an access review campaign.
    
    Requires: access_review:admin permission
    """
    try:
        if not current_user.has_permission("access_review:admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permissions required"
            )
        
        service = AccessReviewService(db)
        campaign = await service.create_review_campaign(
            campaign_data,
            str(current_user.id)
        )
        
        return campaign
        
    except Exception as e:
        logger.error(f"Error creating campaign: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create campaign"
        )


# Analytics and Metrics

@router.get("/metrics", response_model=AccessReviewMetrics)
async def get_review_metrics(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get access review metrics.
    
    Requires: access_review:view permission
    """
    try:
        if not current_user.has_permission("access_review:view"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        service = AccessReviewService(db)
        metrics = await service.get_review_metrics(start_date, end_date)
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get metrics"
        )


# Initialize default templates

@router.post("/templates/defaults")
async def create_default_templates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create default access review templates.
    
    Requires: access_review:admin permission
    """
    try:
        if not current_user.has_permission("access_review:admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permissions required"
            )
        
        service = AccessReviewService(db)
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