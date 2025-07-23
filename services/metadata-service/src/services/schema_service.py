"""
Schema Management Service

This module provides business logic for managing metadata schemas.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
import structlog
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, TEXT
from pymongo.errors import DuplicateKeyError

from ..db.models import (
    MetadataSchema, FieldDefinition, SchemaStatus,
    FieldType, MetadataDocument
)
from ..models.schemas import (
    SchemaCreate, SchemaUpdate, SchemaResponse,
    PaginationParams, PaginatedResponse
)
from ..core.exceptions import (
    ResourceNotFoundError, DuplicateResourceError,
    ValidationError, ConflictError
)

logger = structlog.get_logger()


class SchemaService:
    """Service for managing metadata schemas"""
    
    def __init__(self, db: AsyncIOMotorDatabase, user_id: UUID):
        self.db = db
        self.user_id = user_id
        self.schemas_collection = db.metadata_schemas
        self.metadata_collection = db.metadata_documents
    
    async def create_schema(self, schema_data: SchemaCreate) -> SchemaResponse:
        """Create a new metadata schema"""
        try:
            # Check if schema name already exists
            existing = await self.schemas_collection.find_one({"name": schema_data.name})
            if existing:
                raise DuplicateResourceError(f"Schema with name '{schema_data.name}' already exists")
            
            # Validate parent schema if specified
            parent_fields = []
            if schema_data.parent_schema_id:
                parent = await self._get_schema_by_id(schema_data.parent_schema_id)
                if not parent:
                    raise ResourceNotFoundError(f"Parent schema {schema_data.parent_schema_id} not found")
                
                if schema_data.inherit_fields:
                    parent_fields = parent.fields
            
            # Validate field definitions
            field_names = set()
            for field in schema_data.fields:
                if field.name in field_names:
                    raise ValidationError(f"Duplicate field name: {field.name}")
                field_names.add(field.name)
                
                # Validate field-specific constraints
                self._validate_field_definition(field)
            
            # Check for conflicts with inherited fields
            if parent_fields:
                parent_field_names = {f.name for f in parent_fields}
                conflicts = field_names.intersection(parent_field_names)
                if conflicts:
                    raise ValidationError(
                        f"Fields conflict with parent schema: {', '.join(conflicts)}"
                    )
            
            # Create schema document
            schema = MetadataSchema(
                schema_id=uuid4(),
                name=schema_data.name,
                display_name=schema_data.display_name,
                description=schema_data.description,
                version=1,
                category=schema_data.category,
                asset_types=schema_data.asset_types,
                fields=schema_data.fields,
                parent_schema_id=schema_data.parent_schema_id,
                inherit_fields=schema_data.inherit_fields,
                status=SchemaStatus.DRAFT,
                is_system=False,
                is_default=False,
                created_by=self.user_id,
                created_at=datetime.utcnow(),
                allow_custom_fields=schema_data.allow_custom_fields,
                strict_mode=schema_data.strict_mode
            )
            
            # Insert into database
            result = await self.schemas_collection.insert_one(
                schema.dict(by_alias=True, exclude_none=True)
            )
            schema.id = result.inserted_id
            
            logger.info(
                "schema_created",
                schema_id=str(schema.schema_id),
                name=schema.name,
                category=schema.category
            )
            
            return self._to_response(schema, parent_fields)
            
        except DuplicateKeyError:
            raise DuplicateResourceError(f"Schema with name '{schema_data.name}' already exists")
        except Exception as e:
            logger.error("schema_creation_failed", error=str(e))
            raise
    
    async def get_schema(self, schema_id: UUID) -> SchemaResponse:
        """Get a schema by ID"""
        schema = await self._get_schema_by_id(schema_id)
        if not schema:
            raise ResourceNotFoundError(f"Schema {schema_id} not found")
        
        # Get parent fields if inherited
        parent_fields = []
        if schema.parent_schema_id and schema.inherit_fields:
            parent = await self._get_schema_by_id(schema.parent_schema_id)
            if parent:
                parent_fields = parent.fields
        
        return self._to_response(schema, parent_fields)
    
    async def list_schemas(
        self,
        pagination: PaginationParams,
        category: Optional[str] = None,
        status: Optional[SchemaStatus] = None,
        search: Optional[str] = None
    ) -> PaginatedResponse:
        """List schemas with filtering and pagination"""
        # Build query
        query = {}
        
        if category:
            query["category"] = category
        
        if status:
            query["status"] = status
        
        if search:
            query["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"display_name": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}}
            ]
        
        # Get total count
        total = await self.schemas_collection.count_documents(query)
        
        # Get paginated results
        cursor = self.schemas_collection.find(query)
        cursor = cursor.skip(pagination.offset).limit(pagination.page_size)
        cursor = cursor.sort("created_at", DESCENDING)
        
        schemas = []
        async for doc in cursor:
            schema = MetadataSchema(**doc)
            schemas.append(self._to_response(schema))
        
        return PaginatedResponse(
            items=schemas,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            pages=(total + pagination.page_size - 1) // pagination.page_size
        )
    
    async def update_schema(
        self,
        schema_id: UUID,
        update_data: SchemaUpdate
    ) -> SchemaResponse:
        """Update a schema"""
        schema = await self._get_schema_by_id(schema_id)
        if not schema:
            raise ResourceNotFoundError(f"Schema {schema_id} not found")
        
        if schema.is_system:
            raise ValidationError("System schemas cannot be modified")
        
        # Check if schema is in use
        if schema.status == SchemaStatus.ACTIVE:
            metadata_count = await self.metadata_collection.count_documents(
                {"schema_id": schema_id}
            )
            if metadata_count > 0:
                # Only allow safe updates for active schemas
                if update_data.fields is not None:
                    raise ConflictError(
                        "Cannot modify fields of active schema with existing metadata. "
                        "Create a new version instead."
                    )
        
        # Build update document
        update_doc = {"updated_at": datetime.utcnow(), "updated_by": self.user_id}
        
        if update_data.display_name is not None:
            update_doc["display_name"] = update_data.display_name
        
        if update_data.description is not None:
            update_doc["description"] = update_data.description
        
        if update_data.asset_types is not None:
            update_doc["asset_types"] = update_data.asset_types
        
        if update_data.allow_custom_fields is not None:
            update_doc["allow_custom_fields"] = update_data.allow_custom_fields
        
        if update_data.strict_mode is not None:
            update_doc["strict_mode"] = update_data.strict_mode
        
        # Update fields only if schema is not active or has no metadata
        if update_data.fields is not None and schema.status != SchemaStatus.ACTIVE:
            # Validate new fields
            field_names = set()
            for field in update_data.fields:
                if field.name in field_names:
                    raise ValidationError(f"Duplicate field name: {field.name}")
                field_names.add(field.name)
                self._validate_field_definition(field)
            
            update_doc["fields"] = [f.dict() for f in update_data.fields]
        
        # Update status
        if update_data.status is not None:
            if schema.status == SchemaStatus.ARCHIVED:
                raise ValidationError("Cannot change status of archived schema")
            update_doc["status"] = update_data.status
        
        # Perform update
        result = await self.schemas_collection.update_one(
            {"schema_id": schema_id},
            {"$set": update_doc}
        )
        
        if result.modified_count == 0:
            raise ResourceNotFoundError(f"Schema {schema_id} not found")
        
        # Get updated schema
        updated_schema = await self._get_schema_by_id(schema_id)
        
        logger.info(
            "schema_updated",
            schema_id=str(schema_id),
            updated_fields=list(update_doc.keys())
        )
        
        return self._to_response(updated_schema)
    
    async def delete_schema(self, schema_id: UUID) -> bool:
        """Delete a schema"""
        schema = await self._get_schema_by_id(schema_id)
        if not schema:
            raise ResourceNotFoundError(f"Schema {schema_id} not found")
        
        if schema.is_system:
            raise ValidationError("System schemas cannot be deleted")
        
        # Check if schema is in use
        metadata_count = await self.metadata_collection.count_documents(
            {"schema_id": schema_id}
        )
        if metadata_count > 0:
            raise ConflictError(
                f"Cannot delete schema with {metadata_count} associated metadata records"
            )
        
        # Check if other schemas inherit from this one
        child_count = await self.schemas_collection.count_documents(
            {"parent_schema_id": schema_id}
        )
        if child_count > 0:
            raise ConflictError(
                f"Cannot delete schema with {child_count} child schemas"
            )
        
        # Delete the schema
        result = await self.schemas_collection.delete_one({"schema_id": schema_id})
        
        if result.deleted_count == 0:
            raise ResourceNotFoundError(f"Schema {schema_id} not found")
        
        logger.info("schema_deleted", schema_id=str(schema_id))
        
        return True
    
    async def create_version(
        self,
        schema_id: UUID,
        changes: Optional[Dict[str, Any]] = None
    ) -> SchemaResponse:
        """Create a new version of a schema"""
        schema = await self._get_schema_by_id(schema_id)
        if not schema:
            raise ResourceNotFoundError(f"Schema {schema_id} not found")
        
        if schema.is_system:
            raise ValidationError("Cannot create versions of system schemas")
        
        # Create new schema based on current one
        new_schema = MetadataSchema(
            schema_id=uuid4(),
            name=f"{schema.name}_v{schema.version + 1}",
            display_name=f"{schema.display_name} (v{schema.version + 1})",
            description=schema.description,
            version=schema.version + 1,
            category=schema.category,
            asset_types=schema.asset_types,
            fields=schema.fields,
            parent_schema_id=schema.parent_schema_id,
            inherit_fields=schema.inherit_fields,
            status=SchemaStatus.DRAFT,
            is_system=False,
            is_default=False,
            created_by=self.user_id,
            created_at=datetime.utcnow(),
            allow_custom_fields=schema.allow_custom_fields,
            strict_mode=schema.strict_mode
        )
        
        # Apply changes if provided
        if changes:
            for key, value in changes.items():
                if hasattr(new_schema, key) and key not in ["id", "schema_id", "version"]:
                    setattr(new_schema, key, value)
        
        # Insert new version
        result = await self.schemas_collection.insert_one(
            new_schema.dict(by_alias=True, exclude_none=True)
        )
        new_schema.id = result.inserted_id
        
        logger.info(
            "schema_version_created",
            original_schema_id=str(schema_id),
            new_schema_id=str(new_schema.schema_id),
            version=new_schema.version
        )
        
        return self._to_response(new_schema)
    
    async def get_schema_by_name(self, name: str) -> Optional[MetadataSchema]:
        """Get schema by name"""
        doc = await self.schemas_collection.find_one({"name": name})
        return MetadataSchema(**doc) if doc else None
    
    async def get_default_schema(self, category: str) -> Optional[MetadataSchema]:
        """Get default schema for a category"""
        doc = await self.schemas_collection.find_one({
            "category": category,
            "is_default": True,
            "status": SchemaStatus.ACTIVE
        })
        return MetadataSchema(**doc) if doc else None
    
    async def _get_schema_by_id(self, schema_id: UUID) -> Optional[MetadataSchema]:
        """Get schema by ID"""
        doc = await self.schemas_collection.find_one({"schema_id": schema_id})
        return MetadataSchema(**doc) if doc else None
    
    def _validate_field_definition(self, field: FieldDefinition):
        """Validate field definition"""
        # Validate array type
        if field.field_type == FieldType.ARRAY and not field.array_type:
            raise ValidationError(f"Array field '{field.name}' must specify array_type")
        
        # Validate object schema
        if field.field_type == FieldType.OBJECT and field.object_schema:
            # Recursively validate nested fields
            nested_names = set()
            for nested_field in field.object_schema:
                if nested_field.name in nested_names:
                    raise ValidationError(
                        f"Duplicate nested field name in '{field.name}': {nested_field.name}"
                    )
                nested_names.add(nested_field.name)
                self._validate_field_definition(nested_field)
        
        # Validate reference
        if field.field_type == FieldType.REFERENCE and not field.reference_collection:
            raise ValidationError(
                f"Reference field '{field.name}' must specify reference_collection"
            )
        
        # Validate enum
        if field.field_type == FieldType.ENUM:
            enum_values = field.constraints.get("enum_values")
            if not enum_values or not isinstance(enum_values, list):
                raise ValidationError(
                    f"Enum field '{field.name}' must have enum_values constraint"
                )
    
    def _to_response(
        self,
        schema: MetadataSchema,
        inherited_fields: Optional[List[FieldDefinition]] = None
    ) -> SchemaResponse:
        """Convert schema to response model"""
        # Combine inherited and own fields
        all_fields = []
        if inherited_fields:
            all_fields.extend(inherited_fields)
        all_fields.extend(schema.fields)
        
        return SchemaResponse(
            id=str(schema.id),
            schema_id=schema.schema_id,
            name=schema.name,
            display_name=schema.display_name,
            description=schema.description,
            version=schema.version,
            category=schema.category,
            asset_types=schema.asset_types,
            fields=schema.fields,
            all_fields=all_fields,
            parent_schema_id=schema.parent_schema_id,
            inherit_fields=schema.inherit_fields,
            status=schema.status,
            is_system=schema.is_system,
            is_default=schema.is_default,
            created_by=schema.created_by,
            created_at=schema.created_at,
            updated_by=schema.updated_by,
            updated_at=schema.updated_at,
            allow_custom_fields=schema.allow_custom_fields,
            strict_mode=schema.strict_mode
        )