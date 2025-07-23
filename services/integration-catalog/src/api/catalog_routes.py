"""
Integration catalog routes
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_

from ..core.logging import get_logger
from ..core.exceptions import IntegrationNotFoundError
from ..db.base import get_db
from ..db.models import (
    Integration, IntegrationCategory, IntegrationEndpoint, 
    IntegrationReview, IntegrationTypeEnum, IntegrationStatusEnum
)

logger = get_logger(__name__)

router = APIRouter()


@router.get("/", response_model=Dict[str, Any])
async def list_integrations(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    integration_type: Optional[IntegrationTypeEnum] = Query(None),
    status: Optional[IntegrationStatusEnum] = Query(None),
    is_featured: Optional[bool] = Query(None),
    is_free: Optional[bool] = Query(None),
    provider: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    sort_by: str = Query("name", regex="^(name|rating|install_count|created_at|updated_at)$"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db)
):
    """List integrations with filtering, search, and pagination"""
    
    # Build base query
    query = select(Integration).where(Integration.status == IntegrationStatusEnum.PUBLISHED)
    
    # Apply filters
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Integration.name.ilike(search_term),
                Integration.display_name.ilike(search_term),
                Integration.description.ilike(search_term),
                Integration.provider_name.ilike(search_term)
            )
        )
    
    if category:
        query = query.where(Integration.category == category)
    
    if integration_type:
        query = query.where(Integration.integration_type == integration_type)
    
    if status:
        query = query.where(Integration.status == status)
    
    if is_featured is not None:
        query = query.where(Integration.is_featured == is_featured)
    
    if is_free is not None:
        query = query.where(Integration.is_free == is_free)
    
    if provider:
        query = query.where(Integration.provider_name.ilike(f"%{provider}%"))
    
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",")]
        query = query.where(Integration.tags.op("&&")(tag_list))
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply sorting
    sort_column = getattr(Integration, sort_by)
    if sort_order == "desc":
        sort_column = desc(sort_column)
    
    # Apply pagination
    offset = (page - 1) * limit
    query = query.order_by(sort_column).offset(offset).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    integrations = result.scalars().all()
    
    return {
        "integrations": [
            {
                "id": str(integration.id),
                "name": integration.name,
                "display_name": integration.display_name,
                "description": integration.short_description or integration.description,
                "version": integration.version,
                "integration_type": integration.integration_type,
                "category": integration.category,
                "provider_name": integration.provider_name,
                "status": integration.status,
                "is_featured": integration.is_featured,
                "is_verified": integration.is_verified,
                "is_free": integration.is_free,
                "rating": float(integration.rating),
                "review_count": integration.review_count,
                "install_count": integration.install_count,
                "logo_url": integration.logo_url,
                "tags": integration.tags,
                "pricing_model": integration.pricing_model,
                "setup_complexity": integration.setup_complexity,
                "created_at": integration.created_at,
                "updated_at": integration.updated_at
            }
            for integration in integrations
        ],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        },
        "filters": {
            "search": search,
            "category": category,
            "integration_type": integration_type,
            "status": status,
            "is_featured": is_featured,
            "is_free": is_free,
            "provider": provider,
            "tags": tags
        }
    }


@router.get("/{integration_id}", response_model=Dict[str, Any])
async def get_integration_details(
    integration_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a specific integration"""
    
    # Get integration
    result = await db.execute(
        select(Integration).where(Integration.id == integration_id)
    )
    integration = result.scalar_one_or_none()
    
    if not integration:
        raise IntegrationNotFoundError(integration_id)
    
    # Get endpoints
    endpoints_result = await db.execute(
        select(IntegrationEndpoint)
        .where(IntegrationEndpoint.integration_id == integration_id)
        .order_by(IntegrationEndpoint.path, IntegrationEndpoint.method)
    )
    endpoints = endpoints_result.scalars().all()
    
    # Get recent reviews
    reviews_result = await db.execute(
        select(IntegrationReview)
        .where(
            and_(
                IntegrationReview.integration_id == integration_id,
                IntegrationReview.is_approved == True
            )
        )
        .order_by(desc(IntegrationReview.created_at))
        .limit(10)
    )
    reviews = reviews_result.scalars().all()
    
    return {
        "id": str(integration.id),
        "name": integration.name,
        "display_name": integration.display_name,
        "description": integration.description,
        "short_description": integration.short_description,
        "version": integration.version,
        "integration_type": integration.integration_type,
        "category": integration.category,
        "subcategory": integration.subcategory,
        "provider_name": integration.provider_name,
        "provider_website": integration.provider_website,
        "provider_support_url": integration.provider_support_url,
        "status": integration.status,
        "is_featured": integration.is_featured,
        "is_verified": integration.is_verified,
        "is_free": integration.is_free,
        "protocol": integration.protocol,
        "base_url": integration.base_url,
        "documentation_url": integration.documentation_url,
        "api_reference_url": integration.api_reference_url,
        "auth_type": integration.auth_type,
        "auth_config": integration.auth_config,
        "supported_operations": integration.supported_operations,
        "data_formats": integration.data_formats,
        "rate_limits": integration.rate_limits,
        "setup_complexity": integration.setup_complexity,
        "setup_time_minutes": integration.setup_time_minutes,
        "prerequisites": integration.prerequisites,
        "tags": integration.tags,
        "use_cases": integration.use_cases,
        "industries": integration.industries,
        "logo_url": integration.logo_url,
        "banner_url": integration.banner_url,
        "screenshots": integration.screenshots,
        "video_url": integration.video_url,
        "pricing_model": integration.pricing_model,
        "pricing_details": integration.pricing_details,
        "rating": float(integration.rating),
        "review_count": integration.review_count,
        "install_count": integration.install_count,
        "openapi_spec": integration.openapi_spec,
        "endpoints": [
            {
                "id": str(endpoint.id),
                "path": endpoint.path,
                "method": endpoint.method,
                "operation_id": endpoint.operation_id,
                "summary": endpoint.summary,
                "description": endpoint.description,
                "parameters": endpoint.parameters,
                "request_body": endpoint.request_body,
                "responses": endpoint.responses,
                "requires_auth": endpoint.requires_auth,
                "rate_limit": endpoint.rate_limit,
                "examples": endpoint.examples,
                "tags": endpoint.tags,
                "is_deprecated": endpoint.is_deprecated
            }
            for endpoint in endpoints
        ],
        "recent_reviews": [
            {
                "id": str(review.id),
                "rating": review.rating,
                "title": review.title,
                "comment": review.comment,
                "ease_of_use": review.ease_of_use,
                "documentation_quality": review.documentation_quality,
                "support_quality": review.support_quality,
                "reliability": review.reliability,
                "verified_installation": review.verified_installation,
                "helpful_count": review.helpful_count,
                "created_at": review.created_at
            }
            for review in reviews
        ],
        "published_at": integration.published_at,
        "created_at": integration.created_at,
        "updated_at": integration.updated_at
    }


@router.get("/categories", response_model=List[Dict[str, Any]])
async def get_categories(
    db: AsyncSession = Depends(get_db)
):
    """Get all integration categories"""
    
    result = await db.execute(
        select(IntegrationCategory)
        .where(IntegrationCategory.is_active == True)
        .order_by(IntegrationCategory.display_order, IntegrationCategory.name)
    )
    categories = result.scalars().all()
    
    return [
        {
            "id": str(category.id),
            "name": category.name,
            "slug": category.slug,
            "display_name": category.display_name,
            "description": category.description,
            "parent_id": str(category.parent_id) if category.parent_id else None,
            "icon": category.icon,
            "color": category.color,
            "integration_count": category.integration_count,
            "display_order": category.display_order
        }
        for category in categories
    ]


@router.get("/featured", response_model=List[Dict[str, Any]])
async def get_featured_integrations(
    limit: int = Query(12, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get featured integrations"""
    
    result = await db.execute(
        select(Integration)
        .where(
            and_(
                Integration.status == IntegrationStatusEnum.PUBLISHED,
                Integration.is_featured == True
            )
        )
        .order_by(desc(Integration.rating), desc(Integration.install_count))
        .limit(limit)
    )
    integrations = result.scalars().all()
    
    return [
        {
            "id": str(integration.id),
            "name": integration.name,
            "display_name": integration.display_name,
            "description": integration.short_description,
            "provider_name": integration.provider_name,
            "category": integration.category,
            "integration_type": integration.integration_type,
            "rating": float(integration.rating),
            "install_count": integration.install_count,
            "logo_url": integration.logo_url,
            "banner_url": integration.banner_url,
            "is_free": integration.is_free,
            "pricing_model": integration.pricing_model,
            "setup_complexity": integration.setup_complexity
        }
        for integration in integrations
    ]


@router.get("/popular", response_model=List[Dict[str, Any]])
async def get_popular_integrations(
    limit: int = Query(12, ge=1, le=50),
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """Get popular integrations based on install count and ratings"""
    
    result = await db.execute(
        select(Integration)
        .where(Integration.status == IntegrationStatusEnum.PUBLISHED)
        .order_by(
            desc(Integration.install_count),
            desc(Integration.rating),
            desc(Integration.review_count)
        )
        .limit(limit)
    )
    integrations = result.scalars().all()
    
    return [
        {
            "id": str(integration.id),
            "name": integration.name,
            "display_name": integration.display_name,
            "description": integration.short_description,
            "provider_name": integration.provider_name,
            "category": integration.category,
            "rating": float(integration.rating),
            "review_count": integration.review_count,
            "install_count": integration.install_count,
            "logo_url": integration.logo_url,
            "is_free": integration.is_free,
            "tags": integration.tags[:5]  # First 5 tags
        }
        for integration in integrations
    ]


@router.get("/search/suggestions", response_model=List[str])
async def get_search_suggestions(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=20),
    db: AsyncSession = Depends(get_db)
):
    """Get search suggestions based on integration names and providers"""
    
    search_term = f"%{q}%"
    
    # Get name suggestions
    name_results = await db.execute(
        select(Integration.name)
        .where(
            and_(
                Integration.status == IntegrationStatusEnum.PUBLISHED,
                Integration.name.ilike(search_term)
            )
        )
        .limit(limit // 2)
    )
    names = [row[0] for row in name_results.all()]
    
    # Get provider suggestions
    provider_results = await db.execute(
        select(Integration.provider_name)
        .where(
            and_(
                Integration.status == IntegrationStatusEnum.PUBLISHED,
                Integration.provider_name.ilike(search_term)
            )
        )
        .distinct()
        .limit(limit // 2)
    )
    providers = [row[0] for row in provider_results.all()]
    
    # Combine and deduplicate
    suggestions = list(set(names + providers))
    return suggestions[:limit]


@router.get("/stats", response_model=Dict[str, Any])
async def get_catalog_stats(
    db: AsyncSession = Depends(get_db)
):
    """Get overall catalog statistics"""
    
    # Total integrations
    total_integrations = await db.execute(
        select(func.count(Integration.id))
        .where(Integration.status == IntegrationStatusEnum.PUBLISHED)
    )
    
    # By category
    category_stats = await db.execute(
        select(
            Integration.category,
            func.count(Integration.id).label("count")
        )
        .where(Integration.status == IntegrationStatusEnum.PUBLISHED)
        .group_by(Integration.category)
        .order_by(desc(func.count(Integration.id)))
    )
    
    # By type
    type_stats = await db.execute(
        select(
            Integration.integration_type,
            func.count(Integration.id).label("count")
        )
        .where(Integration.status == IntegrationStatusEnum.PUBLISHED)
        .group_by(Integration.integration_type)
        .order_by(desc(func.count(Integration.id)))
    )
    
    # By pricing
    pricing_stats = await db.execute(
        select(
            Integration.is_free,
            func.count(Integration.id).label("count")
        )
        .where(Integration.status == IntegrationStatusEnum.PUBLISHED)
        .group_by(Integration.is_free)
    )
    
    # Top providers
    provider_stats = await db.execute(
        select(
            Integration.provider_name,
            func.count(Integration.id).label("count")
        )
        .where(Integration.status == IntegrationStatusEnum.PUBLISHED)
        .group_by(Integration.provider_name)
        .order_by(desc(func.count(Integration.id)))
        .limit(10)
    )
    
    return {
        "total_integrations": total_integrations.scalar() or 0,
        "by_category": {row.category: row.count for row in category_stats.all()},
        "by_type": {row.integration_type: row.count for row in type_stats.all()},
        "by_pricing": {
            "free": next((row.count for row in pricing_stats.all() if row.is_free), 0),
            "paid": next((row.count for row in pricing_stats.all() if not row.is_free), 0)
        },
        "top_providers": [
            {"name": row.provider_name, "count": row.count}
            for row in provider_stats.all()
        ]
    }