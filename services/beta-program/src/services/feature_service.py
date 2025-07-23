"""Feature flag service"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import random

from ..models import FeatureFlag, UserFeatureAccess, BetaUser
from ..core.config import get_settings


async def is_feature_enabled_for_user(
    db: AsyncSession,
    beta_user: BetaUser,
    feature: FeatureFlag
) -> bool:
    """Check if a feature is enabled for a user"""
    # Check if feature is globally enabled
    if not feature.is_enabled:
        return False
    
    # Check beta phase compatibility
    if beta_user.beta_phase not in feature.available_phases:
        return False
    
    # Check access level
    access_levels = ["standard", "advanced", "full"]
    user_level_index = access_levels.index(beta_user.feature_access_level)
    min_level_index = access_levels.index(feature.min_access_level)
    
    if user_level_index < min_level_index:
        return False
    
    # Check user-specific access
    result = await db.execute(
        select(UserFeatureAccess).where(
            and_(
                UserFeatureAccess.beta_user_id == beta_user.id,
                UserFeatureAccess.feature_id == feature.id
            )
        )
    )
    user_access = result.scalar_one_or_none()
    
    if user_access:
        return user_access.is_enabled
    
    # Check rollout strategy
    if feature.rollout_strategy == "all_beta":
        return True
    elif feature.rollout_strategy == "percentage":
        # Deterministic assignment based on user ID
        hash_value = hash(f"{beta_user.id}-{feature.id}")
        return (hash_value % 100) < feature.rollout_percentage
    elif feature.rollout_strategy == "whitelist":
        return False  # Only enabled via explicit user access
    elif feature.rollout_strategy == "specific_phase":
        return beta_user.beta_phase in feature.available_phases
    
    return False


async def assign_feature_to_user(
    db: AsyncSession,
    beta_user: BetaUser,
    feature: FeatureFlag,
    enabled: bool = True,
    variant: Optional[str] = None
) -> UserFeatureAccess:
    """Assign a feature to a user"""
    # Check for existing access
    result = await db.execute(
        select(UserFeatureAccess).where(
            and_(
                UserFeatureAccess.beta_user_id == beta_user.id,
                UserFeatureAccess.feature_id == feature.id
            )
        )
    )
    user_access = result.scalar_one_or_none()
    
    if not user_access:
        # Create new access
        user_access = UserFeatureAccess(
            beta_user_id=beta_user.id,
            feature_id=feature.id,
            is_enabled=enabled,
            variant=variant
        )
        db.add(user_access)
    else:
        # Update existing access
        user_access.is_enabled = enabled
        if variant:
            user_access.variant = variant
    
    await db.commit()
    return user_access


async def get_user_features(
    db: AsyncSession,
    beta_user: BetaUser
) -> List[FeatureFlag]:
    """Get all features available to a user"""
    # Get all enabled features
    result = await db.execute(
        select(FeatureFlag).where(FeatureFlag.is_enabled == True)
    )
    all_features = result.scalars().all()
    
    # Filter features available to user
    available_features = []
    for feature in all_features:
        if await is_feature_enabled_for_user(db, beta_user, feature):
            available_features.append(feature)
    
    return available_features


async def track_feature_usage(
    db: AsyncSession,
    beta_user_id: str,
    feature_id: str,
    action: str,
    duration: Optional[float] = None,
    success: bool = True,
    error_type: Optional[str] = None,
    context: Optional[dict] = None
):
    """Track feature usage for analytics"""
    from ..models import FeatureUsage
    import uuid
    
    usage = FeatureUsage(
        beta_user_id=beta_user_id,
        feature_id=feature_id,
        action=action,
        duration=duration,
        success=1 if success else 0,
        error_type=error_type,
        context=context,
        session_id=str(uuid.uuid4())  # Would use actual session ID
    )
    
    db.add(usage)
    
    # Update user's last feature access
    result = await db.execute(
        select(UserFeatureAccess).where(
            and_(
                UserFeatureAccess.beta_user_id == beta_user_id,
                UserFeatureAccess.feature_id == feature_id
            )
        )
    )
    user_access = result.scalar_one_or_none()
    
    if user_access:
        from datetime import datetime
        if not user_access.first_used_at:
            user_access.first_used_at = datetime.utcnow()
        user_access.last_used_at = datetime.utcnow()
        user_access.usage_count += 1
    
    await db.commit()