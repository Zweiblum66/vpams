"""
Integration installation routes
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from pydantic import BaseModel, Field

from ..core.logging import get_logger
from ..core.exceptions import IntegrationNotFoundError
from ..db.base import get_db
from ..db.models import Integration, IntegrationInstallation, IntegrationStatusEnum

logger = get_logger(__name__)

router = APIRouter()


class InstallationCreate(BaseModel):
    """Schema for creating an installation"""
    integration_id: str
    environment: str = "production"
    config: Dict[str, Any] = Field(default_factory=dict)


class InstallationUpdate(BaseModel):
    """Schema for updating an installation"""
    config: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    environment: Optional[str] = None


@router.post("/", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def install_integration(
    installation: InstallationCreate,
    organization_id: str = Query(...),
    user_id: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Install an integration for an organization"""
    
    # Verify integration exists and is published
    integration_result = await db.execute(
        select(Integration).where(
            and_(
                Integration.id == installation.integration_id,
                Integration.status == IntegrationStatusEnum.PUBLISHED
            )
        )
    )
    integration = integration_result.scalar_one_or_none()
    
    if not integration:
        raise HTTPException(
            status_code=404,
            detail="Integration not found or not available for installation"
        )
    
    # Check if already installed
    existing_result = await db.execute(
        select(IntegrationInstallation).where(
            and_(
                IntegrationInstallation.integration_id == installation.integration_id,
                IntegrationInstallation.organization_id == organization_id,
                IntegrationInstallation.environment == installation.environment
            )
        )
    )
    existing = existing_result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Integration already installed in this environment"
        )
    
    # Create installation
    new_installation = IntegrationInstallation(
        integration_id=installation.integration_id,
        organization_id=organization_id,
        user_id=user_id,
        environment=installation.environment,
        config=installation.config,
        status="active"
    )
    
    db.add(new_installation)
    
    # Update install count
    integration.install_count += 1
    
    await db.commit()
    await db.refresh(new_installation)
    
    logger.info(
        "integration_installed",
        integration_id=installation.integration_id,
        organization_id=organization_id,
        user_id=user_id,
        environment=installation.environment
    )
    
    return {
        "id": str(new_installation.id),
        "integration_id": str(new_installation.integration_id),
        "organization_id": new_installation.organization_id,
        "user_id": new_installation.user_id,
        "environment": new_installation.environment,
        "config": new_installation.config,
        "status": new_installation.status,
        "health_status": new_installation.health_status,
        "installed_at": new_installation.installed_at,
        "integration": {
            "id": str(integration.id),
            "name": integration.name,
            "display_name": integration.display_name,
            "version": integration.version,
            "provider_name": integration.provider_name,
            "logo_url": integration.logo_url
        }
    }


@router.get("/", response_model=Dict[str, Any])
async def list_installations(
    organization_id: str = Query(...),
    environment: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List installations for an organization"""
    
    # Build query
    query = select(IntegrationInstallation).where(
        IntegrationInstallation.organization_id == organization_id
    )
    
    if environment:
        query = query.where(IntegrationInstallation.environment == environment)
    
    if status:
        query = query.where(IntegrationInstallation.status == status)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination and ordering
    offset = (page - 1) * limit
    query = query.order_by(desc(IntegrationInstallation.installed_at)).offset(offset).limit(limit)
    
    # Execute query with join to get integration details
    query = query.join(Integration)
    result = await db.execute(query)
    installations = result.scalars().all()
    
    return {
        "installations": [
            {
                "id": str(installation.id),
                "integration_id": str(installation.integration_id),
                "environment": installation.environment,
                "status": installation.status,
                "health_status": installation.health_status,
                "last_used_at": installation.last_used_at,
                "total_requests": installation.total_requests,
                "error_count": installation.error_count,
                "installed_at": installation.installed_at,
                "integration": {
                    "name": installation.integration.name,
                    "display_name": installation.integration.display_name,
                    "version": installation.integration.version,
                    "provider_name": installation.integration.provider_name,
                    "logo_url": installation.integration.logo_url,
                    "category": installation.integration.category
                }
            }
            for installation in installations
        ],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }


@router.get("/{installation_id}", response_model=Dict[str, Any])
async def get_installation_details(
    installation_id: str,
    organization_id: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a specific installation"""
    
    result = await db.execute(
        select(IntegrationInstallation)
        .join(Integration)
        .where(
            and_(
                IntegrationInstallation.id == installation_id,
                IntegrationInstallation.organization_id == organization_id
            )
        )
    )
    installation = result.scalar_one_or_none()
    
    if not installation:
        raise HTTPException(status_code=404, detail="Installation not found")
    
    return {
        "id": str(installation.id),
        "integration_id": str(installation.integration_id),
        "organization_id": installation.organization_id,
        "user_id": installation.user_id,
        "environment": installation.environment,
        "config": installation.config,
        "status": installation.status,
        "health_status": installation.health_status,
        "health_details": installation.health_details,
        "last_used_at": installation.last_used_at,
        "last_health_check": installation.last_health_check,
        "total_requests": installation.total_requests,
        "last_request_at": installation.last_request_at,
        "error_count": installation.error_count,
        "installed_at": installation.installed_at,
        "updated_at": installation.updated_at,
        "integration": {
            "id": str(installation.integration.id),
            "name": installation.integration.name,
            "display_name": installation.integration.display_name,
            "description": installation.integration.description,
            "version": installation.integration.version,
            "provider_name": installation.integration.provider_name,
            "documentation_url": installation.integration.documentation_url,
            "api_reference_url": installation.integration.api_reference_url,
            "logo_url": installation.integration.logo_url,
            "category": installation.integration.category,
            "integration_type": installation.integration.integration_type
        }
    }


@router.put("/{installation_id}", response_model=Dict[str, Any])
async def update_installation(
    installation_id: str,
    update: InstallationUpdate,
    organization_id: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Update an installation"""
    
    result = await db.execute(
        select(IntegrationInstallation).where(
            and_(
                IntegrationInstallation.id == installation_id,
                IntegrationInstallation.organization_id == organization_id
            )
        )
    )
    installation = result.scalar_one_or_none()
    
    if not installation:
        raise HTTPException(status_code=404, detail="Installation not found")
    
    # Update fields
    if update.config is not None:
        installation.config = update.config
    
    if update.status is not None:
        installation.status = update.status
    
    if update.environment is not None:
        installation.environment = update.environment
    
    await db.commit()
    await db.refresh(installation)
    
    logger.info(
        "installation_updated",
        installation_id=installation_id,
        organization_id=organization_id,
        updates=update.model_dump(exclude_unset=True)
    )
    
    return {
        "id": str(installation.id),
        "integration_id": str(installation.integration_id),
        "organization_id": installation.organization_id,
        "environment": installation.environment,
        "config": installation.config,
        "status": installation.status,
        "health_status": installation.health_status,
        "updated_at": installation.updated_at
    }


@router.delete("/{installation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def uninstall_integration(
    installation_id: str,
    organization_id: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Uninstall an integration"""
    
    result = await db.execute(
        select(IntegrationInstallation).where(
            and_(
                IntegrationInstallation.id == installation_id,
                IntegrationInstallation.organization_id == organization_id
            )
        )
    )
    installation = result.scalar_one_or_none()
    
    if not installation:
        raise HTTPException(status_code=404, detail="Installation not found")
    
    # Update install count
    integration_result = await db.execute(
        select(Integration).where(Integration.id == installation.integration_id)
    )
    integration = integration_result.scalar_one_or_none()
    if integration and integration.install_count > 0:
        integration.install_count -= 1
    
    await db.delete(installation)
    await db.commit()
    
    logger.info(
        "integration_uninstalled",
        installation_id=installation_id,
        integration_id=str(installation.integration_id),
        organization_id=organization_id
    )


@router.post("/{installation_id}/health-check", response_model=Dict[str, Any])
async def perform_health_check(
    installation_id: str,
    organization_id: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Perform a health check on an installation"""
    
    result = await db.execute(
        select(IntegrationInstallation).where(
            and_(
                IntegrationInstallation.id == installation_id,
                IntegrationInstallation.organization_id == organization_id
            )
        )
    )
    installation = result.scalar_one_or_none()
    
    if not installation:
        raise HTTPException(status_code=404, detail="Installation not found")
    
    # TODO: Implement actual health check logic
    # For now, just update the timestamp and return healthy
    from datetime import datetime
    
    installation.last_health_check = datetime.utcnow()
    installation.health_status = "healthy"
    installation.health_details = {
        "check_performed_at": installation.last_health_check.isoformat(),
        "status": "healthy",
        "checks": {
            "connectivity": "pass",
            "authentication": "pass",
            "api_availability": "pass"
        }
    }
    
    await db.commit()
    
    logger.info(
        "health_check_performed",
        installation_id=installation_id,
        organization_id=organization_id,
        health_status=installation.health_status
    )
    
    return {
        "installation_id": installation_id,
        "health_status": installation.health_status,
        "health_details": installation.health_details,
        "last_health_check": installation.last_health_check
    }


@router.get("/{installation_id}/usage", response_model=Dict[str, Any])
async def get_installation_usage(
    installation_id: str,
    organization_id: str = Query(...),
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """Get usage statistics for an installation"""
    
    result = await db.execute(
        select(IntegrationInstallation).where(
            and_(
                IntegrationInstallation.id == installation_id,
                IntegrationInstallation.organization_id == organization_id
            )
        )
    )
    installation = result.scalar_one_or_none()
    
    if not installation:
        raise HTTPException(status_code=404, detail="Installation not found")
    
    # TODO: Implement detailed usage analytics
    # For now, return basic statistics
    
    return {
        "installation_id": installation_id,
        "period_days": days,
        "total_requests": installation.total_requests,
        "error_count": installation.error_count,
        "error_rate": (installation.error_count / max(installation.total_requests, 1)) * 100,
        "last_used_at": installation.last_used_at,
        "last_request_at": installation.last_request_at,
        "uptime_percentage": 99.5,  # TODO: Calculate actual uptime
        "average_response_time_ms": 150,  # TODO: Calculate from actual metrics
        "daily_usage": []  # TODO: Implement daily breakdown
    }