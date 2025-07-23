"""
Progress tracking API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta
import logging

from src.db.base import get_db
from src.db.models import (
    UserOnboardingProgress, OnboardingFlow, StepProgress,
    OnboardingStep, UserAchievement, OnboardingGoal,
    ProgressStatus
)
from src.models.schemas import (
    UserProgressResponse, FlowProgressSummary, UserOnboardingSummary,
    UserAchievementResponse
)
from src.core.auth import get_current_user
from src.services.progress_service import ProgressService
from src.services.recommendation_service import RecommendationService

router = APIRouter()
logger = logging.getLogger(__name__)
progress_service = ProgressService()
recommendation_service = RecommendationService()


@router.get("/", response_model=UserOnboardingSummary)
async def get_user_progress(
    user_id: Optional[UUID] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive onboarding progress for a user"""
    # Use provided user_id or current user
    target_user_id = user_id or current_user.id
    
    # If viewing another user's progress, check permissions
    if user_id and user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view other users' progress"
        )
    
    # Get all user progress records
    progress_records = await db.execute(
        select(UserOnboardingProgress)
        .where(UserOnboardingProgress.user_id == target_user_id)
        .options(selectinload(UserOnboardingProgress.flow))
    )
    progress_records = progress_records.scalars().all()
    
    # Calculate summary statistics
    total_flows = len(progress_records)
    completed_flows = sum(1 for p in progress_records if p.status == ProgressStatus.COMPLETED)
    in_progress_flows = sum(1 for p in progress_records if p.status == ProgressStatus.IN_PROGRESS)
    
    # Calculate overall completion
    total_steps = sum(p.total_steps for p in progress_records)
    completed_steps = sum(p.completed_steps for p in progress_records)
    overall_completion = (completed_steps / total_steps * 100) if total_steps > 0 else 0
    
    # Calculate total time spent
    total_time_spent = sum(p.time_spent_minutes for p in progress_records)
    
    # Get achievements
    achievements = await db.execute(
        select(UserAchievement)
        .where(UserAchievement.user_id == target_user_id)
        .options(selectinload(UserAchievement.goal))
    )
    achievements = achievements.scalars().all()
    
    # Get active flows
    active_flows = []
    for progress in progress_records:
        if progress.status == ProgressStatus.IN_PROGRESS:
            # Calculate estimated time remaining
            if progress.completion_percentage > 0:
                avg_time_per_percent = progress.time_spent_minutes / progress.completion_percentage
                estimated_time_remaining = int(
                    avg_time_per_percent * (100 - progress.completion_percentage)
                )
            else:
                estimated_time_remaining = progress.flow.estimated_duration_minutes
            
            active_flows.append(FlowProgressSummary(
                flow_id=progress.flow_id,
                flow_name=progress.flow.name,
                status=progress.status,
                completion_percentage=progress.completion_percentage,
                completed_steps=progress.completed_steps,
                total_steps=progress.total_steps,
                estimated_time_remaining=estimated_time_remaining,
                last_activity=progress.last_activity_at
            ))
    
    # Get recommended tutorials
    recommended_tutorials = await recommendation_service.get_recommended_tutorials(
        user_id=target_user_id,
        limit=5,
        db=db
    )
    
    return UserOnboardingSummary(
        user_id=target_user_id,
        total_flows=total_flows,
        completed_flows=completed_flows,
        in_progress_flows=in_progress_flows,
        overall_completion=overall_completion,
        total_time_spent=total_time_spent,
        achievements=achievements,
        active_flows=active_flows,
        recommended_tutorials=recommended_tutorials
    )


@router.get("/flows/{flow_id}", response_model=UserProgressResponse)
async def get_flow_progress(
    flow_id: UUID,
    user_id: Optional[UUID] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get progress for a specific flow"""
    target_user_id = user_id or current_user.id
    
    # Check permissions
    if user_id and user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view other users' progress"
        )
    
    progress = await db.execute(
        select(UserOnboardingProgress)
        .where(
            and_(
                UserOnboardingProgress.user_id == target_user_id,
                UserOnboardingProgress.flow_id == flow_id
            )
        )
        .options(
            selectinload(UserOnboardingProgress.flow),
            selectinload(UserOnboardingProgress.step_progress)
        )
    )
    progress = progress.scalar()
    
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No progress found for this flow"
        )
    
    return progress


@router.get("/organization/{organization_id}", response_model=List[FlowProgressSummary])
async def get_organization_progress(
    organization_id: UUID,
    flow_id: Optional[UUID] = None,
    status: Optional[ProgressStatus] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get onboarding progress for all users in an organization (admin only)"""
    # Check admin permission
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    # Build query
    query = select(UserOnboardingProgress).where(
        UserOnboardingProgress.organization_id == organization_id
    )
    
    if flow_id:
        query = query.where(UserOnboardingProgress.flow_id == flow_id)
    
    if status:
        query = query.where(UserOnboardingProgress.status == status)
    
    # Get total count
    total = await db.scalar(
        select(func.count()).select_from(query.subquery())
    )
    
    # Pagination
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query.options(selectinload(UserOnboardingProgress.flow)))
    progress_records = result.scalars().all()
    
    # Convert to summaries
    summaries = []
    for progress in progress_records:
        # Calculate estimated time remaining
        if progress.completion_percentage > 0 and progress.status == ProgressStatus.IN_PROGRESS:
            avg_time_per_percent = progress.time_spent_minutes / progress.completion_percentage
            estimated_time_remaining = int(
                avg_time_per_percent * (100 - progress.completion_percentage)
            )
        else:
            estimated_time_remaining = 0
        
        summaries.append(FlowProgressSummary(
            flow_id=progress.flow_id,
            flow_name=progress.flow.name,
            status=progress.status,
            completion_percentage=progress.completion_percentage,
            completed_steps=progress.completed_steps,
            total_steps=progress.total_steps,
            estimated_time_remaining=estimated_time_remaining,
            last_activity=progress.last_activity_at
        ))
    
    return summaries


@router.get("/achievements", response_model=List[UserAchievementResponse])
async def get_user_achievements(
    user_id: Optional[UUID] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's achievements"""
    target_user_id = user_id or current_user.id
    
    # Check permissions
    if user_id and user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view other users' achievements"
        )
    
    achievements = await db.execute(
        select(UserAchievement)
        .where(UserAchievement.user_id == target_user_id)
        .options(selectinload(UserAchievement.goal))
        .order_by(UserAchievement.achieved_at.desc())
    )
    
    return achievements.scalars().all()


@router.get("/stats", response_model=dict)
async def get_progress_statistics(
    user_id: Optional[UUID] = None,
    days: int = Query(30, ge=1, le=365),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed progress statistics"""
    target_user_id = user_id or current_user.id
    
    # Check permissions
    if user_id and user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view other users' statistics"
        )
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Get progress within date range
    progress_records = await db.execute(
        select(UserOnboardingProgress)
        .where(
            and_(
                UserOnboardingProgress.user_id == target_user_id,
                UserOnboardingProgress.created_at >= start_date
            )
        )
    )
    progress_records = progress_records.scalars().all()
    
    # Calculate statistics
    stats = await progress_service.calculate_user_statistics(
        user_id=target_user_id,
        progress_records=progress_records,
        db=db
    )
    
    return stats


@router.post("/reset/{flow_id}")
async def reset_flow_progress(
    flow_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Reset progress for a specific flow"""
    # Get user progress
    progress = await db.execute(
        select(UserOnboardingProgress)
        .where(
            and_(
                UserOnboardingProgress.user_id == current_user.id,
                UserOnboardingProgress.flow_id == flow_id
            )
        )
    )
    progress = progress.scalar()
    
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No progress found for this flow"
        )
    
    # Delete step progress
    await db.execute(
        select(StepProgress)
        .where(StepProgress.user_progress_id == progress.id)
    )
    
    # Reset flow progress
    progress.status = ProgressStatus.NOT_STARTED
    progress.current_step_id = None
    progress.completed_steps = 0
    progress.completion_percentage = 0
    progress.is_completed = False
    progress.started_at = None
    progress.completed_at = None
    progress.time_spent_minutes = 0
    
    await db.commit()
    
    logger.info(f"User {current_user.id} reset progress for flow {flow_id}")
    
    return {"message": "Flow progress reset successfully"}


@router.get("/leaderboard", response_model=List[dict])
async def get_onboarding_leaderboard(
    organization_id: Optional[UUID] = None,
    limit: int = Query(10, ge=1, le=50),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get onboarding leaderboard"""
    # Build leaderboard query
    leaderboard = await progress_service.get_leaderboard(
        organization_id=organization_id,
        limit=limit,
        db=db
    )
    
    return leaderboard


from sqlalchemy.orm import selectinload