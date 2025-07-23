"""
Template Service

This module provides functionality for managing metadata templates.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
import structlog
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, TEXT
from pymongo.errors import DuplicateKeyError
from bson import ObjectId

from ..db.models import MetadataTemplate, MetadataSchema
from ..models.schemas import (
    TemplateCreate, TemplateResponse, 
    PaginationParams, PaginatedResponse
)
from ..services.schema_service import SchemaService
from ..services.metadata_validator import MetadataValidator
from ..core.exceptions import (
    ResourceNotFoundError, DuplicateResourceError,
    ValidationError, ConflictError
)

logger = structlog.get_logger()


class TemplateService:
    """Service for managing metadata templates"""
    
    def __init__(self, db: AsyncIOMotorDatabase, user_id: UUID):
        self.db = db
        self.user_id = user_id
        self.templates_collection = db.metadata_templates
        self.schema_service = SchemaService(db, user_id)
        self.validator = MetadataValidator()
    
    async def create_template(self, template_data: TemplateCreate) -> TemplateResponse:
        """Create a new metadata template"""
        try:
            # Validate that schema exists
            schema = await self.schema_service.get_schema(template_data.schema_id)
            if not schema:
                raise ResourceNotFoundError(f"Schema {template_data.schema_id} not found")
            
            # Validate template name uniqueness for this user
            existing = await self.templates_collection.find_one({
                "name": template_data.name,
                "owner_id": self.user_id
            })
            if existing:
                raise DuplicateResourceError(f"Template with name '{template_data.name}' already exists")
            
            # Validate default values against schema
            validation_result = await self.validator.validate_metadata(
                template_data.default_values,
                schema
            )
            
            # Create template document
            template = MetadataTemplate(
                template_id=uuid4(),
                name=template_data.name,
                description=template_data.description,
                schema_id=template_data.schema_id,
                default_values=validation_result["validated_data"],
                category=template_data.category,
                tags=template_data.tags,
                is_public=template_data.is_public,
                owner_id=self.user_id,
                shared_with=template_data.shared_with,
                created_at=datetime.utcnow(),
                usage_count=0
            )
            
            # Insert into database
            result = await self.templates_collection.insert_one(
                template.dict(by_alias=True, exclude_none=True)
            )
            template.id = result.inserted_id
            
            logger.info(
                "template_created",
                template_id=str(template.template_id),
                name=template.name,
                schema_id=str(template.schema_id)
            )
            
            return self._to_response(template)
            
        except DuplicateKeyError:
            raise DuplicateResourceError(f"Template with name '{template_data.name}' already exists")
        except Exception as e:
            logger.error("template_creation_failed", error=str(e))
            raise
    
    async def get_template(self, template_id: UUID) -> TemplateResponse:
        """Get a template by ID"""
        template = await self._get_template_by_id(template_id)
        if not template:
            raise ResourceNotFoundError(f"Template {template_id} not found")
        
        # Check access permissions
        if not await self._check_template_access(template):
            raise ResourceNotFoundError(f"Template {template_id} not found")
        
        return self._to_response(template)
    
    async def list_templates(
        self,
        pagination: PaginationParams,
        category: Optional[str] = None,
        schema_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        public_only: bool = False,
        search: Optional[str] = None
    ) -> PaginatedResponse:
        """List templates with filtering and pagination"""
        # Build query
        query = {}
        
        if not public_only:
            # Show user's own templates or public templates or shared with user
            query["$or"] = [
                {"owner_id": self.user_id},
                {"is_public": True},
                {"shared_with": self.user_id}
            ]
        else:
            query["is_public"] = True
        
        if category:
            query["category"] = category
        
        if schema_id:
            query["schema_id"] = schema_id
        
        if tags:
            query["tags"] = {"$in": tags}
        
        if search:
            query["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}},
                {"tags": {"$regex": search, "$options": "i"}}
            ]
        
        # Get total count
        total = await self.templates_collection.count_documents(query)
        
        # Get paginated results
        cursor = self.templates_collection.find(query)
        cursor = cursor.skip(pagination.offset).limit(pagination.page_size)
        cursor = cursor.sort("created_at", DESCENDING)
        
        templates = []
        async for doc in cursor:
            template = MetadataTemplate(**doc)
            templates.append(self._to_response(template))
        
        return PaginatedResponse(
            items=templates,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            pages=(total + pagination.page_size - 1) // pagination.page_size
        )
    
    async def update_template(
        self,
        template_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        default_values: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        is_public: Optional[bool] = None,
        shared_with: Optional[List[UUID]] = None
    ) -> TemplateResponse:
        """Update a template"""
        template = await self._get_template_by_id(template_id)
        if not template:
            raise ResourceNotFoundError(f"Template {template_id} not found")
        
        # Check ownership
        if template.owner_id != self.user_id:
            raise ResourceNotFoundError(f"Template {template_id} not found")
        
        # Build update document
        update_doc = {"updated_at": datetime.utcnow()}
        
        if name is not None:
            # Check name uniqueness
            existing = await self.templates_collection.find_one({
                "name": name,
                "owner_id": self.user_id,
                "template_id": {"$ne": template_id}
            })
            if existing:
                raise DuplicateResourceError(f"Template with name '{name}' already exists")
            update_doc["name"] = name
        
        if description is not None:
            update_doc["description"] = description
        
        if default_values is not None:
            # Validate default values against schema
            schema = await self.schema_service.get_schema(template.schema_id)
            validation_result = await self.validator.validate_metadata(
                default_values,
                schema
            )
            update_doc["default_values"] = validation_result["validated_data"]
        
        if tags is not None:
            update_doc["tags"] = tags
        
        if is_public is not None:
            update_doc["is_public"] = is_public
        
        if shared_with is not None:
            update_doc["shared_with"] = shared_with
        
        # Perform update
        result = await self.templates_collection.update_one(
            {"template_id": template_id},
            {"$set": update_doc}
        )
        
        if result.modified_count == 0:
            raise ResourceNotFoundError(f"Template {template_id} not found")
        
        # Get updated template
        updated_template = await self._get_template_by_id(template_id)
        
        logger.info(
            "template_updated",
            template_id=str(template_id),
            updated_fields=list(update_doc.keys())
        )
        
        return self._to_response(updated_template)
    
    async def delete_template(self, template_id: UUID) -> bool:
        """Delete a template"""
        template = await self._get_template_by_id(template_id)
        if not template:
            raise ResourceNotFoundError(f"Template {template_id} not found")
        
        # Check ownership
        if template.owner_id != self.user_id:
            raise ResourceNotFoundError(f"Template {template_id} not found")
        
        # Delete the template
        result = await self.templates_collection.delete_one({"template_id": template_id})
        
        if result.deleted_count == 0:
            raise ResourceNotFoundError(f"Template {template_id} not found")
        
        logger.info("template_deleted", template_id=str(template_id))
        return True
    
    async def use_template(self, template_id: UUID, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Use a template to generate metadata with optional overrides"""
        template = await self._get_template_by_id(template_id)
        if not template:
            raise ResourceNotFoundError(f"Template {template_id} not found")
        
        # Check access permissions
        if not await self._check_template_access(template):
            raise ResourceNotFoundError(f"Template {template_id} not found")
        
        # Increment usage count
        await self.templates_collection.update_one(
            {"template_id": template_id},
            {"$inc": {"usage_count": 1}}
        )
        
        # Start with template defaults
        metadata = template.default_values.copy()
        
        # Apply overrides if provided
        if overrides:
            metadata.update(overrides)
        
        # Validate final metadata against schema
        schema = await self.schema_service.get_schema(template.schema_id)
        validation_result = await self.validator.validate_metadata(metadata, schema)
        
        logger.info(
            "template_used",
            template_id=str(template_id),
            usage_count=template.usage_count + 1
        )
        
        return {
            "metadata": validation_result["validated_data"],
            "custom_fields": validation_result["custom_fields"],
            "validation_errors": validation_result["errors"],
            "validation_warnings": validation_result["warnings"]
        }
    
    async def duplicate_template(
        self, 
        template_id: UUID, 
        new_name: str,
        new_description: Optional[str] = None
    ) -> TemplateResponse:
        """Duplicate an existing template"""
        template = await self._get_template_by_id(template_id)
        if not template:
            raise ResourceNotFoundError(f"Template {template_id} not found")
        
        # Check access permissions
        if not await self._check_template_access(template):
            raise ResourceNotFoundError(f"Template {template_id} not found")
        
        # Create new template based on existing one
        new_template_data = TemplateCreate(
            name=new_name,
            description=new_description or f"Copy of {template.name}",
            schema_id=template.schema_id,
            default_values=template.default_values,
            category=template.category,
            tags=template.tags,
            is_public=False,  # Duplicates are always private initially
            shared_with=[]
        )
        
        return await self.create_template(new_template_data)
    
    async def get_template_suggestions(
        self, 
        schema_id: UUID, 
        limit: int = 10
    ) -> List[TemplateResponse]:
        """Get template suggestions for a schema"""
        query = {
            "schema_id": schema_id,
            "$or": [
                {"owner_id": self.user_id},
                {"is_public": True},
                {"shared_with": self.user_id}
            ]
        }
        
        cursor = self.templates_collection.find(query)
        cursor = cursor.sort("usage_count", DESCENDING).limit(limit)
        
        templates = []
        async for doc in cursor:
            template = MetadataTemplate(**doc)
            templates.append(self._to_response(template))
        
        return templates
    
    async def get_popular_templates(
        self, 
        category: Optional[str] = None, 
        limit: int = 10
    ) -> List[TemplateResponse]:
        """Get popular public templates"""
        query = {"is_public": True}
        
        if category:
            query["category"] = category
        
        cursor = self.templates_collection.find(query)
        cursor = cursor.sort("usage_count", DESCENDING).limit(limit)
        
        templates = []
        async for doc in cursor:
            template = MetadataTemplate(**doc)
            templates.append(self._to_response(template))
        
        return templates
    
    async def share_template(
        self, 
        template_id: UUID, 
        user_ids: List[UUID]
    ) -> TemplateResponse:
        """Share a template with specific users"""
        template = await self._get_template_by_id(template_id)
        if not template:
            raise ResourceNotFoundError(f"Template {template_id} not found")
        
        # Check ownership
        if template.owner_id != self.user_id:
            raise ResourceNotFoundError(f"Template {template_id} not found")
        
        # Update shared_with list
        current_shared = set(template.shared_with)
        new_shared = current_shared.union(set(user_ids))
        
        await self.templates_collection.update_one(
            {"template_id": template_id},
            {"$set": {"shared_with": list(new_shared)}}
        )
        
        # Get updated template
        updated_template = await self._get_template_by_id(template_id)
        
        logger.info(
            "template_shared",
            template_id=str(template_id),
            shared_with_count=len(new_shared)
        )
        
        return self._to_response(updated_template)
    
    async def unshare_template(
        self, 
        template_id: UUID, 
        user_ids: List[UUID]
    ) -> TemplateResponse:
        """Unshare a template from specific users"""
        template = await self._get_template_by_id(template_id)
        if not template:
            raise ResourceNotFoundError(f"Template {template_id} not found")
        
        # Check ownership
        if template.owner_id != self.user_id:
            raise ResourceNotFoundError(f"Template {template_id} not found")
        
        # Update shared_with list
        current_shared = set(template.shared_with)
        new_shared = current_shared.difference(set(user_ids))
        
        await self.templates_collection.update_one(
            {"template_id": template_id},
            {"$set": {"shared_with": list(new_shared)}}
        )
        
        # Get updated template
        updated_template = await self._get_template_by_id(template_id)
        
        logger.info(
            "template_unshared",
            template_id=str(template_id),
            shared_with_count=len(new_shared)
        )
        
        return self._to_response(updated_template)
    
    async def get_template_statistics(self) -> Dict[str, Any]:
        """Get template statistics"""
        try:
            # Basic counts
            total_templates = await self.templates_collection.count_documents({})
            public_templates = await self.templates_collection.count_documents({"is_public": True})
            user_templates = await self.templates_collection.count_documents({"owner_id": self.user_id})
            
            # Category statistics
            category_stats = await self.templates_collection.aggregate([
                {"$group": {
                    "_id": "$category",
                    "count": {"$sum": 1},
                    "avg_usage": {"$avg": "$usage_count"}
                }},
                {"$sort": {"count": -1}}
            ]).to_list(length=20)
            
            # Most used templates
            popular_templates = await self.templates_collection.aggregate([
                {"$match": {"is_public": True}},
                {"$sort": {"usage_count": -1}},
                {"$limit": 10},
                {"$project": {
                    "name": 1,
                    "usage_count": 1,
                    "category": 1
                }}
            ]).to_list(length=10)
            
            return {
                "total_templates": total_templates,
                "public_templates": public_templates,
                "user_templates": user_templates,
                "category_statistics": category_stats,
                "popular_templates": popular_templates,
                "generated_at": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error("template_statistics_failed", error=str(e))
            raise
    
    async def _get_template_by_id(self, template_id: UUID) -> Optional[MetadataTemplate]:
        """Get template by ID"""
        doc = await self.templates_collection.find_one({"template_id": template_id})
        return MetadataTemplate(**doc) if doc else None
    
    async def _check_template_access(self, template: MetadataTemplate) -> bool:
        """Check if user can access template"""
        return (
            template.owner_id == self.user_id or
            template.is_public or
            self.user_id in template.shared_with
        )
    
    def _to_response(self, template: MetadataTemplate) -> TemplateResponse:
        """Convert template to response model"""
        return TemplateResponse(
            id=str(template.id),
            template_id=template.template_id,
            name=template.name,
            description=template.description,
            schema_id=template.schema_id,
            default_values=template.default_values,
            category=template.category,
            tags=template.tags,
            is_public=template.is_public,
            owner_id=template.owner_id,
            shared_with=template.shared_with,
            created_at=template.created_at,
            updated_at=template.updated_at,
            usage_count=template.usage_count
        )