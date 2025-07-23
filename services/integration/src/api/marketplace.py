"""
API Marketplace endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
import logging

from ..db.database import get_db
from ..models.marketplace import APIListing, APIListingCreate, APIListingUpdate
from ..models.schemas import APIListingResponse, APIListingListResponse, MarketplaceStatsResponse
from ..core.auth import get_current_user, check_permission
from ..services.marketplace import MarketplaceService
from ..core.exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/marketplace", tags=["marketplace"])


@router.get("/", response_model=APIListingListResponse)
async def list_api_listings(
    category: Optional[str] = None,
    featured: Optional[bool] = None,
    provider: Optional[str] = None,
    search: Optional[str] = None,
    sort: str = Query("popularity", regex="^(popularity|rating|created_at|name)$"),
    order: str = Query("desc", regex="^(asc|desc)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """List API listings in marketplace"""
    try:
        listings, total = await MarketplaceService.list_listings(
            db=db,
            category=category,
            featured=featured,
            provider=provider,
            search=search,
            sort=sort,
            order=order,
            limit=limit,
            offset=offset
        )
        
        return APIListingListResponse(
            data=listings,
            meta={
                "total": total,
                "limit": limit,
                "offset": offset,
                "pages": (total + limit - 1) // limit
            }
        )
        
    except Exception as e:
        logger.error(f"Error listing API marketplace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list API marketplace"
        )


@router.get("/categories", response_model=List[Dict[str, Any]])
async def get_marketplace_categories(
    db: AsyncSession = Depends(get_db)
):
    """Get available marketplace categories"""
    try:
        categories = await MarketplaceService.get_categories(db)
        return categories
        
    except Exception as e:
        logger.error(f"Error getting marketplace categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get categories"
        )


@router.get("/stats", response_model=MarketplaceStatsResponse)
async def get_marketplace_stats(
    db: AsyncSession = Depends(get_db)
):
    """Get marketplace statistics"""
    try:
        stats = await MarketplaceService.get_stats(db)
        return MarketplaceStatsResponse(data=stats)
        
    except Exception as e:
        logger.error(f"Error getting marketplace stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get marketplace stats"
        )


@router.get("/{listing_id}", response_model=APIListingResponse)
async def get_api_listing(
    listing_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get specific API listing"""
    try:
        listing = await MarketplaceService.get_listing(db, listing_id)
        if not listing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API listing not found"
            )
        
        return APIListingResponse(data=listing)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting API listing {listing_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get API listing"
        )


@router.post("/", response_model=APIListingResponse, status_code=status.HTTP_201_CREATED)
async def create_api_listing(
    listing_data: APIListingCreate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create new API listing"""
    # Check permissions
    await check_permission(current_user, "marketplace:create", db)
    
    try:
        listing = await MarketplaceService.create_listing(
            db=db,
            listing_data=listing_data,
            creator_id=current_user.id
        )
        
        logger.info(f"API listing created: {listing.id} by user {current_user.id}")
        return APIListingResponse(data=listing)
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating API listing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API listing"
        )


@router.put("/{listing_id}", response_model=APIListingResponse)
async def update_api_listing(
    listing_id: str,
    listing_data: APIListingUpdate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update API listing"""
    try:
        # Get existing listing
        listing = await MarketplaceService.get_listing(db, listing_id)
        if not listing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API listing not found"
            )
        
        # Check permissions
        if listing.provider_id != current_user.id:
            await check_permission(current_user, "marketplace:admin", db)
        
        updated_listing = await MarketplaceService.update_listing(
            db=db,
            listing_id=listing_id,
            listing_data=listing_data,
            updater_id=current_user.id
        )
        
        logger.info(f"API listing updated: {listing_id} by user {current_user.id}")
        return APIListingResponse(data=updated_listing)
        
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating API listing {listing_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update API listing"
        )


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_listing(
    listing_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete API listing"""
    try:
        # Get existing listing
        listing = await MarketplaceService.get_listing(db, listing_id)
        if not listing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API listing not found"
            )
        
        # Check permissions
        if listing.provider_id != current_user.id:
            await check_permission(current_user, "marketplace:admin", db)
        
        await MarketplaceService.delete_listing(db, listing_id)
        
        logger.info(f"API listing deleted: {listing_id} by user {current_user.id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting API listing {listing_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete API listing"
        )


@router.post("/{listing_id}/install", response_model=Dict[str, Any])
async def install_api_integration(
    listing_id: str,
    config: Optional[Dict[str, Any]] = None,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Install API integration from marketplace"""
    # Check permissions
    await check_permission(current_user, "integrations:create", db)
    
    try:
        result = await MarketplaceService.install_integration(
            db=db,
            listing_id=listing_id,
            user_id=current_user.id,
            config=config or {}
        )
        
        logger.info(f"API integration installed: {listing_id} by user {current_user.id}")
        return result
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error installing API integration {listing_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to install API integration"
        )


@router.post("/{listing_id}/rate", response_model=Dict[str, Any])
async def rate_api_listing(
    listing_id: str,
    rating: int = Query(..., ge=1, le=5),
    review: Optional[str] = None,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Rate API listing"""
    try:
        result = await MarketplaceService.rate_listing(
            db=db,
            listing_id=listing_id,
            user_id=current_user.id,
            rating=rating,
            review=review
        )
        
        logger.info(f"API listing rated: {listing_id} by user {current_user.id}")
        return result
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error rating API listing {listing_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rate API listing"
        )


@router.get("/{listing_id}/reviews", response_model=List[Dict[str, Any]])
async def get_api_listing_reviews(
    listing_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Get API listing reviews"""
    try:
        reviews = await MarketplaceService.get_reviews(
            db=db,
            listing_id=listing_id,
            limit=limit,
            offset=offset
        )
        
        return reviews
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting reviews for listing {listing_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get reviews"
        )


@router.post("/{listing_id}/test", response_model=Dict[str, Any])
async def test_api_integration(
    listing_id: str,
    test_config: Dict[str, Any],
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Test API integration before installation"""
    try:
        result = await MarketplaceService.test_integration(
            db=db,
            listing_id=listing_id,
            config=test_config,
            user_id=current_user.id
        )
        
        logger.info(f"API integration tested: {listing_id} by user {current_user.id}")
        return result
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error testing API integration {listing_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test API integration"
        )


@router.get("/{listing_id}/documentation", response_model=Dict[str, Any])
async def get_api_documentation(
    listing_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get API documentation for listing"""
    try:
        documentation = await MarketplaceService.get_documentation(db, listing_id)
        if not documentation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API documentation not found"
            )
        
        return documentation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting documentation for listing {listing_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get API documentation"
        )


@router.get("/my/listings", response_model=APIListingListResponse)
async def get_my_api_listings(
    status_filter: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's API listings"""
    try:
        listings, total = await MarketplaceService.get_user_listings(
            db=db,
            user_id=current_user.id,
            status_filter=status_filter,
            limit=limit,
            offset=offset
        )
        
        return APIListingListResponse(
            data=listings,
            meta={
                "total": total,
                "limit": limit,
                "offset": offset,
                "pages": (total + limit - 1) // limit
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting user listings for {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user listings"
        )