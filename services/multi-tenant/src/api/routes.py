"""
API routes for Multi-Tenant Service.

Handles tenant management, domain configuration, and tenant-specific operations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from ..core.deps import get_db, get_current_user, get_tenant_context
from ..core.auth import require_permissions
from ..models.schemas import (
    TenantCreate, TenantUpdate, TenantResponse, TenantStatus,
    DomainInfo, DomainVerificationMethod, CustomDomainRequest,
    TenantConfig, TenantConfigUpdate, TenantUsageResponse,
    SubscriptionPlan, TenantContext, User
)
from ..services.tenant_manager import TenantManager
from ..services.domain_manager import DomainManager
from ..services.tenant_resolver import TenantResolver
from ..services.config_manager import ConfigurationManager


logger = structlog.get_logger()

# Initialize router
router = APIRouter(prefix="/api/v1", tags=["multi-tenant"])

# Service instances (would be dependency injected in production)
tenant_manager = TenantManager()
domain_manager = DomainManager()
tenant_resolver = TenantResolver()
config_manager = ConfigurationManager()


# Tenant Management Routes

@router.post("/tenants", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant: TenantCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["system:manage_tenants"]))
):
    """
    Create a new tenant.
    
    Requires system:manage_tenants permission.
    """
    try:
        # Create tenant
        new_tenant = await tenant_manager.create_tenant(
            name=tenant.name,
            subdomain=tenant.subdomain,
            admin_email=tenant.admin_email,
            plan=tenant.plan or SubscriptionPlan.STANDARD,
            metadata=tenant.metadata
        )
        
        # Queue background provisioning tasks
        background_tasks.add_task(
            tenant_manager.provision_tenant_resources,
            new_tenant.tenant_id
        )
        
        logger.info(
            "Tenant created",
            tenant_id=new_tenant.tenant_id,
            subdomain=tenant.subdomain,
            user_id=current_user.user_id
        )
        
        return new_tenant
        
    except Exception as e:
        logger.error("Failed to create tenant", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/tenants", response_model=List[TenantResponse])
async def list_tenants(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[TenantStatus] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["system:view_tenants"]))
):
    """
    List all tenants.
    
    Requires system:view_tenants permission.
    """
    try:
        tenants = await tenant_manager.list_tenants(
            skip=skip,
            limit=limit,
            status=status
        )
        
        return [TenantResponse.from_orm(t) for t in tenants]
        
    except Exception as e:
        logger.error("Failed to list tenants", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/tenants/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    Get tenant details.
    
    Users can only access their own tenant unless they have system permissions.
    """
    try:
        # Check access
        if tenant_context.tenant_id != tenant_id:
            # Need system permission to view other tenants
            if not current_user.has_permission("system:view_tenants"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to tenant"
                )
        
        tenant = await tenant_manager.get_tenant(tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        return tenant
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get tenant", tenant_id=tenant_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.put("/tenants/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    update: TenantUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    Update tenant details.
    
    Tenant admins can update their own tenant, system admins can update any tenant.
    """
    try:
        # Check access
        if tenant_context.tenant_id != tenant_id:
            if not current_user.has_permission("system:manage_tenants"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to tenant"
                )
        else:
            # Tenant admin updating their own tenant
            if not current_user.has_permission("tenant:manage"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
        
        updated_tenant = await tenant_manager.update_tenant(tenant_id, update)
        
        logger.info(
            "Tenant updated",
            tenant_id=tenant_id,
            user_id=current_user.user_id
        )
        
        return updated_tenant
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update tenant", tenant_id=tenant_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/tenants/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["system:delete_tenants"]))
):
    """
    Delete a tenant.
    
    Requires system:delete_tenants permission.
    This will queue background cleanup of all tenant resources.
    """
    try:
        # Suspend tenant first
        await tenant_manager.suspend_tenant(
            tenant_id,
            reason="Pending deletion",
            suspended_by=current_user.user_id
        )
        
        # Queue deletion in background
        background_tasks.add_task(
            tenant_manager.delete_tenant,
            tenant_id
        )
        
        logger.info(
            "Tenant deletion queued",
            tenant_id=tenant_id,
            user_id=current_user.user_id
        )
        
    except Exception as e:
        logger.error("Failed to delete tenant", tenant_id=tenant_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Domain Management Routes

@router.post("/tenants/{tenant_id}/domains", response_model=DomainInfo, status_code=status.HTTP_201_CREATED)
async def add_custom_domain(
    tenant_id: str,
    domain_request: CustomDomainRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    Add a custom domain to tenant.
    
    Requires tenant:manage permission for the tenant.
    """
    try:
        # Check access
        if tenant_context.tenant_id != tenant_id:
            if not current_user.has_permission("system:manage_tenants"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to tenant"
                )
        elif not current_user.has_permission("tenant:manage"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        # Configure domain
        domain_info = await domain_manager.configure_domain(
            tenant_id=tenant_id,
            domain=domain_request.domain,
            auto_verify=domain_request.auto_verify,
            auto_ssl=domain_request.auto_ssl
        )
        
        logger.info(
            "Custom domain added",
            tenant_id=tenant_id,
            domain=domain_request.domain,
            user_id=current_user.user_id
        )
        
        return domain_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to add custom domain", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/tenants/{tenant_id}/domains", response_model=List[DomainInfo])
async def list_tenant_domains(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    List all domains for a tenant.
    """
    try:
        # Check access
        if tenant_context.tenant_id != tenant_id:
            if not current_user.has_permission("system:view_tenants"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to tenant"
                )
        
        domains = await domain_manager.get_tenant_domains(tenant_id)
        
        return domains
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list tenant domains", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/tenants/{tenant_id}/domains/{domain}/verify", response_model=Dict[str, Any])
async def verify_domain(
    tenant_id: str,
    domain: str,
    method: DomainVerificationMethod = Query(DomainVerificationMethod.DNS),
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    Verify domain ownership.
    """
    try:
        # Check access
        if tenant_context.tenant_id != tenant_id:
            if not current_user.has_permission("system:manage_tenants"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to tenant"
                )
        elif not current_user.has_permission("tenant:manage"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        # Verify domain
        verified = await domain_manager.verify_domain(
            tenant_id=tenant_id,
            domain=domain,
            method=method
        )
        
        if verified:
            logger.info(
                "Domain verified",
                tenant_id=tenant_id,
                domain=domain,
                method=method.value,
                user_id=current_user.user_id
            )
            
            return {
                "verified": True,
                "message": "Domain verified successfully"
            }
        else:
            return {
                "verified": False,
                "message": "Domain verification failed. Please check DNS records."
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to verify domain", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/tenants/{tenant_id}/domains/{domain}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_domain(
    tenant_id: str,
    domain: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    Remove a custom domain from tenant.
    """
    try:
        # Check access
        if tenant_context.tenant_id != tenant_id:
            if not current_user.has_permission("system:manage_tenants"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to tenant"
                )
        elif not current_user.has_permission("tenant:manage"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        await domain_manager.remove_domain(tenant_id, domain)
        
        logger.info(
            "Domain removed",
            tenant_id=tenant_id,
            domain=domain,
            user_id=current_user.user_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to remove domain", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Tenant Configuration Routes

@router.get("/tenants/{tenant_id}/config", response_model=TenantConfig)
async def get_tenant_config(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    Get tenant configuration.
    """
    try:
        # Check access
        if tenant_context.tenant_id != tenant_id:
            if not current_user.has_permission("system:view_tenants"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to tenant"
                )
        
        config = await config_manager.get_config(tenant_id)
        return config
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get tenant config", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.put("/tenants/{tenant_id}/config", response_model=TenantConfig)
async def update_tenant_config(
    tenant_id: str,
    config_update: TenantConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    Update tenant configuration.
    """
    try:
        # Check access
        if tenant_context.tenant_id != tenant_id:
            if not current_user.has_permission("system:manage_tenants"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to tenant"
                )
        elif not current_user.has_permission("tenant:manage"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        updated_config = await config_manager.update_config(
            tenant_id,
            config_update
        )
        
        logger.info(
            "Tenant config updated",
            tenant_id=tenant_id,
            user_id=current_user.user_id
        )
        
        return updated_config
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update tenant config", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Tenant Usage and Metrics Routes

@router.get("/tenants/{tenant_id}/usage", response_model=TenantUsageResponse)
async def get_tenant_usage(
    tenant_id: str,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    Get tenant usage statistics.
    """
    try:
        # Check access
        if tenant_context.tenant_id != tenant_id:
            if not current_user.has_permission("system:view_tenants"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to tenant"
                )
        
        usage = await tenant_manager.get_tenant_usage(
            tenant_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return usage
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get tenant usage", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Configuration Template Routes

@router.get("/config/templates", response_model=List[Dict[str, Any]])
async def list_config_templates(
    category: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user)
):
    """
    List available configuration templates.
    """
    try:
        templates = await config_manager.get_templates(category=category)
        
        return [
            {
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "is_default": t.is_default,
                "tags": t.tags
            }
            for t in templates
        ]
        
    except Exception as e:
        logger.error("Failed to list templates", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/tenants/{tenant_id}/config/apply-template", response_model=TenantConfig)
async def apply_config_template(
    tenant_id: str,
    template_name: str = Query(...),
    merge: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    Apply configuration template to tenant.
    """
    try:
        # Check access
        if tenant_context.tenant_id != tenant_id:
            if not current_user.has_permission("system:manage_tenants"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to tenant"
                )
        elif not current_user.has_permission("tenant:manage"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        config = await config_manager.apply_template(
            tenant_id,
            template_name,
            merge=merge
        )
        
        logger.info(
            "Template applied",
            tenant_id=tenant_id,
            template=template_name,
            merge=merge,
            user_id=current_user.user_id
        )
        
        return config
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to apply template", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/tenants/{tenant_id}/config/rollback", response_model=TenantConfig)
async def rollback_config(
    tenant_id: str,
    version: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    Rollback configuration to previous version.
    """
    try:
        # Check access - only tenant admins or system admins
        if tenant_context.tenant_id != tenant_id:
            if not current_user.has_permission("system:manage_tenants"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to tenant"
                )
        elif not current_user.has_permission("tenant:manage"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        config = await config_manager.rollback_config(tenant_id, version)
        
        logger.info(
            "Configuration rolled back",
            tenant_id=tenant_id,
            to_version=config.version,
            user_id=current_user.user_id
        )
        
        return config
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to rollback config", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/tenants/{tenant_id}/config/diff", response_model=Dict[str, Any])
async def get_config_diff(
    tenant_id: str,
    version1: Optional[int] = Query(None),
    version2: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    Get configuration differences between versions.
    """
    try:
        # Check access
        if tenant_context.tenant_id != tenant_id:
            if not current_user.has_permission("system:view_tenants"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to tenant"
                )
        
        diff = await config_manager.get_config_diff(
            tenant_id,
            version1=version1,
            version2=version2
        )
        
        return diff
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get config diff", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/tenants/{tenant_id}/config/export", response_model=Dict[str, Any])
async def export_config(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    Export tenant configuration.
    """
    try:
        # Check access
        if tenant_context.tenant_id != tenant_id:
            if not current_user.has_permission("system:view_tenants"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to tenant"
                )
        
        config_data = await config_manager.export_config(tenant_id)
        
        logger.info(
            "Configuration exported",
            tenant_id=tenant_id,
            user_id=current_user.user_id
        )
        
        return config_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to export config", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/tenants/{tenant_id}/config/import", response_model=TenantConfig)
async def import_config(
    tenant_id: str,
    config_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    Import configuration from JSON.
    """
    try:
        # Check access - only tenant admins or system admins
        if tenant_context.tenant_id != tenant_id:
            if not current_user.has_permission("system:manage_tenants"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to tenant"
                )
        elif not current_user.has_permission("tenant:manage"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        config = await config_manager.import_config(tenant_id, config_data)
        
        logger.info(
            "Configuration imported",
            tenant_id=tenant_id,
            user_id=current_user.user_id
        )
        
        return config
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to import config", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Service Health Routes

@router.get("/health", response_model=Dict[str, Any])
async def health_check():
    """Check service health."""
    try:
        # Get service statistics
        tenant_stats = await tenant_manager.get_statistics()
        domain_stats = await domain_manager.get_statistics()
        config_stats = await config_manager.get_statistics()
        
        return {
            "status": "healthy",
            "service": "multi-tenant",
            "tenant_manager": tenant_stats,
            "domain_manager": domain_stats,
            "config_manager": config_stats
        }
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "service": "multi-tenant",
            "error": str(e)
        }


# Service Initialization

@router.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    try:
        await tenant_manager.initialize()
        await domain_manager.initialize()
        await tenant_resolver.initialize()
        await config_manager.initialize()
        
        logger.info("Multi-tenant service initialized")
        
    except Exception as e:
        logger.error("Failed to initialize multi-tenant service", error=str(e))
        raise


@router.on_event("shutdown")
async def shutdown_event():
    """Cleanup services on shutdown."""
    try:
        await tenant_manager.cleanup()
        await domain_manager.cleanup()
        await tenant_resolver.cleanup()
        await config_manager.cleanup()
        
        logger.info("Multi-tenant service shutdown complete")
        
    except Exception as e:
        logger.error("Error during shutdown", error=str(e))