"""
Search Template Service - Manages reusable search templates and configurations
"""

import json
import uuid
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import structlog
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, TEXT
from pymongo.errors import DuplicateKeyError, PyMongoError

from ..models.schemas import (
    SearchTemplateCreate, SearchTemplateUpdate, SearchTemplate, SearchTemplateList,
    SearchTemplateExecute, SearchTemplateExecuteResponse, SearchTemplateFavorite,
    SearchTemplateStats, SearchTemplateImport, SearchTemplateExport, SearchTemplateShare,
    SearchTemplateType, SearchTemplateCategory, SearchQuery, SearchResponse,
    SearchType, IndexType, FilterCondition, FacetConfig, FuzzySearchConfig,
    SynonymConfig, RankingConfig, SortOrder
)
from ..db.mongodb import get_mongodb_client
from ..core.exceptions import SearchError, NotFoundError, ValidationError
from .search_service import SearchService

logger = structlog.get_logger()


class SearchTemplateService:
    """Service for managing search templates"""
    
    def __init__(self, mongodb_client: AsyncIOMotorDatabase, search_service: SearchService):
        self.db = mongodb_client
        self.search_service = search_service
        self.collection = self.db.search_templates
        self.favorites_collection = self.db.search_template_favorites
        self.stats_collection = self.db.search_template_stats
        self.shares_collection = self.db.search_template_shares
        
    async def _ensure_indexes(self):
        """Create necessary indexes for efficient queries"""
        try:
            # Primary template collection indexes
            await self.collection.create_index([("id", ASCENDING)], unique=True)
            await self.collection.create_index([("name", TEXT), ("description", TEXT)])
            await self.collection.create_index([("category", ASCENDING)])
            await self.collection.create_index([("template_type", ASCENDING)])
            await self.collection.create_index([("created_by", ASCENDING)])
            await self.collection.create_index([("is_public", ASCENDING)])
            await self.collection.create_index([("created_at", DESCENDING)])
            await self.collection.create_index([("updated_at", DESCENDING)])
            
            # Favorites collection indexes
            await self.favorites_collection.create_index([
                ("user_id", ASCENDING), 
                ("template_id", ASCENDING)
            ], unique=True)
            
            # Stats collection indexes
            await self.stats_collection.create_index([("template_id", ASCENDING)], unique=True)
            await self.stats_collection.create_index([("usage_count", DESCENDING)])
            await self.stats_collection.create_index([("last_used", DESCENDING)])
            
            # Shares collection indexes
            await self.shares_collection.create_index([
                ("template_id", ASCENDING), 
                ("shared_with", ASCENDING)
            ], unique=True)
            
        except Exception as e:
            logger.error("Failed to create indexes", error=str(e))
            raise SearchError(f"Failed to create database indexes: {str(e)}")
    
    async def create_template(self, template_data: SearchTemplateCreate, user_id: str) -> SearchTemplate:
        """Create a new search template"""
        try:
            # Generate unique ID
            template_id = str(uuid.uuid4())
            
            # Validate template configuration
            await self._validate_template_config(template_data.config)
            
            # Create template document
            template_doc = {
                "id": template_id,
                "name": template_data.name,
                "description": template_data.description,
                "category": template_data.category,
                "template_type": template_data.template_type,
                "config": template_data.config.model_dump(),
                "parameters": [param.model_dump() for param in template_data.parameters],
                "tags": template_data.tags,
                "is_public": template_data.is_public,
                "created_by": user_id,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "version": 1
            }
            
            # Insert template
            await self.collection.insert_one(template_doc)
            
            # Initialize stats
            await self.stats_collection.insert_one({
                "template_id": template_id,
                "usage_count": 0,
                "favorite_count": 0,
                "last_used": None,
                "created_at": datetime.utcnow()
            })
            
            logger.info("Search template created", template_id=template_id, name=template_data.name)
            
            return SearchTemplate(**template_doc)
            
        except DuplicateKeyError:
            raise ValidationError("Template with this name already exists")
        except Exception as e:
            logger.error("Failed to create search template", error=str(e))
            raise SearchError(f"Failed to create search template: {str(e)}")
    
    async def get_template(self, template_id: str, user_id: Optional[str] = None) -> SearchTemplate:
        """Get a search template by ID"""
        try:
            # Check if template exists and user has access
            template = await self.collection.find_one({"id": template_id})
            
            if not template:
                raise NotFoundError(f"Search template {template_id} not found")
            
            # Check access permissions
            if not await self._has_access(template, user_id):
                raise ValidationError("Access denied to this template")
            
            return SearchTemplate(**template)
            
        except NotFoundError:
            raise
        except ValidationError:
            raise
        except Exception as e:
            logger.error("Failed to get search template", template_id=template_id, error=str(e))
            raise SearchError(f"Failed to get search template: {str(e)}")
    
    async def update_template(self, template_id: str, template_data: SearchTemplateUpdate, user_id: str) -> SearchTemplate:
        """Update a search template"""
        try:
            # Check if template exists and user has permission
            existing = await self.collection.find_one({"id": template_id})
            if not existing:
                raise NotFoundError(f"Search template {template_id} not found")
            
            if existing["created_by"] != user_id:
                raise ValidationError("Only the template creator can update this template")
            
            # Validate updated configuration if provided
            if template_data.config:
                await self._validate_template_config(template_data.config)
            
            # Prepare update document
            update_doc = {
                "updated_at": datetime.utcnow(),
                "version": existing["version"] + 1
            }
            
            # Add fields that are being updated
            if template_data.name is not None:
                update_doc["name"] = template_data.name
            if template_data.description is not None:
                update_doc["description"] = template_data.description
            if template_data.category is not None:
                update_doc["category"] = template_data.category
            if template_data.template_type is not None:
                update_doc["template_type"] = template_data.template_type
            if template_data.config is not None:
                update_doc["config"] = template_data.config.model_dump()
            if template_data.parameters is not None:
                update_doc["parameters"] = [param.model_dump() for param in template_data.parameters]
            if template_data.tags is not None:
                update_doc["tags"] = template_data.tags
            if template_data.is_public is not None:
                update_doc["is_public"] = template_data.is_public
            
            # Update template
            await self.collection.update_one(
                {"id": template_id},
                {"$set": update_doc}
            )
            
            # Get updated template
            updated_template = await self.collection.find_one({"id": template_id})
            
            logger.info("Search template updated", template_id=template_id)
            
            return SearchTemplate(**updated_template)
            
        except NotFoundError:
            raise
        except ValidationError:
            raise
        except Exception as e:
            logger.error("Failed to update search template", template_id=template_id, error=str(e))
            raise SearchError(f"Failed to update search template: {str(e)}")
    
    async def delete_template(self, template_id: str, user_id: str) -> bool:
        """Delete a search template"""
        try:
            # Check if template exists and user has permission
            existing = await self.collection.find_one({"id": template_id})
            if not existing:
                raise NotFoundError(f"Search template {template_id} not found")
            
            if existing["created_by"] != user_id:
                raise ValidationError("Only the template creator can delete this template")
            
            # Delete template and related data
            await self.collection.delete_one({"id": template_id})
            await self.stats_collection.delete_one({"template_id": template_id})
            await self.favorites_collection.delete_many({"template_id": template_id})
            await self.shares_collection.delete_many({"template_id": template_id})
            
            logger.info("Search template deleted", template_id=template_id)
            
            return True
            
        except NotFoundError:
            raise
        except ValidationError:
            raise
        except Exception as e:
            logger.error("Failed to delete search template", template_id=template_id, error=str(e))
            raise SearchError(f"Failed to delete search template: {str(e)}")
    
    async def list_templates(
        self, 
        user_id: Optional[str] = None,
        category: Optional[SearchTemplateCategory] = None,
        template_type: Optional[SearchTemplateType] = None,
        is_public: Optional[bool] = None,
        created_by: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> SearchTemplateList:
        """List search templates with filtering"""
        try:
            # Build filter query
            filter_query = {}
            
            if category:
                filter_query["category"] = category
            if template_type:
                filter_query["template_type"] = template_type
            if is_public is not None:
                filter_query["is_public"] = is_public
            if created_by:
                filter_query["created_by"] = created_by
            
            # Add access filter for non-public templates
            if user_id:
                access_filter = {
                    "$or": [
                        {"is_public": True},
                        {"created_by": user_id},
                        {"id": {"$in": await self._get_shared_template_ids(user_id)}}
                    ]
                }
                if filter_query:
                    filter_query = {"$and": [filter_query, access_filter]}
                else:
                    filter_query = access_filter
            else:
                filter_query["is_public"] = True
            
            # Calculate pagination
            skip = (page - 1) * limit
            
            # Get templates
            cursor = self.collection.find(filter_query).sort("updated_at", -1).skip(skip).limit(limit)
            templates = await cursor.to_list(length=limit)
            
            # Get total count
            total = await self.collection.count_documents(filter_query)
            
            # Get stats for each template
            template_objects = []
            for template in templates:
                stats = await self.stats_collection.find_one({"template_id": template["id"]})
                template["usage_count"] = stats.get("usage_count", 0) if stats else 0
                template["favorite_count"] = stats.get("favorite_count", 0) if stats else 0
                template_objects.append(SearchTemplate(**template))
            
            return SearchTemplateList(
                templates=template_objects,
                total=total,
                page=page,
                limit=limit,
                pages=(total + limit - 1) // limit
            )
            
        except Exception as e:
            logger.error("Failed to list search templates", error=str(e))
            raise SearchError(f"Failed to list search templates: {str(e)}")
    
    async def execute_template(self, template_id: str, execution_data: SearchTemplateExecute, user_id: Optional[str] = None) -> SearchTemplateExecuteResponse:
        """Execute a search template"""
        try:
            # Get template
            template = await self.get_template(template_id, user_id)
            
            # Build search query from template
            search_query = await self._build_search_query(template, execution_data.parameters)
            
            # Execute search
            start_time = datetime.utcnow()
            search_response = await self.search_service.search(search_query)
            end_time = datetime.utcnow()
            
            # Update usage stats
            await self._update_usage_stats(template_id)
            
            logger.info("Search template executed", 
                       template_id=template_id, 
                       execution_time=(end_time - start_time).total_seconds())
            
            return SearchTemplateExecuteResponse(
                template_id=template_id,
                template_name=template.name,
                search_response=search_response,
                execution_time=(end_time - start_time).total_seconds(),
                executed_at=start_time
            )
            
        except Exception as e:
            logger.error("Failed to execute search template", template_id=template_id, error=str(e))
            raise SearchError(f"Failed to execute search template: {str(e)}")
    
    async def add_to_favorites(self, template_id: str, user_id: str) -> bool:
        """Add template to user's favorites"""
        try:
            # Check if template exists
            template = await self.get_template(template_id, user_id)
            
            # Add to favorites
            await self.favorites_collection.insert_one({
                "user_id": user_id,
                "template_id": template_id,
                "created_at": datetime.utcnow()
            })
            
            # Update favorite count
            await self.stats_collection.update_one(
                {"template_id": template_id},
                {"$inc": {"favorite_count": 1}}
            )
            
            logger.info("Template added to favorites", template_id=template_id, user_id=user_id)
            
            return True
            
        except DuplicateKeyError:
            # Already in favorites
            return True
        except Exception as e:
            logger.error("Failed to add template to favorites", template_id=template_id, error=str(e))
            raise SearchError(f"Failed to add template to favorites: {str(e)}")
    
    async def remove_from_favorites(self, template_id: str, user_id: str) -> bool:
        """Remove template from user's favorites"""
        try:
            result = await self.favorites_collection.delete_one({
                "user_id": user_id,
                "template_id": template_id
            })
            
            if result.deleted_count > 0:
                # Update favorite count
                await self.stats_collection.update_one(
                    {"template_id": template_id},
                    {"$inc": {"favorite_count": -1}}
                )
                
                logger.info("Template removed from favorites", template_id=template_id, user_id=user_id)
            
            return result.deleted_count > 0
            
        except Exception as e:
            logger.error("Failed to remove template from favorites", template_id=template_id, error=str(e))
            raise SearchError(f"Failed to remove template from favorites: {str(e)}")
    
    async def get_template_stats(self, template_id: str, user_id: Optional[str] = None) -> SearchTemplateStats:
        """Get template usage statistics"""
        try:
            # Check access
            template = await self.get_template(template_id, user_id)
            
            # Get stats
            stats = await self.stats_collection.find_one({"template_id": template_id})
            
            if not stats:
                # Initialize stats if not exists
                stats = {
                    "template_id": template_id,
                    "usage_count": 0,
                    "favorite_count": 0,
                    "last_used": None,
                    "created_at": datetime.utcnow()
                }
                await self.stats_collection.insert_one(stats)
            
            return SearchTemplateStats(**stats)
            
        except Exception as e:
            logger.error("Failed to get template stats", template_id=template_id, error=str(e))
            raise SearchError(f"Failed to get template stats: {str(e)}")
    
    async def export_template(self, template_id: str, user_id: Optional[str] = None) -> SearchTemplateExport:
        """Export template for sharing or backup"""
        try:
            template = await self.get_template(template_id, user_id)
            
            export_data = SearchTemplateExport(
                template=template,
                exported_at=datetime.utcnow(),
                exported_by=user_id,
                format_version="1.0"
            )
            
            logger.info("Template exported", template_id=template_id)
            
            return export_data
            
        except Exception as e:
            logger.error("Failed to export template", template_id=template_id, error=str(e))
            raise SearchError(f"Failed to export template: {str(e)}")
    
    async def import_template(self, import_data: SearchTemplateImport, user_id: str) -> SearchTemplate:
        """Import template from export data"""
        try:
            # Create template from import data
            template_create = SearchTemplateCreate(
                name=import_data.template.name,
                description=import_data.template.description,
                category=import_data.template.category,
                template_type=import_data.template.template_type,
                config=import_data.template.config,
                parameters=import_data.template.parameters,
                tags=import_data.template.tags,
                is_public=False  # Always import as private
            )
            
            # If name conflict, append timestamp
            existing = await self.collection.find_one({"name": template_create.name})
            if existing:
                template_create.name = f"{template_create.name} (imported {datetime.utcnow().strftime('%Y-%m-%d %H:%M')})"
            
            return await self.create_template(template_create, user_id)
            
        except Exception as e:
            logger.error("Failed to import template", error=str(e))
            raise SearchError(f"Failed to import template: {str(e)}")
    
    async def share_template(self, template_id: str, share_data: SearchTemplateShare, user_id: str) -> bool:
        """Share template with specific users"""
        try:
            # Check if user owns the template
            template = await self.collection.find_one({"id": template_id})
            if not template:
                raise NotFoundError(f"Search template {template_id} not found")
            
            if template["created_by"] != user_id:
                raise ValidationError("Only the template creator can share this template")
            
            # Add shares
            for shared_user in share_data.shared_with:
                await self.shares_collection.update_one(
                    {"template_id": template_id, "shared_with": shared_user},
                    {
                        "$set": {
                            "template_id": template_id,
                            "shared_with": shared_user,
                            "permissions": share_data.permissions,
                            "shared_by": user_id,
                            "shared_at": datetime.utcnow()
                        }
                    },
                    upsert=True
                )
            
            logger.info("Template shared", template_id=template_id, shared_with=share_data.shared_with)
            
            return True
            
        except Exception as e:
            logger.error("Failed to share template", template_id=template_id, error=str(e))
            raise SearchError(f"Failed to share template: {str(e)}")
    
    async def _validate_template_config(self, config: Any) -> None:
        """Validate template configuration"""
        # This is a placeholder for configuration validation
        # In a real implementation, you would validate the config structure
        pass
    
    async def _has_access(self, template: Dict[str, Any], user_id: Optional[str]) -> bool:
        """Check if user has access to template"""
        # Public templates are accessible to everyone
        if template.get("is_public", False):
            return True
        
        # No user ID means no access to private templates
        if not user_id:
            return False
        
        # Owner has access
        if template.get("created_by") == user_id:
            return True
        
        # Check if template is shared with user
        share = await self.shares_collection.find_one({
            "template_id": template["id"],
            "shared_with": user_id
        })
        
        return share is not None
    
    async def _get_shared_template_ids(self, user_id: str) -> List[str]:
        """Get template IDs shared with user"""
        shares = await self.shares_collection.find({"shared_with": user_id}).to_list(length=None)
        return [share["template_id"] for share in shares]
    
    async def _build_search_query(self, template: SearchTemplate, parameters: Optional[Dict[str, Any]] = None) -> SearchQuery:
        """Build search query from template and parameters"""
        config = template.config
        
        # Start with template's default query
        query_text = config.default_query or ""
        
        # Apply parameter substitutions
        if parameters:
            for param_name, param_value in parameters.items():
                placeholder = f"{{{param_name}}}"
                if placeholder in query_text:
                    query_text = query_text.replace(placeholder, str(param_value))
        
        # Build search query based on template type
        search_query = SearchQuery(
            query=query_text,
            search_type=config.search_type,
            indices=config.indices,
            fields=config.fields,
            sort_by=parameters.get("sort_by", "relevance"),
            sort_order=SortOrder(parameters.get("sort_order", "desc")),
            page=parameters.get("page", 1),
            limit=parameters.get("limit", 20)
        )
        
        # Add filters from template and parameters
        if config.default_filters:
            search_query.filters = config.default_filters
        
        if parameters and "filters" in parameters:
            additional_filters = parameters["filters"]
            if search_query.filters:
                search_query.filters.extend(additional_filters)
            else:
                search_query.filters = additional_filters
        
        return search_query
    
    async def _update_usage_stats(self, template_id: str) -> None:
        """Update template usage statistics"""
        try:
            await self.stats_collection.update_one(
                {"template_id": template_id},
                {
                    "$inc": {"usage_count": 1},
                    "$set": {"last_used": datetime.utcnow()}
                }
            )
        except Exception as e:
            logger.warning("Failed to update usage stats", template_id=template_id, error=str(e))


# Service instance
_search_template_service: Optional[SearchTemplateService] = None


async def get_search_template_service() -> SearchTemplateService:
    """Get search template service instance"""
    global _search_template_service
    
    if _search_template_service is None:
        from .search_service import get_search_service
        
        mongodb_client = await get_mongodb_client()
        search_service = await get_search_service()
        
        _search_template_service = SearchTemplateService(mongodb_client, search_service)
        await _search_template_service._ensure_indexes()
    
    return _search_template_service