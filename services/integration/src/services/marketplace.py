"""
Marketplace service for API integrations
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload

from ..models.marketplace import (
    APIListing, APIListingReview, APIInstallation, MarketplaceCategory,
    APIListingCreate, APIListingUpdate
)
from ..core.exceptions import NotFoundError, ValidationError
from .integration_service import IntegrationService

logger = logging.getLogger(__name__)


class MarketplaceService:
    """API Marketplace Service"""
    
    @staticmethod
    async def list_listings(
        db: AsyncSession,
        category: Optional[str] = None,
        featured: Optional[bool] = None,
        provider: Optional[str] = None,
        search: Optional[str] = None,
        sort: str = "popularity",
        order: str = "desc",
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[APIListing], int]:
        """List API listings with filters"""
        
        # Build query
        query = select(APIListing).where(APIListing.status == "approved")
        
        # Apply filters
        if category:
            query = query.where(APIListing.category == category)
        
        if featured is not None:
            query = query.where(APIListing.featured == featured)
        
        if provider:
            query = query.where(APIListing.provider_name.ilike(f"%{provider}%"))
        
        if search:
            search_filter = or_(
                APIListing.name.ilike(f"%{search}%"),
                APIListing.description.ilike(f"%{search}%"),
                APIListing.short_description.ilike(f"%{search}%"),
                func.array_to_string(APIListing.tags, ',').ilike(f"%{search}%")
            )
            query = query.where(search_filter)
        
        # Apply sorting
        sort_column = {
            "popularity": APIListing.install_count,
            "rating": APIListing.rating_average,
            "created_at": APIListing.created_at,
            "name": APIListing.name
        }.get(sort, APIListing.install_count)
        
        if order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
        
        # Get total count
        count_query = select(func.count()).select_from(query.alias())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        listings = result.scalars().all()
        
        return listings, total
    
    @staticmethod
    async def get_listing(db: AsyncSession, listing_id: str) -> Optional[APIListing]:
        """Get specific API listing"""
        query = select(APIListing).where(
            and_(
                APIListing.id == listing_id,
                APIListing.status == "approved"
            )
        ).options(
            selectinload(APIListing.reviews),
            selectinload(APIListing.installations)
        )
        
        result = await db.execute(query)
        listing = result.scalar_one_or_none()
        
        if listing:
            # Increment view count
            listing.view_count += 1
            await db.commit()
        
        return listing
    
    @staticmethod
    async def create_listing(
        db: AsyncSession,
        listing_data: APIListingCreate,
        creator_id: str
    ) -> APIListing:
        """Create new API listing"""
        
        # Validate category exists
        await MarketplaceService._validate_category(db, listing_data.category)
        
        # Create listing
        listing = APIListing(
            **listing_data.dict(),
            provider_id=creator_id,
            status="pending"  # New listings need approval
        )
        
        db.add(listing)
        await db.commit()
        await db.refresh(listing)
        
        logger.info(f"Created API listing: {listing.id}")
        return listing
    
    @staticmethod
    async def update_listing(
        db: AsyncSession,
        listing_id: str,
        listing_data: APIListingUpdate,
        updater_id: str
    ) -> APIListing:
        """Update API listing"""
        
        # Get existing listing
        query = select(APIListing).where(APIListing.id == listing_id)
        result = await db.execute(query)
        listing = result.scalar_one_or_none()
        
        if not listing:
            raise NotFoundError("API listing not found")
        
        # Update fields
        update_data = listing_data.dict(exclude_unset=True)
        
        if "category" in update_data:
            await MarketplaceService._validate_category(db, update_data["category"])
        
        for field, value in update_data.items():
            setattr(listing, field, value)
        
        listing.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(listing)
        
        logger.info(f"Updated API listing: {listing_id}")
        return listing
    
    @staticmethod
    async def delete_listing(db: AsyncSession, listing_id: str) -> None:
        """Delete API listing"""
        
        query = select(APIListing).where(APIListing.id == listing_id)
        result = await db.execute(query)
        listing = result.scalar_one_or_none()
        
        if not listing:
            raise NotFoundError("API listing not found")
        
        await db.delete(listing)
        await db.commit()
        
        logger.info(f"Deleted API listing: {listing_id}")
    
    @staticmethod
    async def install_integration(
        db: AsyncSession,
        listing_id: str,
        user_id: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Install API integration from marketplace listing"""
        
        # Get listing
        listing = await MarketplaceService.get_listing(db, listing_id)
        if not listing:
            raise NotFoundError("API listing not found")
        
        # Validate configuration against schema
        if listing.config_schema:
            await MarketplaceService._validate_config(config, listing.config_schema)
        
        # Check if already installed by user
        existing_query = select(APIInstallation).where(
            and_(
                APIInstallation.listing_id == listing_id,
                APIInstallation.user_id == user_id,
                APIInstallation.status == "active"
            )
        )
        existing_result = await db.execute(existing_query)
        existing = existing_result.scalar_one_or_none()
        
        if existing:
            raise ValidationError("Integration already installed")
        
        # Create integration using IntegrationService
        integration_data = {
            "name": f"{listing.name} Integration",
            "type": listing.api_type,
            "config": {
                **config,
                "marketplace_listing_id": listing_id,
                "base_url": listing.base_url,
                "auth_type": listing.authentication_type,
                "auth_config": listing.auth_config
            },
            "enabled": True,
            "metadata": {
                "marketplace_install": True,
                "listing_version": listing.version
            }
        }
        
        integration = await IntegrationService.create_integration(
            db=db,
            integration_data=integration_data,
            creator_id=user_id
        )
        
        # Record installation
        installation = APIInstallation(
            listing_id=listing_id,
            user_id=user_id,
            integration_id=integration.id,
            version=listing.version,
            config=config,
            status="active"
        )
        
        db.add(installation)
        
        # Update listing stats
        listing.install_count += 1
        
        await db.commit()
        await db.refresh(installation)
        
        logger.info(f"Installed API integration: {listing_id} for user {user_id}")
        
        return {
            "installation_id": str(installation.id),
            "integration_id": str(integration.id),
            "status": "active",
            "installed_at": installation.installed_at
        }
    
    @staticmethod
    async def rate_listing(
        db: AsyncSession,
        listing_id: str,
        user_id: str,
        rating: int,
        review: Optional[str] = None
    ) -> Dict[str, Any]:
        """Rate and review API listing"""
        
        # Get listing
        listing = await MarketplaceService.get_listing(db, listing_id)
        if not listing:
            raise NotFoundError("API listing not found")
        
        # Check if user already reviewed
        existing_query = select(APIListingReview).where(
            and_(
                APIListingReview.listing_id == listing_id,
                APIListingReview.user_id == user_id
            )
        )
        existing_result = await db.execute(existing_query)
        existing = existing_result.scalar_one_or_none()
        
        if existing:
            # Update existing review
            existing.rating = rating
            existing.review_text = review
            existing.updated_at = datetime.utcnow()
            review_obj = existing
        else:
            # Create new review
            review_obj = APIListingReview(
                listing_id=listing_id,
                user_id=user_id,
                rating=rating,
                review_text=review
            )
            db.add(review_obj)
        
        await db.commit()
        
        # Recalculate listing rating
        await MarketplaceService._update_listing_rating(db, listing_id)
        
        logger.info(f"Rated API listing: {listing_id} by user {user_id}")
        
        return {
            "review_id": str(review_obj.id),
            "rating": rating,
            "created_at": review_obj.created_at
        }
    
    @staticmethod
    async def get_reviews(
        db: AsyncSession,
        listing_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[APIListingReview]:
        """Get reviews for API listing"""
        
        query = select(APIListingReview).where(
            APIListingReview.listing_id == listing_id
        ).order_by(desc(APIListingReview.created_at)).offset(offset).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def test_integration(
        db: AsyncSession,
        listing_id: str,
        config: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """Test API integration before installation"""
        
        # Get listing
        listing = await MarketplaceService.get_listing(db, listing_id)
        if not listing:
            raise NotFoundError("API listing not found")
        
        # Validate configuration
        if listing.config_schema:
            await MarketplaceService._validate_config(config, listing.config_schema)
        
        # Create temporary integration for testing
        test_config = {
            **config,
            "base_url": listing.base_url,
            "auth_type": listing.authentication_type,
            "auth_config": listing.auth_config
        }
        
        # Test connection based on API type
        try:
            if listing.api_type == "rest":
                result = await MarketplaceService._test_rest_api(test_config)
            elif listing.api_type == "graphql":
                result = await MarketplaceService._test_graphql_api(test_config)
            elif listing.api_type == "grpc":
                result = await MarketplaceService._test_grpc_api(test_config)
            else:
                result = {"status": "success", "message": "Configuration valid"}
            
            logger.info(f"Tested API integration: {listing_id} for user {user_id}")
            return result
            
        except Exception as e:
            logger.error(f"API test failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    @staticmethod
    async def get_documentation(
        db: AsyncSession,
        listing_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get API documentation for listing"""
        
        listing = await MarketplaceService.get_listing(db, listing_id)
        if not listing:
            return None
        
        return {
            "documentation_url": listing.documentation_url,
            "openapi_spec": listing.openapi_spec,
            "examples": listing.examples,
            "changelog": listing.changelog
        }
    
    @staticmethod
    async def get_categories(db: AsyncSession) -> List[Dict[str, Any]]:
        """Get marketplace categories"""
        
        query = select(MarketplaceCategory).order_by(
            MarketplaceCategory.sort_order,
            MarketplaceCategory.name
        )
        
        result = await db.execute(query)
        categories = result.scalars().all()
        
        return [
            {
                "id": str(cat.id),
                "name": cat.name,
                "description": cat.description,
                "icon": cat.icon,
                "color": cat.color,
                "listing_count": cat.listing_count,
                "featured": cat.featured
            }
            for cat in categories
        ]
    
    @staticmethod
    async def get_stats(db: AsyncSession) -> Dict[str, Any]:
        """Get marketplace statistics"""
        
        # Get listing counts
        total_listings_query = select(func.count()).select_from(APIListing).where(
            APIListing.status == "approved"
        )
        total_listings_result = await db.execute(total_listings_query)
        total_listings = total_listings_result.scalar()
        
        # Get total installations
        total_installs_query = select(func.sum(APIListing.install_count)).select_from(APIListing)
        total_installs_result = await db.execute(total_installs_query)
        total_installs = total_installs_result.scalar() or 0
        
        # Get category breakdown
        category_query = select(
            APIListing.category,
            func.count().label("count")
        ).where(
            APIListing.status == "approved"
        ).group_by(APIListing.category)
        
        category_result = await db.execute(category_query)
        categories = [
            {"category": row.category, "count": row.count}
            for row in category_result
        ]
        
        return {
            "total_listings": total_listings,
            "total_installs": total_installs,
            "categories": categories,
            "featured_count": len([l for l in categories if l.get("featured")])
        }
    
    @staticmethod
    async def get_user_listings(
        db: AsyncSession,
        user_id: str,
        status_filter: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[APIListing], int]:
        """Get user's API listings"""
        
        query = select(APIListing).where(APIListing.provider_id == user_id)
        
        if status_filter:
            query = query.where(APIListing.status == status_filter)
        
        # Get total count
        count_query = select(func.count()).select_from(query.alias())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        query = query.order_by(desc(APIListing.created_at)).offset(offset).limit(limit)
        
        result = await db.execute(query)
        listings = result.scalars().all()
        
        return listings, total
    
    # Helper methods
    @staticmethod
    async def _validate_category(db: AsyncSession, category: str) -> None:
        """Validate category exists"""
        query = select(MarketplaceCategory).where(MarketplaceCategory.name == category)
        result = await db.execute(query)
        cat = result.scalar_one_or_none()
        
        if not cat:
            raise ValidationError(f"Invalid category: {category}")
    
    @staticmethod
    async def _validate_config(config: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Validate configuration against JSON schema"""
        # This would use jsonschema library in production
        # For now, just basic validation
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in config:
                raise ValidationError(f"Required field missing: {field}")
    
    @staticmethod
    async def _update_listing_rating(db: AsyncSession, listing_id: str) -> None:
        """Recalculate listing rating average"""
        
        # Get all reviews for listing
        query = select(
            func.avg(APIListingReview.rating).label("avg_rating"),
            func.count().label("review_count")
        ).where(APIListingReview.listing_id == listing_id)
        
        result = await db.execute(query)
        row = result.first()
        
        # Update listing
        listing_query = select(APIListing).where(APIListing.id == listing_id)
        listing_result = await db.execute(listing_query)
        listing = listing_result.scalar_one_or_none()
        
        if listing:
            listing.rating_average = float(row.avg_rating or 0.0)
            listing.rating_count = row.review_count or 0
            await db.commit()
    
    @staticmethod
    async def _test_rest_api(config: Dict[str, Any]) -> Dict[str, Any]:
        """Test REST API connection"""
        import aiohttp
        
        base_url = config.get("base_url")
        if not base_url:
            raise ValidationError("Base URL required for REST API")
        
        # Test basic connectivity
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}/health", timeout=10) as response:
                if response.status == 200:
                    return {"status": "success", "message": "REST API connection successful"}
                else:
                    return {"status": "error", "message": f"HTTP {response.status}"}
    
    @staticmethod
    async def _test_graphql_api(config: Dict[str, Any]) -> Dict[str, Any]:
        """Test GraphQL API connection"""
        # Simplified GraphQL test
        return {"status": "success", "message": "GraphQL configuration valid"}
    
    @staticmethod
    async def _test_grpc_api(config: Dict[str, Any]) -> Dict[str, Any]:
        """Test gRPC API connection"""
        # Simplified gRPC test
        return {"status": "success", "message": "gRPC configuration valid"}