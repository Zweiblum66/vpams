"""
API Routes for Plugin Service
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.logging import get_logger
from ..core.exceptions import (
    PluginError,
    PluginNotFoundError,
    PluginValidationError,
    PluginPermissionError
)
from ..core.plugin_manager import PluginManager
from ..core.plugin_registry import PluginRegistry
from ..db.base import get_db
from ..models.schemas import (
    PluginMetadataResponse,
    PluginListResponse,
    PluginInstallRequest,
    PluginConfigUpdate,
    PluginHealthResponse,
    PluginExecuteRequest,
    PluginExecuteResponse,
    PluginSearchRequest,
    PluginRegistryResponse,
    PluginReviewRequest,
    DeveloperAccountResponse,
    WebhookRequest,
    WebhookResponse
)
from .dependencies import get_current_user, get_plugin_manager, get_plugin_registry

logger = get_logger(__name__)

router = APIRouter()


# Plugin Management Routes
@router.get("/plugins", response_model=PluginListResponse)
async def list_plugins(
    plugin_type: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    plugin_manager: PluginManager = Depends(get_plugin_manager),
    current_user: dict = Depends(get_current_user)
):
    """List all installed plugins"""
    try:
        plugins = await plugin_manager.get_all_plugins()
        
        # Filter by type if specified
        if plugin_type:
            plugins = [p for p in plugins if p.get_type().value == plugin_type]
        
        # Filter by status if specified
        if status:
            plugins = [p for p in plugins if p.status.value == status]
        
        # Pagination
        total = len(plugins)
        start = (page - 1) * limit
        end = start + limit
        plugins = plugins[start:end]
        
        return PluginListResponse(
            plugins=[PluginMetadataResponse.from_plugin(p) for p in plugins],
            total=total,
            page=page,
            limit=limit
        )
    except Exception as e:
        logger.error("Failed to list plugins", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list plugins")


@router.get("/plugins/{plugin_id}", response_model=PluginMetadataResponse)
async def get_plugin(
    plugin_id: str,
    plugin_manager: PluginManager = Depends(get_plugin_manager),
    current_user: dict = Depends(get_current_user)
):
    """Get plugin details"""
    plugin = await plugin_manager.get_plugin(plugin_id)
    if not plugin:
        raise PluginNotFoundError(plugin_id)
    
    return PluginMetadataResponse.from_plugin(plugin)


@router.post("/plugins/install", response_model=PluginMetadataResponse)
async def install_plugin(
    file: UploadFile = File(...),
    plugin_manager: PluginManager = Depends(get_plugin_manager),
    current_user: dict = Depends(get_current_user)
):
    """Install a plugin from uploaded package"""
    if not current_user.get("is_superuser"):
        raise PluginPermissionError("install", "admin privileges required")
    
    try:
        # Read plugin package
        contents = await file.read()
        
        # Install plugin
        metadata = await plugin_manager.install_plugin(contents, file.filename)
        
        return PluginMetadataResponse.from_metadata(metadata)
    except PluginError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error("Failed to install plugin", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to install plugin")


@router.delete("/plugins/{plugin_id}")
async def uninstall_plugin(
    plugin_id: str,
    plugin_manager: PluginManager = Depends(get_plugin_manager),
    current_user: dict = Depends(get_current_user)
):
    """Uninstall a plugin"""
    if not current_user.get("is_superuser"):
        raise PluginPermissionError("uninstall", "admin privileges required")
    
    try:
        await plugin_manager.uninstall_plugin(plugin_id)
        return {"message": f"Plugin {plugin_id} uninstalled successfully"}
    except PluginError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error("Failed to uninstall plugin", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to uninstall plugin")


@router.post("/plugins/{plugin_id}/enable")
async def enable_plugin(
    plugin_id: str,
    plugin_manager: PluginManager = Depends(get_plugin_manager),
    current_user: dict = Depends(get_current_user)
):
    """Enable a plugin"""
    if not current_user.get("is_superuser"):
        raise PluginPermissionError("enable", "admin privileges required")
    
    try:
        await plugin_manager.enable_plugin(plugin_id)
        return {"message": f"Plugin {plugin_id} enabled successfully"}
    except PluginError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/plugins/{plugin_id}/disable")
async def disable_plugin(
    plugin_id: str,
    plugin_manager: PluginManager = Depends(get_plugin_manager),
    current_user: dict = Depends(get_current_user)
):
    """Disable a plugin"""
    if not current_user.get("is_superuser"):
        raise PluginPermissionError("disable", "admin privileges required")
    
    try:
        await plugin_manager.disable_plugin(plugin_id)
        return {"message": f"Plugin {plugin_id} disabled successfully"}
    except PluginError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/plugins/{plugin_id}/reload")
async def reload_plugin(
    plugin_id: str,
    plugin_manager: PluginManager = Depends(get_plugin_manager),
    current_user: dict = Depends(get_current_user)
):
    """Reload a plugin"""
    if not current_user.get("is_superuser"):
        raise PluginPermissionError("reload", "admin privileges required")
    
    try:
        await plugin_manager.reload_plugin(plugin_id)
        return {"message": f"Plugin {plugin_id} reloaded successfully"}
    except PluginError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.put("/plugins/{plugin_id}/config")
async def update_plugin_config(
    plugin_id: str,
    config: PluginConfigUpdate,
    plugin_manager: PluginManager = Depends(get_plugin_manager),
    current_user: dict = Depends(get_current_user)
):
    """Update plugin configuration"""
    if not current_user.get("is_superuser"):
        raise PluginPermissionError("configure", "admin privileges required")
    
    plugin = await plugin_manager.get_plugin(plugin_id)
    if not plugin:
        raise PluginNotFoundError(plugin_id)
    
    # Validate settings
    if not plugin.validate_settings(config.settings):
        raise PluginValidationError(plugin_id, ["Invalid settings"])
    
    # Update config
    plugin.config.settings = config.settings
    
    # Reload if needed
    if config.reload:
        await plugin_manager.reload_plugin(plugin_id)
    
    return {"message": f"Plugin {plugin_id} configuration updated"}


@router.get("/plugins/{plugin_id}/health", response_model=PluginHealthResponse)
async def get_plugin_health(
    plugin_id: str,
    plugin_manager: PluginManager = Depends(get_plugin_manager),
    current_user: dict = Depends(get_current_user)
):
    """Get plugin health status"""
    plugin = await plugin_manager.get_plugin(plugin_id)
    if not plugin:
        raise PluginNotFoundError(plugin_id)
    
    health = plugin.get_health_status()
    
    return PluginHealthResponse(
        plugin_id=plugin_id,
        status=plugin.status.value,
        health=health
    )


@router.post("/plugins/{plugin_id}/execute", response_model=PluginExecuteResponse)
async def execute_plugin_hook(
    plugin_id: str,
    request: PluginExecuteRequest,
    plugin_manager: PluginManager = Depends(get_plugin_manager),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Execute a plugin hook"""
    plugin = await plugin_manager.get_plugin(plugin_id)
    if not plugin:
        raise PluginNotFoundError(plugin_id)
    
    # Check permissions
    if request.capability and not plugin.has_capability(request.capability):
        raise PluginPermissionError(plugin_id, request.capability)
    
    try:
        # Create context
        from ..core.plugin_base import PluginContext
        context = PluginContext(
            user_id=current_user.get("id"),
            tenant_id=current_user.get("tenant_id"),
            metadata=request.context_metadata
        )
        
        # Execute hook
        result = await plugin.execute_hook(
            request.hook_name,
            context,
            **request.parameters
        )
        
        # Log execution
        from ..db.models import PluginExecution
        execution = PluginExecution(
            plugin_id=plugin.metadata.id,
            tenant_id=current_user.get("tenant_id"),
            user_id=current_user.get("id"),
            hook_name=request.hook_name,
            context=request.context_metadata,
            parameters=request.parameters,
            success=result.success,
            result=result.data,
            error=result.error
        )
        db.add(execution)
        await db.commit()
        
        return PluginExecuteResponse(
            success=result.success,
            data=result.data,
            error=result.error,
            metadata=result.metadata
        )
    except Exception as e:
        logger.error(
            "Plugin execution failed",
            plugin_id=plugin_id,
            hook=request.hook_name,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Plugin execution failed")


# Plugin Registry Routes
@router.get("/registry/search", response_model=List[PluginRegistryResponse])
async def search_registry(
    query: Optional[str] = None,
    plugin_type: Optional[str] = None,
    tags: Optional[List[str]] = Query(None),
    min_rating: Optional[float] = None,
    max_price: Optional[float] = None,
    sort_by: str = Query("downloads", pattern="^(downloads|rating|name|updated)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    plugin_registry: PluginRegistry = Depends(get_plugin_registry),
    current_user: dict = Depends(get_current_user)
):
    """Search plugin registry"""
    results = plugin_registry.search_plugins(
        query=query,
        plugin_type=plugin_type,
        tags=tags,
        min_rating=min_rating,
        max_price=max_price,
        sort_by=sort_by,
        limit=limit,
        offset=(page - 1) * limit
    )
    
    return [PluginRegistryResponse(**result) for result in results]


@router.get("/registry/featured", response_model=List[PluginRegistryResponse])
async def get_featured_plugins(
    plugin_registry: PluginRegistry = Depends(get_plugin_registry),
    current_user: dict = Depends(get_current_user)
):
    """Get featured plugins"""
    results = plugin_registry.get_featured_plugins()
    return [PluginRegistryResponse(**result) for result in results]


@router.get("/registry/popular", response_model=List[PluginRegistryResponse])
async def get_popular_plugins(
    limit: int = Query(10, ge=1, le=50),
    plugin_registry: PluginRegistry = Depends(get_plugin_registry),
    current_user: dict = Depends(get_current_user)
):
    """Get popular plugins"""
    results = plugin_registry.get_popular_plugins(limit)
    return [PluginRegistryResponse(**result) for result in results]


@router.post("/registry/{plugin_id}/install")
async def install_from_registry(
    plugin_id: str,
    plugin_registry: PluginRegistry = Depends(get_plugin_registry),
    plugin_manager: PluginManager = Depends(get_plugin_manager),
    current_user: dict = Depends(get_current_user)
):
    """Install a plugin from registry"""
    if not current_user.get("is_superuser"):
        raise PluginPermissionError("install", "admin privileges required")
    
    # Get plugin from registry
    plugin_entry = plugin_registry.get_plugin(plugin_id)
    if not plugin_entry:
        raise PluginNotFoundError(plugin_id)
    
    # Download and install
    # TODO: Implement download from URL
    # For now, return not implemented
    raise HTTPException(
        status_code=501,
        detail="Registry installation not yet implemented"
    )


@router.post("/registry/{plugin_id}/review", response_model=Dict[str, str])
async def add_plugin_review(
    plugin_id: str,
    review: PluginReviewRequest,
    plugin_registry: PluginRegistry = Depends(get_plugin_registry),
    current_user: dict = Depends(get_current_user)
):
    """Add a review for a plugin"""
    try:
        plugin_registry.add_review(
            plugin_id,
            current_user.get("id"),
            review.rating,
            review.comment
        )
        return {"message": "Review added successfully"}
    except PluginError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


# Developer Routes
@router.get("/developer/account", response_model=DeveloperAccountResponse)
async def get_developer_account(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get developer account information"""
    from sqlalchemy import select
    from ..db.models import DeveloperAccount
    
    result = await db.execute(
        select(DeveloperAccount).where(
            DeveloperAccount.user_id == current_user.get("id")
        )
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(status_code=404, detail="Developer account not found")
    
    return DeveloperAccountResponse.from_orm(account)


@router.post("/developer/register", response_model=DeveloperAccountResponse)
async def register_developer(
    company_name: Optional[str] = None,
    website: Optional[str] = None,
    support_email: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Register as a plugin developer"""
    from ..db.models import DeveloperAccount
    import secrets
    
    # Check if already registered
    existing = await db.execute(
        select(DeveloperAccount).where(
            DeveloperAccount.user_id == current_user.get("id")
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already registered as developer")
    
    # Create developer account
    account = DeveloperAccount(
        user_id=current_user.get("id"),
        company_name=company_name,
        website=website,
        support_email=support_email,
        api_key=secrets.token_urlsafe(32),
        api_key_created_at=datetime.utcnow()
    )
    
    db.add(account)
    await db.commit()
    
    return DeveloperAccountResponse.from_orm(account)


# Webhook Routes
@router.post("/webhooks", response_model=WebhookResponse)
async def register_webhook(
    webhook: WebhookRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Register a webhook for plugin events"""
    from ..db.models import PluginWebhook
    import secrets
    
    # Create webhook
    webhook_record = PluginWebhook(
        plugin_id=webhook.plugin_id,
        tenant_id=current_user.get("tenant_id"),
        event_types=webhook.event_types,
        url=webhook.url,
        secret=secrets.token_urlsafe(32)
    )
    
    db.add(webhook_record)
    await db.commit()
    
    return WebhookResponse.from_orm(webhook_record)


@router.get("/webhooks", response_model=List[WebhookResponse])
async def list_webhooks(
    plugin_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List registered webhooks"""
    from sqlalchemy import select
    from ..db.models import PluginWebhook
    
    query = select(PluginWebhook).where(
        PluginWebhook.tenant_id == current_user.get("tenant_id")
    )
    
    if plugin_id:
        query = query.where(PluginWebhook.plugin_id == plugin_id)
    
    result = await db.execute(query)
    webhooks = result.scalars().all()
    
    return [WebhookResponse.from_orm(w) for w in webhooks]


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a webhook"""
    from sqlalchemy import select, update
    from ..db.models import PluginWebhook
    
    result = await db.execute(
        select(PluginWebhook).where(
            PluginWebhook.id == webhook_id,
            PluginWebhook.tenant_id == current_user.get("tenant_id")
        )
    )
    webhook = result.scalar_one_or_none()
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    webhook.active = False
    await db.commit()
    
    return {"message": "Webhook deleted successfully"}


# Admin Routes
@router.get("/admin/health", response_model=Dict[str, Any])
async def get_plugin_system_health(
    plugin_manager: PluginManager = Depends(get_plugin_manager),
    plugin_registry: PluginRegistry = Depends(get_plugin_registry),
    current_user: dict = Depends(get_current_user)
):
    """Get overall plugin system health"""
    if not current_user.get("is_superuser"):
        raise PluginPermissionError("admin", "admin privileges required")
    
    plugin_health = await plugin_manager.get_plugin_health_status()
    registry_stats = plugin_registry.get_plugin_stats()
    
    return {
        "plugins": plugin_health,
        "registry": registry_stats,
        "system": {
            "plugins_loaded": len(plugin_health),
            "plugins_enabled": len([p for p in plugin_health.values() if p.get("enabled")]),
            "plugins_error": len([p for p in plugin_health.values() if p.get("status") == "error"])
        }
    }


# Developer Portal Routes
@router.get("/developer/portal/dashboard", response_model=Dict[str, Any])
async def get_developer_dashboard(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get developer dashboard data including plugin stats and recent activity"""
    from sqlalchemy import select, func
    from ..db.models import Plugin, PluginExecution, PluginReview, DeveloperAccount
    
    # Verify developer account
    developer_result = await db.execute(
        select(DeveloperAccount).where(
            DeveloperAccount.user_id == current_user.get("id")
        )
    )
    developer = developer_result.scalar_one_or_none()
    if not developer:
        raise HTTPException(status_code=404, detail="Developer account not found")
    
    # Get plugins owned by developer
    plugins_result = await db.execute(
        select(Plugin).where(Plugin.developer_id == developer.id)
    )
    plugins = plugins_result.scalars().all()
    
    # Get execution statistics
    plugin_ids = [p.id for p in plugins]
    if plugin_ids:
        exec_stats = await db.execute(
            select(
                func.count(PluginExecution.id).label("total_executions"),
                func.avg(PluginExecution.execution_time).label("avg_execution_time"),
                func.count().filter(PluginExecution.success == True).label("successful_executions"),
                func.count().filter(PluginExecution.success == False).label("failed_executions")
            ).where(PluginExecution.plugin_id.in_(plugin_ids))
        )
        stats = exec_stats.first()
        
        # Get recent reviews
        reviews_result = await db.execute(
            select(PluginReview)
            .where(PluginReview.plugin_id.in_(plugin_ids))
            .order_by(PluginReview.created_at.desc())
            .limit(10)
        )
        recent_reviews = reviews_result.scalars().all()
    else:
        stats = None
        recent_reviews = []
    
    return {
        "developer_info": {
            "id": developer.id,
            "company_name": developer.company_name,
            "website": developer.website,
            "support_email": developer.support_email,
            "verified": developer.verified,
            "created_at": developer.created_at
        },
        "plugin_stats": {
            "total_plugins": len(plugins),
            "active_plugins": len([p for p in plugins if p.status == "enabled"]),
            "total_downloads": sum([p.download_count for p in plugins]),
            "total_executions": stats.total_executions if stats else 0,
            "avg_execution_time": float(stats.avg_execution_time) if stats and stats.avg_execution_time else 0,
            "success_rate": (stats.successful_executions / stats.total_executions * 100) if stats and stats.total_executions > 0 else 0
        },
        "recent_reviews": [
            {
                "plugin_id": r.plugin_id,
                "rating": r.rating,
                "comment": r.comment,
                "created_at": r.created_at
            } for r in recent_reviews
        ],
        "plugins": [
            {
                "id": p.id,
                "name": p.name,
                "version": p.version,
                "status": p.status,
                "downloads": p.download_count,
                "rating": p.rating,
                "last_updated": p.updated_at
            } for p in plugins
        ]
    }


@router.get("/developer/portal/plugins", response_model=List[Dict[str, Any]])
async def get_developer_plugins(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all plugins owned by the developer"""
    from sqlalchemy import select
    from ..db.models import Plugin, DeveloperAccount
    
    # Get developer account
    developer_result = await db.execute(
        select(DeveloperAccount).where(
            DeveloperAccount.user_id == current_user.get("id")
        )
    )
    developer = developer_result.scalar_one_or_none()
    if not developer:
        raise HTTPException(status_code=404, detail="Developer account not found")
    
    # Get plugins
    plugins_result = await db.execute(
        select(Plugin).where(Plugin.developer_id == developer.id)
    )
    plugins = plugins_result.scalars().all()
    
    return [
        {
            "id": p.id,
            "name": p.name,
            "version": p.version,
            "description": p.description,
            "plugin_type": p.plugin_type,
            "status": p.status,
            "download_count": p.download_count,
            "rating": p.rating,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
            "marketplace_status": p.marketplace_status,
            "metadata": p.metadata
        } for p in plugins
    ]


@router.post("/developer/portal/plugins", response_model=Dict[str, str])
async def create_plugin_draft(
    plugin_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new plugin draft"""
    from ..db.models import Plugin, DeveloperAccount
    import uuid
    
    # Get developer account
    developer_result = await db.execute(
        select(DeveloperAccount).where(
            DeveloperAccount.user_id == current_user.get("id")
        )
    )
    developer = developer_result.scalar_one_or_none()
    if not developer:
        raise HTTPException(status_code=404, detail="Developer account not found")
    
    # Create plugin draft
    plugin = Plugin(
        id=str(uuid.uuid4()),
        name=plugin_data.get("name"),
        version="0.1.0",
        description=plugin_data.get("description", ""),
        plugin_type=plugin_data.get("plugin_type"),
        developer_id=developer.id,
        status="draft",
        marketplace_status="draft",
        metadata=plugin_data.get("metadata", {}),
        file_path="",  # Will be set when code is uploaded
        download_count=0,
        rating=0.0
    )
    
    db.add(plugin)
    await db.commit()
    
    return {"message": "Plugin draft created successfully", "plugin_id": plugin.id}


@router.put("/developer/portal/plugins/{plugin_id}", response_model=Dict[str, str])
async def update_plugin_draft(
    plugin_id: str,
    plugin_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a plugin draft"""
    from sqlalchemy import select
    from ..db.models import Plugin, DeveloperAccount
    
    # Get developer account
    developer_result = await db.execute(
        select(DeveloperAccount).where(
            DeveloperAccount.user_id == current_user.get("id")
        )
    )
    developer = developer_result.scalar_one_or_none()
    if not developer:
        raise HTTPException(status_code=404, detail="Developer account not found")
    
    # Get plugin
    plugin_result = await db.execute(
        select(Plugin).where(
            Plugin.id == plugin_id,
            Plugin.developer_id == developer.id
        )
    )
    plugin = plugin_result.scalar_one_or_none()
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    # Update plugin
    if "name" in plugin_data:
        plugin.name = plugin_data["name"]
    if "description" in plugin_data:
        plugin.description = plugin_data["description"]
    if "version" in plugin_data:
        plugin.version = plugin_data["version"]
    if "metadata" in plugin_data:
        plugin.metadata = plugin_data["metadata"]
    
    plugin.updated_at = datetime.utcnow()
    await db.commit()
    
    return {"message": "Plugin updated successfully"}


@router.get("/developer/portal/analytics", response_model=Dict[str, Any])
async def get_plugin_analytics(
    plugin_id: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get analytics data for developer's plugins"""
    from sqlalchemy import select, func
    from datetime import datetime, timedelta
    from ..db.models import Plugin, PluginExecution, PluginReview, DeveloperAccount
    
    # Get developer account
    developer_result = await db.execute(
        select(DeveloperAccount).where(
            DeveloperAccount.user_id == current_user.get("id")
        )
    )
    developer = developer_result.scalar_one_or_none()
    if not developer:
        raise HTTPException(status_code=404, detail="Developer account not found")
    
    # Build query for plugins
    plugin_query = select(Plugin).where(Plugin.developer_id == developer.id)
    if plugin_id:
        plugin_query = plugin_query.where(Plugin.id == plugin_id)
    
    plugins_result = await db.execute(plugin_query)
    plugins = plugins_result.scalars().all()
    plugin_ids = [p.id for p in plugins]
    
    if not plugin_ids:
        return {"message": "No plugins found"}
    
    # Date range for analytics
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Get execution analytics
    exec_analytics = await db.execute(
        select(
            func.date(PluginExecution.created_at).label("date"),
            func.count(PluginExecution.id).label("executions"),
            func.avg(PluginExecution.execution_time).label("avg_time"),
            func.count().filter(PluginExecution.success == True).label("successes"),
            func.count().filter(PluginExecution.success == False).label("failures")
        )
        .where(
            PluginExecution.plugin_id.in_(plugin_ids),
            PluginExecution.created_at >= start_date
        )
        .group_by(func.date(PluginExecution.created_at))
        .order_by(func.date(PluginExecution.created_at))
    )
    
    daily_stats = [
        {
            "date": row.date.isoformat(),
            "executions": row.executions,
            "avg_execution_time": float(row.avg_time) if row.avg_time else 0,
            "success_rate": (row.successes / row.executions * 100) if row.executions > 0 else 0
        }
        for row in exec_analytics
    ]
    
    # Get review analytics
    review_analytics = await db.execute(
        select(
            func.avg(PluginReview.rating).label("avg_rating"),
            func.count(PluginReview.id).label("total_reviews"),
            func.count().filter(PluginReview.rating >= 4).label("positive_reviews")
        )
        .where(
            PluginReview.plugin_id.in_(plugin_ids),
            PluginReview.created_at >= start_date
        )
    )
    
    review_stats = review_analytics.first()
    
    return {
        "period": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
        "overview": {
            "total_plugins": len(plugins),
            "total_downloads": sum([p.download_count for p in plugins]),
            "avg_rating": float(review_stats.avg_rating) if review_stats.avg_rating else 0,
            "total_reviews": review_stats.total_reviews if review_stats.total_reviews else 0,
            "positive_review_rate": (review_stats.positive_reviews / review_stats.total_reviews * 100) if review_stats.total_reviews > 0 else 0
        },
        "daily_analytics": daily_stats,
        "plugin_breakdown": [
            {
                "id": p.id,
                "name": p.name,
                "downloads": p.download_count,
                "rating": p.rating,
                "status": p.status
            } for p in plugins
        ]
    }


@router.get("/developer/portal/documentation", response_model=Dict[str, Any])
async def get_developer_documentation():
    """Get developer documentation and guides"""
    return {
        "getting_started": {
            "title": "Getting Started with Plugin Development",
            "sections": [
                {
                    "title": "Plugin Architecture Overview",
                    "content": "Learn about the MAMS plugin architecture and 12 supported plugin types"
                },
                {
                    "title": "Development Environment Setup",
                    "content": "Set up your development environment for plugin development"
                },
                {
                    "title": "Creating Your First Plugin",
                    "content": "Step-by-step guide to creating a simple processor plugin"
                }
            ]
        },
        "api_reference": {
            "title": "Plugin API Reference",
            "sections": [
                {
                    "title": "Plugin Base Classes",
                    "content": "Documentation for all plugin base classes and interfaces"
                },
                {
                    "title": "Hook System",
                    "content": "How to use the decorator-based hook system"
                },
                {
                    "title": "Event Handling",
                    "content": "Event-driven communication with the core system"
                }
            ]
        },
        "examples": {
            "title": "Plugin Examples",
            "sections": [
                {
                    "title": "Image Processor Plugin",
                    "content": "Complete example of an image processing plugin"
                },
                {
                    "title": "Storage Connector Plugin",
                    "content": "Example storage backend integration"
                },
                {
                    "title": "Workflow Automation Plugin",
                    "content": "Custom workflow step implementation"
                }
            ]
        },
        "best_practices": {
            "title": "Best Practices",
            "sections": [
                {
                    "title": "Security Guidelines",
                    "content": "Security best practices for plugin development"
                },
                {
                    "title": "Performance Optimization",
                    "content": "How to optimize plugin performance"
                },
                {
                    "title": "Error Handling",
                    "content": "Proper error handling and logging"
                }
            ]
        }
    }


@router.post("/developer/portal/validate", response_model=Dict[str, Any])
async def validate_plugin_code(
    plugin_code: Dict[str, str],  # {"main.py": "...", "config.yaml": "..."}
    current_user: dict = Depends(get_current_user)
):
    """Validate plugin code before submission"""
    from ..core.plugin_loader import PluginLoader
    
    validation_results = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "suggestions": []
    }
    
    try:
        # Create temporary plugin loader for validation
        loader = PluginLoader()
        
        # Validate main plugin file
        if "main.py" in plugin_code:
            code_validation = await loader.validate_plugin_code(plugin_code["main.py"])
            if not code_validation["valid"]:
                validation_results["valid"] = False
                validation_results["errors"].extend(code_validation["errors"])
            validation_results["warnings"].extend(code_validation.get("warnings", []))
        
        # Validate configuration
        if "config.yaml" in plugin_code:
            config_validation = await loader.validate_plugin_config(plugin_code["config.yaml"])
            if not config_validation["valid"]:
                validation_results["valid"] = False
                validation_results["errors"].extend(config_validation["errors"])
        
        # Validate plugin manifest
        if "plugin.json" in plugin_code:
            manifest_validation = await loader.validate_plugin_manifest(plugin_code["plugin.json"])
            if not manifest_validation["valid"]:
                validation_results["valid"] = False
                validation_results["errors"].extend(manifest_validation["errors"])
        
        # Add suggestions for improvement
        validation_results["suggestions"] = [
            "Consider adding comprehensive error handling",
            "Add unit tests for your plugin functionality",
            "Include detailed documentation in your plugin metadata",
            "Optimize for performance with large datasets"
        ]
        
    except Exception as e:
        validation_results["valid"] = False
        validation_results["errors"].append(f"Validation error: {str(e)}")
    
    return validation_results


@router.get("/developer/portal/templates", response_model=List[Dict[str, Any]])
async def get_plugin_templates():
    """Get available plugin templates for different plugin types"""
    templates = [
        {
            "id": "processor_basic",
            "name": "Basic Processor Plugin",
            "description": "Simple asset processing plugin template",
            "plugin_type": "processor",
            "files": {
                "main.py": '''from plugin_base import ProcessorPlugin, PluginResult

class BasicProcessorPlugin(ProcessorPlugin):
    async def initialize(self) -> bool:
        self.logger.info("Initializing Basic Processor Plugin")
        return True
    
    async def process_asset(self, asset_id: str, context) -> PluginResult:
        # Your processing logic here
        return PluginResult(success=True, data={"processed": True})
''',
                "plugin.json": '''{
  "metadata": {
    "id": "basic-processor",
    "name": "Basic Processor",
    "version": "1.0.0",
    "description": "Basic asset processor",
    "author": "Your Name"
  },
  "requirements": {
    "python": ">=3.11"
  }
}''',
                "config.yaml": '''enabled: true
settings:
  enable_optimization: true
'''
            }
        },
        {
            "id": "storage_connector",
            "name": "Storage Connector Plugin",
            "description": "Template for storage backend integration",
            "plugin_type": "storage",
            "files": {
                "main.py": '''from plugin_base import StoragePlugin, PluginResult

class StorageConnectorPlugin(StoragePlugin):
    async def initialize(self) -> bool:
        # Initialize storage connection
        return True
    
    async def store_file(self, file_path: str, destination: str, context) -> PluginResult:
        # Store file logic
        return PluginResult(success=True, data={"stored_path": destination})
    
    async def retrieve_file(self, file_path: str, context) -> PluginResult:
        # Retrieve file logic
        return PluginResult(success=True, data={"file_data": "..."})
'''
            }
        }
    ]
    
    return templates


@router.post("/developer/portal/publish", response_model=Dict[str, str])
async def publish_plugin(
    plugin_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Publish a plugin to the marketplace"""
    from sqlalchemy import select
    from ..db.models import Plugin, DeveloperAccount
    
    # Get developer account
    developer_result = await db.execute(
        select(DeveloperAccount).where(
            DeveloperAccount.user_id == current_user.get("id")
        )
    )
    developer = developer_result.scalar_one_or_none()
    if not developer:
        raise HTTPException(status_code=404, detail="Developer account not found")
    
    # Get plugin
    plugin_result = await db.execute(
        select(Plugin).where(
            Plugin.id == plugin_id,
            Plugin.developer_id == developer.id
        )
    )
    plugin = plugin_result.scalar_one_or_none()
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    # Validate plugin is ready for publishing
    if not plugin.file_path:
        raise HTTPException(status_code=400, detail="Plugin code must be uploaded before publishing")
    
    if plugin.marketplace_status == "published":
        raise HTTPException(status_code=400, detail="Plugin is already published")
    
    # Update plugin status
    plugin.marketplace_status = "under_review"
    plugin.status = "pending_approval"
    plugin.updated_at = datetime.utcnow()
    
    await db.commit()
    
    # TODO: Send notification to admin team for review
    
    return {"message": "Plugin submitted for review", "status": "under_review"}