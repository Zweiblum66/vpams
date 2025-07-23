"""
Metadata Service

This module provides business logic for managing metadata documents.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
import structlog
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, TEXT
from pymongo.errors import DuplicateKeyError
from bson import ObjectId

from ..db.models import (
    MetadataDocument, MetadataSchema, FieldDefinition, 
    SchemaStatus, FieldType
)
from ..models.schemas import (
    MetadataCreate, MetadataUpdate, MetadataResponse,
    PaginationParams, PaginatedResponse, ValidationResult
)
from ..services.metadata_validator import MetadataValidator
from ..services.schema_service import SchemaService
from ..core.exceptions import (
    ResourceNotFoundError, DuplicateResourceError,
    ValidationError, ConflictError
)

logger = structlog.get_logger()


class MetadataService:
    """Service for managing metadata documents"""
    
    def __init__(self, db: AsyncIOMotorDatabase, user_id: UUID):
        self.db = db
        self.user_id = user_id
        self.metadata_collection = db.metadata_documents
        self.schemas_collection = db.metadata_schemas
        self.validator = MetadataValidator()
        self.schema_service = SchemaService(db, user_id)
    
    async def create_metadata(self, metadata_data: MetadataCreate) -> MetadataResponse:
        """Create a new metadata document"""
        try:
            # Get and validate schema
            schema = await self.schema_service.get_schema(metadata_data.schema_id)
            if not schema:
                raise ResourceNotFoundError(f"Schema {metadata_data.schema_id} not found")
            
            # Validate metadata against schema
            validation_result = await self.validator.validate_metadata(
                metadata_data.metadata,
                schema,
                metadata_data.custom_fields
            )
            
            # Create metadata document
            metadata_doc = MetadataDocument(
                asset_id=metadata_data.asset_id,
                schema_id=metadata_data.schema_id,
                schema_version=schema.version,
                metadata=validation_result["validated_data"],
                custom_fields=validation_result["custom_fields"],
                is_valid=validation_result["valid"],
                validation_errors=validation_result["errors"],
                created_by=self.user_id,
                created_at=datetime.utcnow(),
                source=metadata_data.source,
                source_details=metadata_data.source_details or {}
            )
            
            # Insert into database
            result = await self.metadata_collection.insert_one(
                metadata_doc.dict(by_alias=True, exclude_none=True)
            )
            metadata_doc.id = result.inserted_id
            
            logger.info(
                "metadata_created",
                metadata_id=str(metadata_doc.id),
                asset_id=str(metadata_data.asset_id),
                schema_id=str(metadata_data.schema_id),
                valid=validation_result["valid"]
            )
            
            return self._to_response(metadata_doc)
            
        except Exception as e:
            logger.error("metadata_creation_failed", error=str(e))
            raise
    
    async def get_metadata(self, metadata_id: str) -> MetadataResponse:
        """Get a metadata document by ID"""
        if not ObjectId.is_valid(metadata_id):
            raise ValidationError("Invalid metadata ID format")
        
        doc = await self.metadata_collection.find_one({"_id": ObjectId(metadata_id)})
        if not doc:
            raise ResourceNotFoundError(f"Metadata {metadata_id} not found")
        
        metadata_doc = MetadataDocument(**doc)
        return self._to_response(metadata_doc)
    
    async def get_asset_metadata(
        self, 
        asset_id: UUID, 
        schema_id: Optional[UUID] = None,
        current_only: bool = True
    ) -> List[MetadataResponse]:
        """Get metadata for an asset"""
        query = {"asset_id": asset_id}
        if schema_id:
            query["schema_id"] = schema_id
        if current_only:
            query["is_current"] = True
        
        cursor = self.metadata_collection.find(query)
        cursor = cursor.sort("created_at", DESCENDING)
        
        metadata_docs = []
        async for doc in cursor:
            metadata_doc = MetadataDocument(**doc)
            metadata_docs.append(self._to_response(metadata_doc))
        
        return metadata_docs
    
    async def update_metadata(
        self, 
        metadata_id: str, 
        update_data: MetadataUpdate
    ) -> MetadataResponse:
        """Update a metadata document with versioning"""
        if not ObjectId.is_valid(metadata_id):
            raise ValidationError("Invalid metadata ID format")
        
        # Get existing metadata
        doc = await self.metadata_collection.find_one({"_id": ObjectId(metadata_id)})
        if not doc:
            raise ResourceNotFoundError(f"Metadata {metadata_id} not found")
        
        existing_metadata = MetadataDocument(**doc)
        
        # Get schema for validation
        schema = await self.schema_service.get_schema(existing_metadata.schema_id)
        if not schema:
            raise ResourceNotFoundError(f"Schema {existing_metadata.schema_id} not found")
        
        # Prepare updated metadata
        updated_metadata = existing_metadata.metadata.copy()
        updated_custom_fields = existing_metadata.custom_fields.copy()
        
        if update_data.metadata:
            if update_data.merge:
                # Merge with existing metadata
                updated_metadata.update(update_data.metadata)
            else:
                # Replace existing metadata
                updated_metadata = update_data.metadata
        
        if update_data.custom_fields:
            if update_data.merge:
                updated_custom_fields.update(update_data.custom_fields)
            else:
                updated_custom_fields = update_data.custom_fields
        
        # Validate updated metadata
        validation_result = await self.validator.validate_metadata(
            updated_metadata,
            schema,
            updated_custom_fields
        )
        
        # Create new version
        new_version = MetadataDocument(
            asset_id=existing_metadata.asset_id,
            schema_id=existing_metadata.schema_id,
            schema_version=existing_metadata.schema_version,
            metadata=validation_result["validated_data"],
            custom_fields=validation_result["custom_fields"],
            is_valid=validation_result["valid"],
            validation_errors=validation_result["errors"],
            version=existing_metadata.version + 1,
            is_current=True,
            parent_version_id=existing_metadata.id,
            created_by=existing_metadata.created_by,
            updated_by=self.user_id,
            updated_at=datetime.utcnow(),
            source=existing_metadata.source,
            source_details=existing_metadata.source_details
        )
        
        # Use transaction to ensure consistency
        async with await self.db.client.start_session() as session:
            async with session.start_transaction():
                # Mark current version as not current
                await self.metadata_collection.update_one(
                    {"_id": ObjectId(metadata_id)},
                    {"$set": {"is_current": False}},
                    session=session
                )
                
                # Insert new version
                result = await self.metadata_collection.insert_one(
                    new_version.dict(by_alias=True, exclude_none=True),
                    session=session
                )
                new_version.id = result.inserted_id
        
        logger.info(
            "metadata_updated",
            metadata_id=metadata_id,
            new_version_id=str(new_version.id),
            asset_id=str(existing_metadata.asset_id),
            version=new_version.version,
            valid=validation_result["valid"]
        )
        
        return self._to_response(new_version)
    
    async def delete_metadata(self, metadata_id: str) -> bool:
        """Delete a metadata document"""
        if not ObjectId.is_valid(metadata_id):
            raise ValidationError("Invalid metadata ID format")
        
        result = await self.metadata_collection.delete_one({"_id": ObjectId(metadata_id)})
        
        if result.deleted_count == 0:
            raise ResourceNotFoundError(f"Metadata {metadata_id} not found")
        
        logger.info("metadata_deleted", metadata_id=metadata_id)
        return True
    
    async def validate_metadata(
        self, 
        asset_id: UUID, 
        schema_id: UUID, 
        metadata: Dict[str, Any],
        strict: Optional[bool] = None
    ) -> ValidationResult:
        """Validate metadata against a schema without saving"""
        # Get schema
        schema = await self.schema_service.get_schema(schema_id)
        if not schema:
            raise ResourceNotFoundError(f"Schema {schema_id} not found")
        
        # Validate metadata
        validation_result = await self.validator.validate_metadata(
            metadata,
            schema,
            strict=strict
        )
        
        return ValidationResult(
            valid=validation_result["valid"],
            errors=validation_result["errors"],
            warnings=validation_result["warnings"],
            validated_data=validation_result["validated_data"],
            custom_fields=validation_result["custom_fields"]
        )
    
    async def search_metadata(
        self, 
        query: Dict[str, Any], 
        pagination: PaginationParams
    ) -> PaginatedResponse:
        """Search metadata documents"""
        try:
            # Build search query
            search_query = {}
            
            # Handle text search
            if "text" in query:
                search_query["$text"] = {"$search": query["text"]}
            
            # Handle field-specific searches
            for field, value in query.items():
                if field == "text":
                    continue
                elif field == "asset_id":
                    search_query["asset_id"] = UUID(value) if isinstance(value, str) else value
                elif field == "schema_id":
                    search_query["schema_id"] = UUID(value) if isinstance(value, str) else value
                elif field.startswith("metadata."):
                    search_query[field] = value
                elif field.startswith("custom_fields."):
                    search_query[field] = value
                else:
                    search_query[field] = value
            
            # Get total count
            total = await self.metadata_collection.count_documents(search_query)
            
            # Get paginated results
            cursor = self.metadata_collection.find(search_query)
            cursor = cursor.skip(pagination.offset).limit(pagination.page_size)
            cursor = cursor.sort("created_at", DESCENDING)
            
            results = []
            async for doc in cursor:
                metadata_doc = MetadataDocument(**doc)
                results.append(self._to_response(metadata_doc))
            
            return PaginatedResponse(
                items=results,
                total=total,
                page=pagination.page,
                page_size=pagination.page_size,
                pages=(total + pagination.page_size - 1) // pagination.page_size
            )
            
        except Exception as e:
            logger.error("metadata_search_failed", error=str(e))
            raise
    
    async def get_metadata_by_asset_and_schema(
        self, 
        asset_id: UUID, 
        schema_id: UUID
    ) -> Optional[MetadataResponse]:
        """Get metadata for a specific asset and schema combination"""
        doc = await self.metadata_collection.find_one({
            "asset_id": asset_id,
            "schema_id": schema_id
        })
        
        if not doc:
            return None
        
        metadata_doc = MetadataDocument(**doc)
        return self._to_response(metadata_doc)
    
    async def bulk_create_metadata(
        self, 
        metadata_list: List[MetadataCreate]
    ) -> List[MetadataResponse]:
        """Create multiple metadata documents"""
        results = []
        
        for metadata_data in metadata_list:
            try:
                result = await self.create_metadata(metadata_data)
                results.append(result)
            except Exception as e:
                logger.error(
                    "bulk_metadata_creation_failed",
                    asset_id=str(metadata_data.asset_id),
                    schema_id=str(metadata_data.schema_id),
                    error=str(e)
                )
                # Continue with next item instead of failing entire batch
                continue
        
        return results
    
    async def bulk_update_metadata(
        self, 
        updates: List[Dict[str, Any]]
    ) -> List[MetadataResponse]:
        """Update multiple metadata documents"""
        results = []
        
        for update_info in updates:
            try:
                metadata_id = update_info["metadata_id"]
                update_data = MetadataUpdate(**update_info["update_data"])
                result = await self.update_metadata(metadata_id, update_data)
                results.append(result)
            except Exception as e:
                logger.error(
                    "bulk_metadata_update_failed",
                    metadata_id=update_info.get("metadata_id"),
                    error=str(e)
                )
                continue
        
        return results
    
    async def get_metadata_statistics(self) -> Dict[str, Any]:
        """Get metadata statistics"""
        try:
            # Basic counts
            total_metadata = await self.metadata_collection.count_documents({})
            valid_metadata = await self.metadata_collection.count_documents({"is_valid": True})
            invalid_metadata = await self.metadata_collection.count_documents({"is_valid": False})
            
            # Schema usage statistics
            schema_stats = await self.metadata_collection.aggregate([
                {"$group": {
                    "_id": "$schema_id",
                    "count": {"$sum": 1}
                }},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]).to_list(length=10)
            
            # Asset metadata coverage
            asset_stats = await self.metadata_collection.aggregate([
                {"$group": {
                    "_id": "$asset_id",
                    "metadata_count": {"$sum": 1}
                }},
                {"$group": {
                    "_id": None,
                    "total_assets": {"$sum": 1},
                    "avg_metadata_per_asset": {"$avg": "$metadata_count"}
                }}
            ]).to_list(length=1)
            
            return {
                "total_metadata": total_metadata,
                "valid_metadata": valid_metadata,
                "invalid_metadata": invalid_metadata,
                "validation_rate": (valid_metadata / total_metadata) if total_metadata > 0 else 0,
                "schema_usage": schema_stats,
                "asset_coverage": asset_stats[0] if asset_stats else {},
                "generated_at": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error("metadata_statistics_failed", error=str(e))
            raise
    
    # Version Management Methods
    async def get_metadata_versions(
        self, 
        asset_id: UUID, 
        schema_id: Optional[UUID] = None
    ) -> List[MetadataResponse]:
        """Get all versions of metadata for an asset"""
        query = {"asset_id": asset_id}
        if schema_id:
            query["schema_id"] = schema_id
        
        cursor = self.metadata_collection.find(query)
        cursor = cursor.sort("version", DESCENDING)
        
        metadata_docs = []
        async for doc in cursor:
            metadata_doc = MetadataDocument(**doc)
            metadata_docs.append(self._to_response(metadata_doc))
        
        return metadata_docs
    
    async def get_metadata_version(
        self, 
        asset_id: UUID, 
        schema_id: UUID, 
        version: int
    ) -> MetadataResponse:
        """Get a specific version of metadata"""
        query = {
            "asset_id": asset_id,
            "schema_id": schema_id,
            "version": version
        }
        
        doc = await self.metadata_collection.find_one(query)
        if not doc:
            raise ResourceNotFoundError(
                f"Metadata version {version} not found for asset {asset_id} and schema {schema_id}"
            )
        
        metadata_doc = MetadataDocument(**doc)
        return self._to_response(metadata_doc)
    
    async def restore_metadata_version(
        self, 
        asset_id: UUID, 
        schema_id: UUID, 
        version: int
    ) -> MetadataResponse:
        """Restore a specific version of metadata as current"""
        # Get the version to restore
        version_doc = await self.metadata_collection.find_one({
            "asset_id": asset_id,
            "schema_id": schema_id,
            "version": version
        })
        
        if not version_doc:
            raise ResourceNotFoundError(
                f"Metadata version {version} not found for asset {asset_id} and schema {schema_id}"
            )
        
        version_metadata = MetadataDocument(**version_doc)
        
        # Get current version
        current_doc = await self.metadata_collection.find_one({
            "asset_id": asset_id,
            "schema_id": schema_id,
            "is_current": True
        })
        
        if not current_doc:
            raise ResourceNotFoundError(
                f"Current metadata not found for asset {asset_id} and schema {schema_id}"
            )
        
        current_metadata = MetadataDocument(**current_doc)
        
        # Create new version based on the version to restore
        new_version = MetadataDocument(
            asset_id=version_metadata.asset_id,
            schema_id=version_metadata.schema_id,
            schema_version=version_metadata.schema_version,
            metadata=version_metadata.metadata,
            custom_fields=version_metadata.custom_fields,
            is_valid=version_metadata.is_valid,
            validation_errors=version_metadata.validation_errors,
            version=current_metadata.version + 1,
            is_current=True,
            parent_version_id=current_metadata.id,
            created_by=version_metadata.created_by,
            updated_by=self.user_id,
            updated_at=datetime.utcnow(),
            source=f"restored_from_version_{version}",
            source_details={"restored_from_version": version}
        )
        
        # Use transaction to ensure consistency
        async with await self.db.client.start_session() as session:
            async with session.start_transaction():
                # Mark current version as not current
                await self.metadata_collection.update_one(
                    {"_id": current_metadata.id},
                    {"$set": {"is_current": False}},
                    session=session
                )
                
                # Insert restored version
                result = await self.metadata_collection.insert_one(
                    new_version.dict(by_alias=True, exclude_none=True),
                    session=session
                )
                new_version.id = result.inserted_id
        
        logger.info(
            "metadata_version_restored",
            asset_id=str(asset_id),
            schema_id=str(schema_id),
            restored_version=version,
            new_version=new_version.version
        )
        
        return self._to_response(new_version)
    
    async def compare_metadata_versions(
        self, 
        asset_id: UUID, 
        schema_id: UUID, 
        version1: int, 
        version2: int
    ) -> Dict[str, Any]:
        """Compare two versions of metadata"""
        # Get both versions
        version1_doc = await self.metadata_collection.find_one({
            "asset_id": asset_id,
            "schema_id": schema_id,
            "version": version1
        })
        
        version2_doc = await self.metadata_collection.find_one({
            "asset_id": asset_id,
            "schema_id": schema_id,
            "version": version2
        })
        
        if not version1_doc:
            raise ResourceNotFoundError(f"Version {version1} not found")
        
        if not version2_doc:
            raise ResourceNotFoundError(f"Version {version2} not found")
        
        v1_metadata = MetadataDocument(**version1_doc)
        v2_metadata = MetadataDocument(**version2_doc)
        
        # Compare metadata fields
        v1_fields = set(v1_metadata.metadata.keys())
        v2_fields = set(v2_metadata.metadata.keys())
        
        added_fields = v2_fields - v1_fields
        removed_fields = v1_fields - v2_fields
        common_fields = v1_fields & v2_fields
        
        changed_fields = {}
        for field in common_fields:
            if v1_metadata.metadata[field] != v2_metadata.metadata[field]:
                changed_fields[field] = {
                    "old_value": v1_metadata.metadata[field],
                    "new_value": v2_metadata.metadata[field]
                }
        
        return {
            "version1": version1,
            "version2": version2,
            "added_fields": list(added_fields),
            "removed_fields": list(removed_fields),
            "changed_fields": changed_fields,
            "total_changes": len(added_fields) + len(removed_fields) + len(changed_fields)
        }
    
    async def get_metadata_history(
        self, 
        asset_id: UUID, 
        schema_id: UUID, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get metadata change history"""
        cursor = self.metadata_collection.find({
            "asset_id": asset_id,
            "schema_id": schema_id
        })
        cursor = cursor.sort("version", DESCENDING).limit(limit)
        
        history = []
        async for doc in cursor:
            metadata_doc = MetadataDocument(**doc)
            history.append({
                "version": metadata_doc.version,
                "is_current": metadata_doc.is_current,
                "created_at": metadata_doc.created_at,
                "updated_at": metadata_doc.updated_at,
                "created_by": metadata_doc.created_by,
                "updated_by": metadata_doc.updated_by,
                "source": metadata_doc.source,
                "is_valid": metadata_doc.is_valid,
                "validation_errors_count": len(metadata_doc.validation_errors)
            })
        
        return history
    
    def _to_response(self, metadata_doc: MetadataDocument) -> MetadataResponse:
        """Convert metadata document to response model"""
        return MetadataResponse(
            id=str(metadata_doc.id),
            asset_id=metadata_doc.asset_id,
            schema_id=metadata_doc.schema_id,
            schema_version=metadata_doc.schema_version,
            metadata=metadata_doc.metadata,
            custom_fields=metadata_doc.custom_fields,
            is_valid=metadata_doc.is_valid,
            validation_errors=metadata_doc.validation_errors,
            version=metadata_doc.version,
            is_current=metadata_doc.is_current,
            parent_version_id=str(metadata_doc.parent_version_id) if metadata_doc.parent_version_id else None,
            created_by=metadata_doc.created_by,
            created_at=metadata_doc.created_at,
            updated_by=metadata_doc.updated_by,
            updated_at=metadata_doc.updated_at,
            source=metadata_doc.source,
            source_details=metadata_doc.source_details
        )