"""
Onboarding steps API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from uuid import UUID
from datetime import datetime
import logging

from src.db.base import get_db
from src.db.models import (
    OnboardingStep, UserOnboardingProgress, StepProgress,
    ProgressStatus
)
from src.models.schemas import (
    OnboardingStepCreate, OnboardingStepUpdate, OnboardingStepResponse,
    StepProgressResponse, CompleteStepRequest, SkipStepRequest
)
from src.core.auth import get_current_user
from src.services.step_service import StepService
from src.services.validation_service import ValidationService

router = APIRouter()
logger = logging.getLogger(__name__)
step_service = StepService()
validation_service = ValidationService()


@router.get("/", response_model=List[OnboardingStepResponse])
async def list_steps(
    flow_id: Optional[UUID] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all steps, optionally filtered by flow"""
    query = select(OnboardingStep)
    
    if flow_id:
        query = query.where(OnboardingStep.flow_id == flow_id)
    
    query = query.order_by(OnboardingStep.flow_id, OnboardingStep.order)
    
    result = await db.execute(query)
    steps = result.scalars().all()
    
    return steps


@router.get("/{step_id}", response_model=OnboardingStepResponse)
async def get_step(
    step_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a specific step"""
    step = await db.get(OnboardingStep, step_id)
    
    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Step not found"
        )
    
    # Get user's progress on this step if exists
    progress = await db.execute(
        select(StepProgress)
        .join(UserOnboardingProgress)
        .where(
            and_(
                StepProgress.step_id == step_id,
                UserOnboardingProgress.user_id == current_user.id
            )
        )
    )
    step_progress = progress.scalar()
    
    if step_progress:
        step.user_progress = step_progress
    
    return step


@router.post("/{step_id}/complete", response_model=StepProgressResponse)
async def complete_step(
    step_id: UUID,
    request: CompleteStepRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark a step as completed"""
    # Get the step
    step = await db.get(OnboardingStep, step_id)
    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Step not found"
        )
    
    # Get user's flow progress
    user_progress = await db.execute(
        select(UserOnboardingProgress)
        .where(
            and_(
                UserOnboardingProgress.user_id == current_user.id,
                UserOnboardingProgress.flow_id == step.flow_id
            )
        )
    )
    user_progress = user_progress.scalar()
    
    if not user_progress:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Flow not started"
        )
    
    # Validate step response if needed
    if step.validation_rules and request.response_data:
        is_valid, errors = await validation_service.validate_step_response(
            step, request.response_data
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"message": "Validation failed", "errors": errors}
            )
    
    # Get or create step progress
    step_progress = await db.execute(
        select(StepProgress)
        .where(
            and_(
                StepProgress.user_progress_id == user_progress.id,
                StepProgress.step_id == step_id
            )
        )
    )
    step_progress = step_progress.scalar()
    
    if not step_progress:
        step_progress = StepProgress(
            user_progress_id=user_progress.id,
            step_id=step_id,
            started_at=datetime.utcnow()
        )
        db.add(step_progress)
    
    # Update step progress
    step_progress.status = ProgressStatus.COMPLETED
    step_progress.completed_at = datetime.utcnow()
    step_progress.response_data = request.response_data
    step_progress.attempts += 1
    
    if request.time_spent_seconds:
        step_progress.time_spent_seconds = request.time_spent_seconds
    elif step_progress.started_at:
        step_progress.time_spent_seconds = int(
            (step_progress.completed_at - step_progress.started_at).total_seconds()
        )
    
    # Update flow progress
    user_progress.completed_steps += 1
    user_progress.last_activity_at = datetime.utcnow()
    user_progress.completion_percentage = (
        user_progress.completed_steps / user_progress.total_steps * 100
    )
    
    # Move to next step
    next_step = await step_service.get_next_step(step, db)
    if next_step:
        user_progress.current_step_id = next_step.id
    else:
        # Flow completed
        user_progress.status = ProgressStatus.COMPLETED
        user_progress.completed_at = datetime.utcnow()
        user_progress.is_completed = True
    
    await db.commit()
    await db.refresh(step_progress)
    
    # Execute any step actions in background
    if step.action_url:
        background_tasks.add_task(
            step_service.execute_step_action,
            step=step,
            user_id=current_user.id,
            response_data=request.response_data
        )
    
    logger.info(f"User {current_user.id} completed step {step_id}")
    
    return step_progress


@router.post("/{step_id}/skip", response_model=StepProgressResponse)
async def skip_step(
    step_id: UUID,
    request: SkipStepRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Skip an optional step"""
    # Get the step
    step = await db.get(OnboardingStep, step_id)
    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Step not found"
        )
    
    if not step.is_optional:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This step cannot be skipped"
        )
    
    # Get user's flow progress
    user_progress = await db.execute(
        select(UserOnboardingProgress)
        .where(
            and_(
                UserOnboardingProgress.user_id == current_user.id,
                UserOnboardingProgress.flow_id == step.flow_id
            )
        )
    )
    user_progress = user_progress.scalar()
    
    if not user_progress:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Flow not started"
        )
    
    # Create or update step progress
    step_progress = await db.execute(
        select(StepProgress)
        .where(
            and_(
                StepProgress.user_progress_id == user_progress.id,
                StepProgress.step_id == step_id
            )
        )
    )
    step_progress = step_progress.scalar()
    
    if not step_progress:
        step_progress = StepProgress(
            user_progress_id=user_progress.id,
            step_id=step_id
        )
        db.add(step_progress)
    
    # Mark as skipped
    step_progress.status = ProgressStatus.SKIPPED
    step_progress.metadata["skip_reason"] = request.reason
    
    # Move to next step
    next_step = await step_service.get_next_step(step, db)
    if next_step:
        user_progress.current_step_id = next_step.id
    
    user_progress.last_activity_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(step_progress)
    
    logger.info(f"User {current_user.id} skipped step {step_id}")
    
    return step_progress


@router.post("/", response_model=OnboardingStepResponse)
async def create_step(
    step_data: OnboardingStepCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new step (admin only)"""
    # Check admin permission
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    # Verify flow exists
    flow = await db.get(OnboardingFlow, step_data.flow_id)
    if not flow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flow not found"
        )
    
    # Create step
    step = OnboardingStep(**step_data.dict())
    db.add(step)
    
    # Update flow's total steps count
    await step_service.update_flow_step_count(step_data.flow_id, db)
    
    await db.commit()
    await db.refresh(step)
    
    logger.info(f"Created step: {step.id} for flow {step_data.flow_id}")
    
    return step


@router.put("/{step_id}", response_model=OnboardingStepResponse)
async def update_step(
    step_id: UUID,
    update_data: OnboardingStepUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a step (admin only)"""
    # Check admin permission
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    step = await db.get(OnboardingStep, step_id)
    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Step not found"
        )
    
    # Update step
    for field, value in update_data.dict(exclude_unset=True).items():
        setattr(step, field, value)
    
    await db.commit()
    await db.refresh(step)
    
    logger.info(f"Updated step: {step_id}")
    
    return step


@router.delete("/{step_id}")
async def delete_step(
    step_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a step (admin only)"""
    # Check admin permission
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    step = await db.get(OnboardingStep, step_id)
    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Step not found"
        )
    
    flow_id = step.flow_id
    
    await db.delete(step)
    
    # Update flow's total steps count
    await step_service.update_flow_step_count(flow_id, db)
    
    await db.commit()
    
    logger.info(f"Deleted step: {step_id}")
    
    return {"message": "Step deleted successfully"}


@router.post("/{step_id}/reorder")
async def reorder_step(
    step_id: UUID,
    new_order: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Reorder steps within a flow (admin only)"""
    # Check admin permission
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    step = await db.get(OnboardingStep, step_id)
    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Step not found"
        )
    
    await step_service.reorder_steps(step, new_order, db)
    
    await db.commit()
    
    logger.info(f"Reordered step {step_id} to position {new_order}")
    
    return {"message": "Step reordered successfully"}


from src.db.models import OnboardingFlow