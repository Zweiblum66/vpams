"""
App Marketplace Routes for Plugin Service
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_

from ..core.logging import get_logger
from ..core.exceptions import (
    PluginError,
    PluginNotFoundError,
    PluginPermissionError
)
from ..core.plugin_manager import PluginManager
from ..core.plugin_registry import PluginRegistry
from ..db.base import get_db
from ..models.schemas import (
    PluginMarketplaceResponse,
    PluginInstallRequest,
    PluginReviewRequest,
    PluginSearchRequest
)
from .dependencies import get_current_user, get_plugin_manager, get_plugin_registry

logger = get_logger(__name__)

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


@router.get("/featured", response_model=List[PluginMarketplaceResponse])
async def get_featured_plugins(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get featured plugins from the marketplace"""
    from ..db.models import Plugin, PluginCategory
    
    # Get featured plugins (high rating, many downloads, recently updated)
    result = await db.execute(
        select(Plugin)
        .join(PluginCategory, Plugin.category_id == PluginCategory.id, isouter=True)
        .where(
            and_(
                Plugin.marketplace_status == "published",
                Plugin.status == "enabled",
                Plugin.rating >= 4.0
            )
        )
        .order_by(
            desc(Plugin.rating),
            desc(Plugin.download_count),
            desc(Plugin.updated_at)
        )
        .limit(limit)
    )
    
    plugins = result.scalars().all()
    
    return [
        PluginMarketplaceResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            version=p.version,
            author=p.developer.company_name if p.developer else "Unknown",
            rating=p.rating,
            download_count=p.download_count,
            category=p.category.name if p.category else "Other",
            plugin_type=p.plugin_type,
            price=0.0,  # Free for now
            screenshots=[],
            tags=p.metadata.get("tags", []) if p.metadata else [],
            created_at=p.created_at,
            updated_at=p.updated_at,
            featured=True
        ) for p in plugins
    ]


@router.get("/search", response_model=List[PluginMarketplaceResponse])
async def search_marketplace_plugins(
    query: Optional[str] = None,
    category: Optional[str] = None,
    plugin_type: Optional[str] = None,
    min_rating: Optional[float] = None,
    free_only: bool = False,
    sort_by: str = Query("relevance", regex="^(relevance|rating|downloads|newest|oldest)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Search plugins in the marketplace"""
    from ..db.models import Plugin, PluginCategory
    
    # Build base query
    base_query = select(Plugin).where(
        and_(
            Plugin.marketplace_status == "published",
            Plugin.status == "enabled"
        )
    )
    
    # Add search filters
    if query:
        search_filter = or_(
            Plugin.name.ilike(f"%{query}%"),
            Plugin.description.ilike(f"%{query}%"),
            Plugin.metadata["tags"].astext.ilike(f"%{query}%")
        )
        base_query = base_query.where(search_filter)
    
    if category:
        base_query = base_query.join(PluginCategory).where(PluginCategory.name == category)
    
    if plugin_type:
        base_query = base_query.where(Plugin.plugin_type == plugin_type)
    
    if min_rating:
        base_query = base_query.where(Plugin.rating >= min_rating)
    
    if free_only:
        # For now, all plugins are free, but this will be useful later
        pass
    
    # Add sorting
    if sort_by == "rating":
        base_query = base_query.order_by(desc(Plugin.rating))
    elif sort_by == "downloads":
        base_query = base_query.order_by(desc(Plugin.download_count))
    elif sort_by == "newest":
        base_query = base_query.order_by(desc(Plugin.created_at))
    elif sort_by == "oldest":
        base_query = base_query.order_by(Plugin.created_at)
    else:  # relevance
        if query:
            # Order by text match relevance (simplified)
            base_query = base_query.order_by(
                desc(Plugin.rating),
                desc(Plugin.download_count)
            )
        else:
            base_query = base_query.order_by(
                desc(Plugin.rating),
                desc(Plugin.download_count)
            )
    
    # Add pagination
    offset = (page - 1) * limit
    base_query = base_query.offset(offset).limit(limit)
    
    result = await db.execute(base_query)
    plugins = result.scalars().all()
    
    return [
        PluginMarketplaceResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            version=p.version,
            author=p.developer.company_name if p.developer else "Unknown",
            rating=p.rating,
            download_count=p.download_count,
            category=p.category.name if p.category else "Other",
            plugin_type=p.plugin_type,
            price=0.0,
            screenshots=[],
            tags=p.metadata.get("tags", []) if p.metadata else [],
            created_at=p.created_at,
            updated_at=p.updated_at,
            featured=False
        ) for p in plugins
    ]


@router.get("/categories", response_model=List[Dict[str, Any]])
async def get_plugin_categories(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all plugin categories with plugin counts"""
    from ..db.models import Plugin, PluginCategory
    
    # Get categories with plugin counts
    result = await db.execute(
        select(
            PluginCategory.id,
            PluginCategory.name,
            PluginCategory.description,
            PluginCategory.icon,
            func.count(Plugin.id).label("plugin_count")
        )
        .outerjoin(
            Plugin,
            and_(
                Plugin.category_id == PluginCategory.id,
                Plugin.marketplace_status == "published",
                Plugin.status == "enabled"
            )
        )
        .group_by(PluginCategory.id, PluginCategory.name, PluginCategory.description, PluginCategory.icon)
        .order_by(PluginCategory.name)
    )
    
    categories = result.all()
    
    return [
        {
            "id": cat.id,
            "name": cat.name,
            "description": cat.description,
            "icon": cat.icon,
            "plugin_count": cat.plugin_count
        } for cat in categories
    ]


@router.get("/popular", response_model=List[PluginMarketplaceResponse])
async def get_popular_plugins(
    limit: int = Query(10, ge=1, le=50),
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get popular plugins based on recent downloads and usage"""
    from ..db.models import Plugin, PluginExecution
    from datetime import timedelta
    
    # Calculate popularity based on recent downloads and executions
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    result = await db.execute(
        select(Plugin)
        .outerjoin(PluginExecution, Plugin.id == PluginExecution.plugin_id)
        .where(
            and_(
                Plugin.marketplace_status == "published",
                Plugin.status == "enabled"
            )
        )
        .group_by(Plugin.id)
        .order_by(
            desc(func.count(PluginExecution.id)),  # Recent executions
            desc(Plugin.download_count),           # Total downloads
            desc(Plugin.rating)                    # Rating
        )
        .limit(limit)
    )
    
    plugins = result.scalars().all()
    
    return [
        PluginMarketplaceResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            version=p.version,
            author=p.developer.company_name if p.developer else "Unknown",
            rating=p.rating,
            download_count=p.download_count,
            category=p.category.name if p.category else "Other",
            plugin_type=p.plugin_type,
            price=0.0,
            screenshots=[],
            tags=p.metadata.get("tags", []) if p.metadata else [],
            created_at=p.created_at,
            updated_at=p.updated_at,
            featured=False
        ) for p in plugins
    ]


@router.get("/{plugin_id}", response_model=Dict[str, Any])
async def get_plugin_details(
    plugin_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get detailed information about a specific plugin"""
    from ..db.models import Plugin, PluginReview, PluginInstallation
    
    # Get plugin details
    plugin_result = await db.execute(
        select(Plugin).where(
            and_(
                Plugin.id == plugin_id,
                Plugin.marketplace_status == "published"
            )
        )
    )
    plugin = plugin_result.scalar_one_or_none()
    
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    # Get recent reviews
    reviews_result = await db.execute(
        select(PluginReview)
        .where(PluginReview.plugin_id == plugin_id)
        .order_by(desc(PluginReview.created_at))
        .limit(10)
    )
    reviews = reviews_result.scalars().all()
    
    # Check if user has installed this plugin
    installation_result = await db.execute(
        select(PluginInstallation).where(
            and_(
                PluginInstallation.plugin_id == plugin_id,
                PluginInstallation.tenant_id == current_user.get("tenant_id")
            )
        )
    )
    installation = installation_result.scalar_one_or_none()
    
    # Get rating distribution
    rating_dist_result = await db.execute(
        select(
            PluginReview.rating,
            func.count(PluginReview.id).label("count")
        )
        .where(PluginReview.plugin_id == plugin_id)
        .group_by(PluginReview.rating)
        .order_by(PluginReview.rating)
    )
    rating_distribution = {str(row.rating): row.count for row in rating_dist_result}
    
    return {
        "id": plugin.id,
        "name": plugin.name,
        "description": plugin.description,
        "long_description": plugin.metadata.get("long_description", plugin.description),
        "version": plugin.version,
        "author": plugin.developer.company_name if plugin.developer else "Unknown",
        "author_verified": plugin.developer.verified if plugin.developer else False,
        "rating": plugin.rating,
        "download_count": plugin.download_count,
        "category": plugin.category.name if plugin.category else "Other",
        "plugin_type": plugin.plugin_type,
        "price": 0.0,
        "screenshots": plugin.metadata.get("screenshots", []) if plugin.metadata else [],
        "tags": plugin.metadata.get("tags", []) if plugin.metadata else [],
        "requirements": plugin.metadata.get("requirements", {}) if plugin.metadata else {},
        "changelog": plugin.metadata.get("changelog", []) if plugin.metadata else [],
        "documentation_url": plugin.metadata.get("documentation_url"),
        "support_url": plugin.metadata.get("support_url"),
        "source_url": plugin.metadata.get("source_url"),
        "license": plugin.metadata.get("license", "Proprietary"),
        "created_at": plugin.created_at,
        "updated_at": plugin.updated_at,
        "is_installed": installation is not None,
        "installation_status": installation.status if installation else None,
        "reviews": [
            {
                "id": r.id,
                "rating": r.rating,
                "title": r.title,
                "comment": r.comment,
                "author": "Anonymous",  # Privacy protection
                "created_at": r.created_at,
                "helpful_count": 0  # TODO: Implement helpful votes
            } for r in reviews
        ],
        "rating_distribution": rating_distribution,
        "total_reviews": len(reviews)
    }


@router.post("/{plugin_id}/install", response_model=Dict[str, str])
async def install_plugin_from_marketplace(
    plugin_id: str,
    config: Optional[Dict[str, Any]] = None,
    plugin_manager: PluginManager = Depends(get_plugin_manager),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Install a plugin from the marketplace"""
    from ..db.models import Plugin, PluginInstallation
    import uuid
    
    # Check if plugin exists and is published
    plugin_result = await db.execute(
        select(Plugin).where(
            and_(
                Plugin.id == plugin_id,
                Plugin.marketplace_status == "published",
                Plugin.status == "enabled"
            )
        )
    )
    plugin = plugin_result.scalar_one_or_none()
    
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found or not available")
    
    # Check if already installed
    existing_installation = await db.execute(
        select(PluginInstallation).where(
            and_(
                PluginInstallation.plugin_id == plugin_id,
                PluginInstallation.tenant_id == current_user.get("tenant_id")
            )
        )
    )
    
    if existing_installation.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Plugin already installed")
    
    try:
        # Create installation record
        installation = PluginInstallation(
            id=str(uuid.uuid4()),
            plugin_id=plugin_id,
            tenant_id=current_user.get("tenant_id"),
            installed_by=current_user.get("id"),
            status="installing",
            config=config or {}
        )
        
        db.add(installation)
        await db.commit()
        
        # Install plugin through plugin manager
        # TODO: Implement actual plugin installation from marketplace
        # This would involve downloading plugin files and installing them
        
        # Update installation status
        installation.status = "installed"
        installation.installed_at = datetime.utcnow()
        
        # Increment download count
        plugin.download_count += 1
        
        await db.commit()
        
        logger.info(
            "Plugin installed from marketplace",
            plugin_id=plugin_id,
            tenant_id=current_user.get("tenant_id"),
            user_id=current_user.get("id")
        )
        
        return {"message": "Plugin installed successfully", "installation_id": installation.id}
        
    except Exception as e:
        logger.error(f"Failed to install plugin {plugin_id}: {e}")
        # Update installation status to failed
        if 'installation' in locals():
            installation.status = "failed"
            installation.error_message = str(e)
            await db.commit()
        
        raise HTTPException(status_code=500, detail="Plugin installation failed")


@router.delete("/{plugin_id}/install", response_model=Dict[str, str])
async def uninstall_plugin_from_marketplace(
    plugin_id: str,
    plugin_manager: PluginManager = Depends(get_plugin_manager),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Uninstall a plugin"""
    from ..db.models import PluginInstallation
    
    # Find installation
    installation_result = await db.execute(
        select(PluginInstallation).where(
            and_(
                PluginInstallation.plugin_id == plugin_id,
                PluginInstallation.tenant_id == current_user.get("tenant_id")
            )
        )
    )
    installation = installation_result.scalar_one_or_none()
    
    if not installation:
        raise HTTPException(status_code=404, detail="Plugin not installed")
    
    try:
        # Uninstall through plugin manager
        await plugin_manager.uninstall_plugin(plugin_id)
        
        # Remove installation record
        await db.delete(installation)
        await db.commit()
        
        logger.info(
            "Plugin uninstalled",
            plugin_id=plugin_id,
            tenant_id=current_user.get("tenant_id"),
            user_id=current_user.get("id")
        )
        
        return {"message": "Plugin uninstalled successfully"}
        
    except Exception as e:
        logger.error(f"Failed to uninstall plugin {plugin_id}: {e}")
        raise HTTPException(status_code=500, detail="Plugin uninstallation failed")


@router.post("/{plugin_id}/reviews", response_model=Dict[str, str])
async def add_plugin_review(
    plugin_id: str,
    review: PluginReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Add a review for a plugin"""
    from ..db.models import Plugin, PluginReview, PluginInstallation
    import uuid
    
    # Check if plugin exists
    plugin_result = await db.execute(
        select(Plugin).where(Plugin.id == plugin_id)
    )
    plugin = plugin_result.scalar_one_or_none()
    
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    # Check if user has installed the plugin (requirement for reviewing)
    installation_result = await db.execute(
        select(PluginInstallation).where(
            and_(
                PluginInstallation.plugin_id == plugin_id,
                PluginInstallation.tenant_id == current_user.get("tenant_id"),
                PluginInstallation.status == "installed"
            )
        )
    )
    
    if not installation_result.scalar_one_or_none():
        raise HTTPException(
            status_code=403, 
            detail="You must install and use the plugin before reviewing it"
        )
    
    # Check if user already reviewed this plugin
    existing_review = await db.execute(
        select(PluginReview).where(
            and_(
                PluginReview.plugin_id == plugin_id,
                PluginReview.user_id == current_user.get("id")
            )
        )
    )
    
    if existing_review.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="You have already reviewed this plugin")
    
    # Create review
    plugin_review = PluginReview(
        id=str(uuid.uuid4()),
        plugin_id=plugin_id,
        user_id=current_user.get("id"),
        rating=review.rating,
        title=review.title,
        comment=review.comment
    )
    
    db.add(plugin_review)
    
    # Update plugin rating
    avg_rating_result = await db.execute(
        select(func.avg(PluginReview.rating)).where(PluginReview.plugin_id == plugin_id)
    )
    new_avg_rating = avg_rating_result.scalar()
    
    if new_avg_rating:
        plugin.rating = float(new_avg_rating)
    
    await db.commit()
    
    return {"message": "Review added successfully"}


@router.get("/my/installed", response_model=List[Dict[str, Any]])
async def get_my_installed_plugins(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get plugins installed by the current user/tenant"""
    from ..db.models import Plugin, PluginInstallation
    
    result = await db.execute(
        select(PluginInstallation, Plugin)
        .join(Plugin, PluginInstallation.plugin_id == Plugin.id)
        .where(PluginInstallation.tenant_id == current_user.get("tenant_id"))
        .order_by(desc(PluginInstallation.installed_at))
    )
    
    installations = result.all()
    
    return [
        {
            "installation_id": inst.PluginInstallation.id,
            "plugin_id": inst.Plugin.id,
            "name": inst.Plugin.name,
            "description": inst.Plugin.description,
            "version": inst.Plugin.version,
            "plugin_type": inst.Plugin.plugin_type,
            "status": inst.PluginInstallation.status,
            "installed_at": inst.PluginInstallation.installed_at,
            "last_used": inst.PluginInstallation.last_used,
            "config": inst.PluginInstallation.config,
            "error_message": inst.PluginInstallation.error_message
        } for inst in installations
    ]


@router.get("/stats", response_model=Dict[str, Any])
async def get_marketplace_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get marketplace statistics"""
    from ..db.models import Plugin, PluginCategory, PluginReview, PluginInstallation
    
    # Total plugins
    total_plugins_result = await db.execute(
        select(func.count(Plugin.id)).where(
            and_(
                Plugin.marketplace_status == "published",
                Plugin.status == "enabled"
            )
        )
    )
    total_plugins = total_plugins_result.scalar()
    
    # Total downloads
    total_downloads_result = await db.execute(
        select(func.sum(Plugin.download_count)).where(
            and_(
                Plugin.marketplace_status == "published",
                Plugin.status == "enabled"
            )
        )
    )
    total_downloads = total_downloads_result.scalar() or 0
    
    # Average rating
    avg_rating_result = await db.execute(
        select(func.avg(Plugin.rating)).where(
            and_(
                Plugin.marketplace_status == "published",
                Plugin.status == "enabled",
                Plugin.rating > 0
            )
        )
    )
    avg_rating = avg_rating_result.scalar() or 0
    
    # Categories count
    categories_result = await db.execute(
        select(func.count(PluginCategory.id))
    )
    total_categories = categories_result.scalar()
    
    # Recent activity (last 30 days)
    from datetime import timedelta
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    recent_plugins_result = await db.execute(
        select(func.count(Plugin.id)).where(
            and_(
                Plugin.marketplace_status == "published",
                Plugin.created_at >= thirty_days_ago
            )
        )
    )
    recent_plugins = recent_plugins_result.scalar()
    
    return {
        "total_plugins": total_plugins,
        "total_downloads": total_downloads,
        "average_rating": round(float(avg_rating), 2) if avg_rating else 0,
        "total_categories": total_categories,
        "recent_plugins": recent_plugins,
        "marketplace_health": {
            "active_plugins": total_plugins,
            "avg_rating": round(float(avg_rating), 2) if avg_rating else 0,
            "growth_rate": "5.2%"  # TODO: Calculate actual growth rate
        }
    }