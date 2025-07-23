"""Feedback API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from typing import List, Optional
from datetime import datetime

from ..core.database import get_db
from ..core.auth import get_current_user, require_admin
from ..models import Feedback, BetaUser, FeatureFlag, FeedbackCategory, FeedbackStatus
from ..schemas.feedback import (
    FeedbackCreate,
    FeedbackUpdate,
    FeedbackResponse,
    FeedbackListResponse,
    FeedbackVoteRequest
)
from ..services.email_service import send_feedback_notification
from ..core.config import get_settings

router = APIRouter(prefix="/beta/feedback", tags=["Feedback"])


@router.post("", response_model=FeedbackResponse)
async def submit_feedback(
    feedback: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Submit beta feedback"""
    # Get beta user
    result = await db.execute(
        select(BetaUser).where(BetaUser.user_id == current_user["user_id"])
    )
    beta_user = result.scalar_one_or_none()
    
    if not beta_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only beta users can submit feedback"
        )
    
    # Create feedback
    new_feedback = Feedback(
        beta_user_id=beta_user.id,
        **feedback.dict()
    )
    
    # Set priority based on severity for bug reports
    if feedback.category == FeedbackCategory.BUG_REPORT:
        if feedback.severity == "critical":
            new_feedback.priority = 1
        elif feedback.severity == "high":
            new_feedback.priority = 2
        elif feedback.severity == "medium":
            new_feedback.priority = 3
        else:
            new_feedback.priority = 4
    
    db.add(new_feedback)
    
    # Update user feedback count
    if feedback.category == FeedbackCategory.BUG_REPORT:
        beta_user.bug_reports_count += 1
    elif feedback.category == FeedbackCategory.FEATURE_REQUEST:
        beta_user.feature_requests_count += 1
    beta_user.feedback_count += 1
    
    await db.commit()
    await db.refresh(new_feedback)
    
    # Send notification to team
    settings = get_settings()
    if settings.feedback_notification_email:
        await send_feedback_notification(
            settings.feedback_notification_email,
            new_feedback,
            beta_user
        )
    
    return FeedbackResponse.from_orm(new_feedback)


@router.get("", response_model=FeedbackListResponse)
async def list_feedback(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[FeedbackCategory] = None,
    status: Optional[FeedbackStatus] = None,
    severity: Optional[str] = None,
    user_id: Optional[str] = None,
    feature_id: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List feedback"""
    # Build base query
    query = select(Feedback).join(BetaUser)
    
    # Non-admins can only see their own feedback
    if not current_user.get("is_admin"):
        query = query.where(BetaUser.user_id == current_user["user_id"])
    
    # Apply filters
    if category:
        query = query.where(Feedback.category == category)
    
    if status:
        query = query.where(Feedback.status == status)
    
    if severity:
        query = query.where(Feedback.severity == severity)
    
    if user_id and current_user.get("is_admin"):
        query = query.where(BetaUser.user_id == user_id)
    
    if feature_id:
        query = query.where(Feedback.feature_id == feature_id)
    
    if search:
        query = query.where(
            or_(
                Feedback.title.ilike(f"%{search}%"),
                Feedback.description.ilike(f"%{search}%")
            )
        )
    
    # Get total count
    count_query = select(func.count()).select_from(Feedback).join(BetaUser)
    if not current_user.get("is_admin"):
        count_query = count_query.where(BetaUser.user_id == current_user["user_id"])
    if category or status or severity or user_id or feature_id or search:
        count_query = query.with_only_columns([func.count()])
    total = await db.scalar(count_query)
    
    # Apply pagination
    query = query.offset((page - 1) * limit).limit(limit)
    query = query.order_by(Feedback.created_at.desc())
    
    # Execute query
    result = await db.execute(query)
    feedback_items = result.scalars().all()
    
    return FeedbackListResponse(
        feedback=[FeedbackResponse.from_orm(item) for item in feedback_items],
        total=total,
        page=page,
        limit=limit,
        pages=(total + limit - 1) // limit
    )


@router.get("/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback(
    feedback_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get feedback details"""
    # Get feedback with user
    result = await db.execute(
        select(Feedback).join(BetaUser).where(Feedback.id == feedback_id)
    )
    feedback = result.scalar_one_or_none()
    
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )
    
    # Check permission
    beta_user = feedback.beta_user
    if not current_user.get("is_admin") and beta_user.user_id != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only view own feedback"
        )
    
    return FeedbackResponse.from_orm(feedback)


@router.put("/{feedback_id}", response_model=FeedbackResponse)
async def update_feedback(
    feedback_id: str,
    update: FeedbackUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update feedback"""
    # Get feedback
    result = await db.execute(
        select(Feedback).join(BetaUser).where(Feedback.id == feedback_id)
    )
    feedback = result.scalar_one_or_none()
    
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )
    
    # Check permission
    beta_user = feedback.beta_user
    is_owner = beta_user.user_id == current_user["user_id"]
    is_admin = current_user.get("is_admin", False)
    
    if not is_admin and not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only update own feedback"
        )
    
    # Update feedback
    update_data = update.dict(exclude_unset=True)
    
    # Restrict fields for non-admins
    if not is_admin:
        admin_only_fields = [
            "status", "priority", "assigned_to", "resolution",
            "resolved_at", "resolved_by", "github_issue_url",
            "jira_ticket_id", "internal_notes", "tags"
        ]
        for field in admin_only_fields:
            update_data.pop(field, None)
    
    # Handle status changes
    if "status" in update_data and is_admin:
        old_status = feedback.status
        new_status = update_data["status"]
        
        if new_status == FeedbackStatus.RESOLVED and old_status != FeedbackStatus.RESOLVED:
            feedback.resolved_at = datetime.utcnow()
            feedback.resolved_by = current_user["email"]
    
    for field, value in update_data.items():
        setattr(feedback, field, value)
    
    feedback.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(feedback)
    
    return FeedbackResponse.from_orm(feedback)


@router.post("/{feedback_id}/vote")
async def vote_on_feedback(
    feedback_id: str,
    vote: FeedbackVoteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Vote on feedback"""
    # Get beta user
    result = await db.execute(
        select(BetaUser).where(BetaUser.user_id == current_user["user_id"])
    )
    beta_user = result.scalar_one_or_none()
    
    if not beta_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only beta users can vote on feedback"
        )
    
    # Get feedback
    result = await db.execute(
        select(Feedback).where(Feedback.id == feedback_id)
    )
    feedback = result.scalar_one_or_none()
    
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )
    
    # Update vote counts
    if vote.vote_type == "upvote":
        feedback.upvotes += 1
    elif vote.vote_type == "downvote":
        feedback.downvotes += 1
    
    await db.commit()
    
    return {
        "message": "Vote recorded",
        "feedback_id": str(feedback.id),
        "upvotes": feedback.upvotes,
        "downvotes": feedback.downvotes
    }