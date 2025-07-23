"""Feature flags API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from typing import List, Optional
from datetime import datetime
import random

from ..core.database import get_db
from ..core.auth import get_current_user, require_admin
from ..models import FeatureFlag, UserFeatureAccess, BetaUser
from ..schemas.feature import (
    FeatureFlagCreate,
    FeatureFlagUpdate,
    FeatureFlagResponse,
    FeatureFlagListResponse,
    UserFeatureResponse,
    FeatureToggleRequest
)
from ..services.feature_service import (
    is_feature_enabled_for_user,
    assign_feature_to_user,
    get_user_features
)
from ..core.config import get_settings

router = APIRouter(prefix="/beta/features", tags=["Feature Flags"])


@router.get("", response_model=FeatureFlagListResponse)
async def list_features(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    is_enabled: Optional[bool] = None,
    risk_level: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List all beta features"""
    # Build query
    query = select(FeatureFlag)
    
    # Apply filters
    if category:
        query = query.where(FeatureFlag.category == category)
    
    if is_enabled is not None:
        query = query.where(FeatureFlag.is_enabled == is_enabled)
    
    if risk_level:
        query = query.where(FeatureFlag.risk_level == risk_level)
    
    # Get total count
    count_query = select(func.count()).select_from(FeatureFlag)
    if category or is_enabled is not None or risk_level:
        count_query = query.with_only_columns([func.count()])
    total = await db.scalar(count_query)
    
    # Apply pagination
    query = query.offset((page - 1) * limit).limit(limit)
    query = query.order_by(FeatureFlag.created_at.desc())
    
    # Execute query
    result = await db.execute(query)
    features = result.scalars().all()
    
    return FeatureFlagListResponse(
        features=[FeatureFlagResponse.from_orm(feature) for feature in features],
        total=total,
        page=page,
        limit=limit,
        pages=(total + limit - 1) // limit
    )


@router.get("/{feature_id}", response_model=FeatureFlagResponse)
async def get_feature(
    feature_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get feature details"""
    result = await db.execute(
        select(FeatureFlag).where(FeatureFlag.id == feature_id)
    )
    feature = result.scalar_one_or_none()
    
    if not feature:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feature not found"
        )
    
    return FeatureFlagResponse.from_orm(feature)


@router.post("", response_model=FeatureFlagResponse)
async def create_feature(
    feature: FeatureFlagCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Create new beta feature (admin only)"""
    # Check for existing feature
    result = await db.execute(
        select(FeatureFlag).where(FeatureFlag.name == feature.name)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Feature with this name already exists"
        )
    
    # Create feature
    new_feature = FeatureFlag(
        **feature.dict(),
        created_by=current_user["email"]
    )
    
    db.add(new_feature)
    await db.commit()
    await db.refresh(new_feature)
    
    return FeatureFlagResponse.from_orm(new_feature)


@router.put("/{feature_id}", response_model=FeatureFlagResponse)
async def update_feature(
    feature_id: str,
    update: FeatureFlagUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Update feature flag (admin only)"""
    # Get feature
    result = await db.execute(
        select(FeatureFlag).where(FeatureFlag.id == feature_id)
    )
    feature = result.scalar_one_or_none()
    
    if not feature:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feature not found"
        )
    
    # Update feature
    update_data = update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(feature, field, value)
    
    feature.updated_at = datetime.utcnow()
    
    # Update changelog
    if not feature.changelog:
        feature.changelog = []
    
    feature.changelog.append({
        "date": datetime.utcnow().isoformat(),
        "user": current_user["email"],
        "changes": list(update_data.keys())
    })
    
    await db.commit()
    await db.refresh(feature)
    
    return FeatureFlagResponse.from_orm(feature)


@router.get("/user/{user_id}", response_model=List[UserFeatureResponse])
async def get_user_features(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get features available to a user"""
    # Check permission
    if not current_user.get("is_admin") and str(current_user["user_id"]) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only view own features"
        )
    
    # Get beta user
    result = await db.execute(
        select(BetaUser).where(BetaUser.user_id == user_id)
    )
    beta_user = result.scalar_one_or_none()
    
    if not beta_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not in beta program"
        )
    
    # Get user features
    features = await get_user_features(db, beta_user)
    
    return [UserFeatureResponse(
        feature_id=str(feature.id),
        name=feature.name,
        display_name=feature.display_name,
        description=feature.description,
        category=feature.category,
        is_enabled=await is_feature_enabled_for_user(db, beta_user, feature),
        variant=None,  # Would be populated from UserFeatureAccess
        config=feature.config
    ) for feature in features]


@router.post("/{feature_id}/toggle")
async def toggle_feature_for_user(
    feature_id: str,
    request: FeatureToggleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Toggle feature for a user (admin only)"""
    # Get feature
    result = await db.execute(
        select(FeatureFlag).where(FeatureFlag.id == feature_id)
    )
    feature = result.scalar_one_or_none()
    
    if not feature:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feature not found"
        )
    
    # Get beta user
    result = await db.execute(
        select(BetaUser).where(BetaUser.user_id == request.user_id)
    )
    beta_user = result.scalar_one_or_none()
    
    if not beta_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not in beta program"
        )
    
    # Get or create user feature access
    result = await db.execute(
        select(UserFeatureAccess).where(
            and_(
                UserFeatureAccess.beta_user_id == beta_user.id,
                UserFeatureAccess.feature_id == feature.id
            )
        )
    )
    access = result.scalar_one_or_none()
    
    if not access:
        access = UserFeatureAccess(
            beta_user_id=beta_user.id,
            feature_id=feature.id,
            is_enabled=request.enabled
        )
        db.add(access)
    else:
        access.is_enabled = request.enabled
        if request.enabled:
            access.enabled_at = datetime.utcnow()
        else:
            access.disabled_at = datetime.utcnow()
    
    await db.commit()
    
    return {
        "message": f"Feature {'enabled' if request.enabled else 'disabled'} for user",
        "feature": feature.name,
        "user_id": str(beta_user.user_id),
        "enabled": request.enabled
    }


@router.post("/{feature_id}/rollout")
async def update_feature_rollout(
    feature_id: str,
    percentage: int = Query(..., ge=0, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Update feature rollout percentage (admin only)"""
    # Get feature
    result = await db.execute(
        select(FeatureFlag).where(FeatureFlag.id == feature_id)
    )
    feature = result.scalar_one_or_none()
    
    if not feature:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feature not found"
        )
    
    # Update rollout
    old_percentage = feature.rollout_percentage
    feature.rollout_percentage = percentage
    feature.updated_at = datetime.utcnow()
    
    # Update changelog
    if not feature.changelog:
        feature.changelog = []
    
    feature.changelog.append({
        "date": datetime.utcnow().isoformat(),
        "user": current_user["email"],
        "action": "rollout_update",
        "old_value": old_percentage,
        "new_value": percentage
    })
    
    await db.commit()
    
    # Optionally, update user access based on new percentage
    # This would involve selecting random users to enable/disable the feature
    
    return {
        "message": "Feature rollout updated",
        "feature": feature.name,
        "old_percentage": old_percentage,
        "new_percentage": percentage
    }