"""
Onboarding flow API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import List, Optional
from uuid import UUID
import logging

from src.db.base import get_db
from src.db.models import (
    OnboardingFlow, OnboardingStep, UserOnboardingProgress,
    FlowType, UserRole, ProgressStatus
)
from src.models.schemas import (
    OnboardingFlowCreate, OnboardingFlowUpdate, OnboardingFlowResponse,
    StartFlowRequest, UserProgressResponse
)
from src.core.auth import get_current_user
from src.services.flow_service import FlowService
from src.services.analytics_service import AnalyticsService

router = APIRouter()
logger = logging.getLogger(__name__)
flow_service = FlowService()
analytics_service = AnalyticsService()


@router.get("/", response_model=List[OnboardingFlowResponse])
async def list_flows(
    flow_type: Optional[FlowType] = None,
    role: Optional[UserRole] = None,
    is_active: bool = True,
    include_completed: bool = False,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List available onboarding flows for the current user"""
    # Build query
    query = select(OnboardingFlow).where(OnboardingFlow.is_active == is_active)
    
    if flow_type:
        query = query.where(OnboardingFlow.type == flow_type)
    
    if role:
        # Filter flows that target this role
        query = query.where(
            or_(
                OnboardingFlow.target_roles == [],  # Empty means all roles
                OnboardingFlow.target_roles.contains([role.value])
            )
        )
    
    # Filter based on user progress if not including completed
    if not include_completed:
        # Get user's completed flows
        completed_flows = await db.execute(
            select(UserOnboardingProgress.flow_id)
            .where(
                and_(
                    UserOnboardingProgress.user_id == current_user.id,
                    UserOnboardingProgress.status == ProgressStatus.COMPLETED
                )
            )
        )
        completed_flow_ids = [row[0] for row in completed_flows]
        
        if completed_flow_ids:
            query = query.where(OnboardingFlow.id.notin_(completed_flow_ids))
    
    # Order by mandatory first, then by name
    query = query.order_by(
        OnboardingFlow.is_mandatory.desc(),
        OnboardingFlow.name
    )
    
    # Pagination
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    flows = result.scalars().all()
    
    # Load steps for each flow
    for flow in flows:
        steps = await db.execute(
            select(OnboardingStep)
            .where(OnboardingStep.flow_id == flow.id)
            .order_by(OnboardingStep.order)
        )
        flow.steps = steps.scalars().all()
    
    return flows


@router.get("/{flow_id}", response_model=OnboardingFlowResponse)
async def get_flow(
    flow_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a specific flow"""
    flow = await db.get(OnboardingFlow, flow_id)
    
    if not flow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Onboarding flow not found"
        )
    
    # Load steps
    steps = await db.execute(
        select(OnboardingStep)
        .where(OnboardingStep.flow_id == flow.id)
        .order_by(OnboardingStep.order)
    )
    flow.steps = steps.scalars().all()
    
    # Get user's progress on this flow if exists
    progress = await db.execute(
        select(UserOnboardingProgress)
        .where(
            and_(
                UserOnboardingProgress.user_id == current_user.id,
                UserOnboardingProgress.flow_id == flow_id
            )
        )
    )
    user_progress = progress.scalar()
    
    # Add progress info to response
    if user_progress:
        flow.user_progress = user_progress
    
    return flow


@router.post("/{flow_id}/start", response_model=UserProgressResponse)
async def start_flow(
    flow_id: UUID,
    request: StartFlowRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Start an onboarding flow for a user"""
    # Verify flow exists and is active
    flow = await db.get(OnboardingFlow, flow_id)
    if not flow or not flow.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Onboarding flow not found or inactive"
        )
    
    # Check if user already has progress on this flow
    existing_progress = await db.execute(
        select(UserOnboardingProgress)
        .where(
            and_(
                UserOnboardingProgress.user_id == request.user_id,
                UserOnboardingProgress.flow_id == flow_id
            )
        )
    )
    progress = existing_progress.scalar()
    
    if progress:
        if progress.status == ProgressStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Flow already completed"
            )
        # Reset progress if restarting
        progress.status = ProgressStatus.IN_PROGRESS
        progress.started_at = datetime.utcnow()
        progress.current_step_id = None
        progress.completed_steps = 0
    else:
        # Create new progress record
        steps_count = await db.scalar(
            select(func.count())
            .select_from(OnboardingStep)
            .where(OnboardingStep.flow_id == flow_id)
        )
        
        progress = UserOnboardingProgress(
            user_id=request.user_id,
            organization_id=request.organization_id,
            flow_id=flow_id,
            status=ProgressStatus.IN_PROGRESS,
            total_steps=steps_count,
            started_at=datetime.utcnow(),
            last_activity_at=datetime.utcnow()
        )
        db.add(progress)
    
    await db.commit()
    await db.refresh(progress)
    
    # Track analytics
    await analytics_service.track_flow_started(
        user_id=request.user_id,
        flow_id=flow_id,
        organization_id=request.organization_id
    )
    
    # Load flow details
    progress.flow = flow
    
    logger.info(f"User {request.user_id} started flow {flow_id}")
    
    return progress


@router.put("/{flow_id}/complete", response_model=UserProgressResponse)
async def complete_flow(
    flow_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark a flow as completed"""
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
    
    if progress.status == ProgressStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Flow already completed"
        )
    
    # Update progress
    progress.status = ProgressStatus.COMPLETED
    progress.completed_at = datetime.utcnow()
    progress.completion_percentage = 100.0
    progress.is_completed = True
    
    # Calculate total time spent
    if progress.started_at:
        progress.time_spent_minutes = int(
            (progress.completed_at - progress.started_at).total_seconds() / 60
        )
    
    await db.commit()
    await db.refresh(progress)
    
    # Track analytics
    await analytics_service.track_flow_completed(
        user_id=current_user.id,
        flow_id=flow_id,
        time_spent=progress.time_spent_minutes
    )
    
    # Check for achievements
    await flow_service.check_achievements(current_user.id, db)
    
    logger.info(f"User {current_user.id} completed flow {flow_id}")
    
    return progress


@router.post("/", response_model=OnboardingFlowResponse)
async def create_flow(
    flow_data: OnboardingFlowCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new onboarding flow (admin only)"""
    # Check admin permission
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    # Create flow
    flow = OnboardingFlow(**flow_data.dict())
    db.add(flow)
    
    await db.commit()
    await db.refresh(flow)
    
    logger.info(f"Created onboarding flow: {flow.id}")
    
    return flow


@router.put("/{flow_id}", response_model=OnboardingFlowResponse)
async def update_flow(
    flow_id: UUID,
    update_data: OnboardingFlowUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update an onboarding flow (admin only)"""
    # Check admin permission
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    flow = await db.get(OnboardingFlow, flow_id)
    if not flow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Onboarding flow not found"
        )
    
    # Update flow
    for field, value in update_data.dict(exclude_unset=True).items():
        setattr(flow, field, value)
    
    flow.version += 1
    
    await db.commit()
    await db.refresh(flow)
    
    logger.info(f"Updated onboarding flow: {flow_id}")
    
    return flow


@router.delete("/{flow_id}")
async def delete_flow(
    flow_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an onboarding flow (admin only)"""
    # Check admin permission
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    flow = await db.get(OnboardingFlow, flow_id)
    if not flow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Onboarding flow not found"
        )
    
    # Soft delete by deactivating
    flow.is_active = False
    
    await db.commit()
    
    logger.info(f"Deactivated onboarding flow: {flow_id}")
    
    return {"message": "Flow deactivated successfully"}


@router.get("/{flow_id}/prerequisites", response_model=List[OnboardingFlowResponse])
async def get_flow_prerequisites(
    flow_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get prerequisite flows for a specific flow"""
    flow = await db.get(OnboardingFlow, flow_id)
    if not flow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Onboarding flow not found"
        )
    
    if not flow.prerequisites:
        return []
    
    # Get prerequisite flows
    prerequisites = await db.execute(
        select(OnboardingFlow)
        .where(OnboardingFlow.id.in_(flow.prerequisites))
    )
    
    return prerequisites.scalars().all()


from datetime import datetime
from sqlalchemy import func