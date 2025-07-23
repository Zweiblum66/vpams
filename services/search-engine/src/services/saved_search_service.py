"""
Saved Search Service - Manage saved searches for users
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import structlog
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..models.schemas import (
    SavedSearchCreate, SavedSearchUpdate, SavedSearch, SavedSearchList,
    SavedSearchExecute, FilteredSearchQuery, FilteredSearchResponse,
    FilterCondition
)
from ..db.models import SavedSearchModel
from ..core.exceptions import SearchError, NotFoundError, ValidationError
from .search_service import SearchService, get_search_service

logger = structlog.get_logger()


class SavedSearchService:
    """Service for managing saved searches"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.saved_search_model = SavedSearchModel(db.saved_searches)
        self.db = db
    
    async def create_saved_search(
        self,
        user_id: str,
        saved_search: SavedSearchCreate
    ) -> SavedSearch:
        """Create a new saved search for a user"""
        try:
            # Check if name already exists for this user
            name_exists = await self.saved_search_model.check_name_exists(
                user_id, saved_search.name
            )
            if name_exists:
                raise ValidationError(
                    f"A saved search with name '{saved_search.name}' already exists"
                )
            
            # Prepare document for MongoDB
            search_doc = {
                "user_id": user_id,
                "name": saved_search.name,
                "description": saved_search.description,
                "query": saved_search.query.dict(),
                "is_public": saved_search.is_public,
                "tags": saved_search.tags or [],
                "notify_on_new_results": saved_search.notify_on_new_results
            }
            
            # Create the saved search
            search_id = await self.saved_search_model.create(search_doc)
            
            # Retrieve and return the created search
            created_search = await self.saved_search_model.get_by_id(search_id)
            if not created_search:
                raise SearchError("Failed to retrieve created search")
            
            logger.info(
                "saved_search_created",
                user_id=user_id,
                search_id=search_id,
                name=saved_search.name
            )
            
            return self._format_saved_search(created_search)
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error("failed_to_create_saved_search", error=str(e), user_id=user_id)
            raise SearchError(f"Failed to create saved search: {str(e)}")
    
    async def get_saved_search(
        self,
        search_id: str,
        user_id: Optional[str] = None
    ) -> SavedSearch:
        """Get a saved search by ID"""
        try:
            search = await self.saved_search_model.get_by_id(search_id, user_id)
            if not search:
                raise NotFoundError(f"Saved search {search_id} not found")
            
            return self._format_saved_search(search)
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("failed_to_get_saved_search", error=str(e), search_id=search_id)
            raise SearchError(f"Failed to get saved search: {str(e)}")
    
    async def list_user_searches(
        self,
        user_id: str,
        page: int = 1,
        per_page: int = 20,
        include_public: bool = True
    ) -> SavedSearchList:
        """List saved searches for a user"""
        try:
            skip = (page - 1) * per_page
            
            searches, total = await self.saved_search_model.get_user_searches(
                user_id,
                skip=skip,
                limit=per_page,
                include_public=include_public
            )
            
            total_pages = (total + per_page - 1) // per_page
            
            return SavedSearchList(
                searches=[self._format_saved_search(s) for s in searches],
                total=total,
                page=page,
                per_page=per_page,
                total_pages=total_pages
            )
            
        except Exception as e:
            logger.error("failed_to_list_user_searches", error=str(e), user_id=user_id)
            raise SearchError(f"Failed to list saved searches: {str(e)}")
    
    async def search_by_tags(
        self,
        tags: List[str],
        page: int = 1,
        per_page: int = 20
    ) -> SavedSearchList:
        """Search public saved searches by tags"""
        try:
            skip = (page - 1) * per_page
            
            searches, total = await self.saved_search_model.search_by_tags(
                tags,
                skip=skip,
                limit=per_page
            )
            
            total_pages = (total + per_page - 1) // per_page
            
            return SavedSearchList(
                searches=[self._format_saved_search(s) for s in searches],
                total=total,
                page=page,
                per_page=per_page,
                total_pages=total_pages
            )
            
        except Exception as e:
            logger.error("failed_to_search_by_tags", error=str(e), tags=tags)
            raise SearchError(f"Failed to search by tags: {str(e)}")
    
    async def get_popular_searches(self, limit: int = 10) -> List[SavedSearch]:
        """Get most popular public saved searches"""
        try:
            searches = await self.saved_search_model.get_popular_searches(limit)
            return [self._format_saved_search(s) for s in searches]
            
        except Exception as e:
            logger.error("failed_to_get_popular_searches", error=str(e))
            raise SearchError(f"Failed to get popular searches: {str(e)}")
    
    async def update_saved_search(
        self,
        search_id: str,
        user_id: str,
        update_data: SavedSearchUpdate
    ) -> SavedSearch:
        """Update a saved search"""
        try:
            # Get existing search to verify ownership
            existing = await self.saved_search_model.get_by_id(search_id, user_id)
            if not existing:
                raise NotFoundError(f"Saved search {search_id} not found")
            
            if existing["user_id"] != user_id:
                raise ValidationError("You can only update your own saved searches")
            
            # Check if new name conflicts
            if update_data.name and update_data.name != existing["name"]:
                name_exists = await self.saved_search_model.check_name_exists(
                    user_id, update_data.name, exclude_id=search_id
                )
                if name_exists:
                    raise ValidationError(
                        f"A saved search with name '{update_data.name}' already exists"
                    )
            
            # Prepare update document
            update_doc = {}
            if update_data.name is not None:
                update_doc["name"] = update_data.name
            if update_data.description is not None:
                update_doc["description"] = update_data.description
            if update_data.query is not None:
                update_doc["query"] = update_data.query.dict()
            if update_data.is_public is not None:
                update_doc["is_public"] = update_data.is_public
            if update_data.tags is not None:
                update_doc["tags"] = update_data.tags
            if update_data.notify_on_new_results is not None:
                update_doc["notify_on_new_results"] = update_data.notify_on_new_results
            
            # Update the search
            success = await self.saved_search_model.update(search_id, user_id, update_doc)
            if not success:
                raise SearchError("Failed to update saved search")
            
            # Get and return updated search
            updated_search = await self.saved_search_model.get_by_id(search_id)
            if not updated_search:
                raise SearchError("Failed to retrieve updated search")
            
            logger.info(
                "saved_search_updated",
                user_id=user_id,
                search_id=search_id
            )
            
            return self._format_saved_search(updated_search)
            
        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error("failed_to_update_saved_search", error=str(e), search_id=search_id)
            raise SearchError(f"Failed to update saved search: {str(e)}")
    
    async def delete_saved_search(self, search_id: str, user_id: str) -> bool:
        """Delete a saved search"""
        try:
            success = await self.saved_search_model.delete(search_id, user_id)
            if not success:
                raise NotFoundError(f"Saved search {search_id} not found or access denied")
            
            logger.info(
                "saved_search_deleted",
                user_id=user_id,
                search_id=search_id
            )
            
            return True
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("failed_to_delete_saved_search", error=str(e), search_id=search_id)
            raise SearchError(f"Failed to delete saved search: {str(e)}")
    
    async def execute_saved_search(
        self,
        search_id: str,
        user_id: Optional[str],
        execute_params: Optional[SavedSearchExecute] = None
    ) -> FilteredSearchResponse:
        """Execute a saved search with optional parameter overrides"""
        try:
            # Get the saved search
            saved_search = await self.get_saved_search(search_id, user_id)
            
            # Increment usage counter
            await self.saved_search_model.increment_usage(search_id)
            
            # Build query with overrides
            query = FilteredSearchQuery(**saved_search.query.dict())
            
            if execute_params:
                # Apply overrides
                if execute_params.size is not None:
                    query.size = execute_params.size
                if execute_params.from_ is not None:
                    query.from_ = execute_params.from_
                if execute_params.sort_by is not None:
                    query.sort_by = execute_params.sort_by
                if execute_params.sort_order is not None:
                    query.sort_order = execute_params.sort_order
                
                # Add additional filters
                if execute_params.additional_filters:
                    if query.filters:
                        query.filters.extend(execute_params.additional_filters)
                    else:
                        query.filters = execute_params.additional_filters
            
            # Execute the search
            search_service = await get_search_service()
            results = await search_service.filtered_search(query)
            
            logger.info(
                "saved_search_executed",
                search_id=search_id,
                user_id=user_id,
                total_hits=results.total_hits
            )
            
            return results
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("failed_to_execute_saved_search", error=str(e), search_id=search_id)
            raise SearchError(f"Failed to execute saved search: {str(e)}")
    
    def _format_saved_search(self, search_doc: Dict[str, Any]) -> SavedSearch:
        """Format MongoDB document to SavedSearch model"""
        return SavedSearch(
            id=search_doc["id"],
            user_id=search_doc["user_id"],
            name=search_doc["name"],
            description=search_doc.get("description"),
            query=FilteredSearchQuery(**search_doc["query"]),
            is_public=search_doc["is_public"],
            tags=search_doc.get("tags", []),
            notify_on_new_results=search_doc.get("notify_on_new_results", False),
            usage_count=search_doc.get("usage_count", 0),
            last_used_at=search_doc.get("last_used_at"),
            created_at=search_doc["created_at"],
            updated_at=search_doc["updated_at"]
        )


# Dependency injection helper
_saved_search_service: Optional[SavedSearchService] = None


async def get_saved_search_service() -> SavedSearchService:
    """Get saved search service instance"""
    global _saved_search_service
    
    if _saved_search_service is None:
        from ..db.mongodb import get_mongodb
        db = await get_mongodb()
        _saved_search_service = SavedSearchService(db)
    
    return _saved_search_service