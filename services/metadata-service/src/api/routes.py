"""
API Routes for Metadata Service

This module defines all API endpoints for the metadata service.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
import structlog

from ..db.database import get_db
from ..core.auth import get_current_user
from ..models.schemas import (
    SchemaCreate, SchemaUpdate, SchemaResponse,
    MetadataCreate, MetadataUpdate, MetadataResponse,
    TemplateCreate, TemplateResponse,
    PaginationParams, PaginatedResponse,
    ValidationResult, ExtractionRequest
)
from ..services.schema_service import SchemaService
from ..services.metadata_service import MetadataService
from ..services.extraction_service import ExtractionService
from ..services.template_service import TemplateService
from ..core.exceptions import (
    NotFoundError, DuplicateResourceError,
    ValidationError, ConflictError
)

logger = structlog.get_logger()

# Create routers
schema_router = APIRouter(prefix="/api/v1/schemas", tags=["schemas"])
metadata_router = APIRouter(prefix="/api/v1/metadata", tags=["metadata"])
template_router = APIRouter(prefix="/api/v1/templates", tags=["templates"])
extraction_router = APIRouter(prefix="/api/v1/extract", tags=["extraction"])
search_router = APIRouter(prefix="/api/v1/search", tags=["search"])


# Schema Management Endpoints
@schema_router.post("/", response_model=SchemaResponse, status_code=status.HTTP_201_CREATED)
async def create_schema(
    schema_data: SchemaCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new metadata schema"""
    try:
        service = SchemaService(db, current_user["user_id"])
        return await service.create_schema(schema_data)
    except DuplicateResourceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("Failed to create schema", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@schema_router.get("/", response_model=PaginatedResponse)
async def list_schemas(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List metadata schemas with filtering and pagination"""
    try:
        pagination = PaginationParams(page=page, page_size=page_size)
        service = SchemaService(db, current_user["user_id"])
        return await service.list_schemas(pagination, category, status, search)
    except Exception as e:
        logger.error("Failed to list schemas", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@schema_router.get("/{schema_id}", response_model=SchemaResponse)
async def get_schema(
    schema_id: UUID,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get a specific metadata schema"""
    try:
        service = SchemaService(db, current_user["user_id"])
        return await service.get_schema(schema_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to get schema", error=str(e), schema_id=str(schema_id))
        raise HTTPException(status_code=500, detail="Internal server error")


@schema_router.put("/{schema_id}", response_model=SchemaResponse)
async def update_schema(
    schema_id: UUID,
    update_data: SchemaUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a metadata schema"""
    try:
        service = SchemaService(db, current_user["user_id"])
        return await service.update_schema(schema_id, update_data)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error("Failed to update schema", error=str(e), schema_id=str(schema_id))
        raise HTTPException(status_code=500, detail="Internal server error")


@schema_router.delete("/{schema_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schema(
    schema_id: UUID,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a metadata schema"""
    try:
        service = SchemaService(db, current_user["user_id"])
        await service.delete_schema(schema_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error("Failed to delete schema", error=str(e), schema_id=str(schema_id))
        raise HTTPException(status_code=500, detail="Internal server error")


@schema_router.post("/{schema_id}/version", response_model=SchemaResponse)
async def create_schema_version(
    schema_id: UUID,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new version of a schema"""
    try:
        service = SchemaService(db, current_user["user_id"])
        return await service.create_version(schema_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("Failed to create schema version", error=str(e), schema_id=str(schema_id))
        raise HTTPException(status_code=500, detail="Internal server error")


# Metadata Operations Endpoints
@metadata_router.post("/", response_model=MetadataResponse, status_code=status.HTTP_201_CREATED)
async def create_metadata(
    metadata_data: MetadataCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create metadata for an asset"""
    try:
        service = MetadataService(db, current_user["user_id"])
        return await service.create_metadata(metadata_data)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("Failed to create metadata", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@metadata_router.get("/asset/{asset_id}", response_model=List[MetadataResponse])
async def get_asset_metadata(
    asset_id: UUID,
    schema_id: Optional[UUID] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all metadata for an asset"""
    try:
        service = MetadataService(db, current_user["user_id"])
        return await service.get_asset_metadata(asset_id, schema_id)
    except Exception as e:
        logger.error("Failed to get asset metadata", error=str(e), asset_id=str(asset_id))
        raise HTTPException(status_code=500, detail="Internal server error")


@metadata_router.get("/{metadata_id}", response_model=MetadataResponse)
async def get_metadata(
    metadata_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get specific metadata document"""
    try:
        service = MetadataService(db, current_user["user_id"])
        return await service.get_metadata(metadata_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to get metadata", error=str(e), metadata_id=metadata_id)
        raise HTTPException(status_code=500, detail="Internal server error")


@metadata_router.put("/{metadata_id}", response_model=MetadataResponse)
async def update_metadata(
    metadata_id: str,
    update_data: MetadataUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update metadata document"""
    try:
        service = MetadataService(db, current_user["user_id"])
        return await service.update_metadata(metadata_id, update_data)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("Failed to update metadata", error=str(e), metadata_id=metadata_id)
        raise HTTPException(status_code=500, detail="Internal server error")


@metadata_router.delete("/{metadata_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_metadata(
    metadata_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete metadata document"""
    try:
        service = MetadataService(db, current_user["user_id"])
        await service.delete_metadata(metadata_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to delete metadata", error=str(e), metadata_id=metadata_id)
        raise HTTPException(status_code=500, detail="Internal server error")


@metadata_router.post("/validate", response_model=ValidationResult)
async def validate_metadata(
    asset_id: UUID,
    schema_id: UUID,
    metadata: dict,
    strict: Optional[bool] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Validate metadata against a schema without saving"""
    try:
        service = MetadataService(db, current_user["user_id"])
        return await service.validate_metadata(asset_id, schema_id, metadata, strict)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to validate metadata", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


# Version Management Endpoints
@metadata_router.get("/asset/{asset_id}/versions", response_model=List[MetadataResponse])
async def get_metadata_versions(
    asset_id: UUID,
    schema_id: Optional[UUID] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all versions of metadata for an asset"""
    try:
        service = MetadataService(db, current_user["user_id"])
        return await service.get_metadata_versions(asset_id, schema_id)
    except Exception as e:
        logger.error("Failed to get metadata versions", error=str(e), asset_id=str(asset_id))
        raise HTTPException(status_code=500, detail="Internal server error")


@metadata_router.get("/asset/{asset_id}/version/{version}", response_model=MetadataResponse)
async def get_metadata_version(
    asset_id: UUID,
    schema_id: UUID,
    version: int,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get a specific version of metadata"""
    try:
        service = MetadataService(db, current_user["user_id"])
        return await service.get_metadata_version(asset_id, schema_id, version)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to get metadata version", error=str(e), asset_id=str(asset_id))
        raise HTTPException(status_code=500, detail="Internal server error")


@metadata_router.post("/asset/{asset_id}/restore/{version}", response_model=MetadataResponse)
async def restore_metadata_version(
    asset_id: UUID,
    schema_id: UUID,
    version: int,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Restore a specific version of metadata as current"""
    try:
        service = MetadataService(db, current_user["user_id"])
        return await service.restore_metadata_version(asset_id, schema_id, version)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to restore metadata version", error=str(e), asset_id=str(asset_id))
        raise HTTPException(status_code=500, detail="Internal server error")


@metadata_router.get("/asset/{asset_id}/compare/{version1}/{version2}")
async def compare_metadata_versions(
    asset_id: UUID,
    schema_id: UUID,
    version1: int,
    version2: int,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Compare two versions of metadata"""
    try:
        service = MetadataService(db, current_user["user_id"])
        return await service.compare_metadata_versions(asset_id, schema_id, version1, version2)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to compare metadata versions", error=str(e), asset_id=str(asset_id))
        raise HTTPException(status_code=500, detail="Internal server error")


@metadata_router.get("/asset/{asset_id}/history")
async def get_metadata_history(
    asset_id: UUID,
    schema_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get metadata change history"""
    try:
        service = MetadataService(db, current_user["user_id"])
        return await service.get_metadata_history(asset_id, schema_id, limit)
    except Exception as e:
        logger.error("Failed to get metadata history", error=str(e), asset_id=str(asset_id))
        raise HTTPException(status_code=500, detail="Internal server error")


# Template Management Endpoints
@template_router.post("/", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    template_data: TemplateCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new metadata template"""
    try:
        service = TemplateService(db, current_user["user_id"])
        return await service.create_template(template_data)
    except DuplicateResourceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("Failed to create template", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@template_router.get("/", response_model=PaginatedResponse)
async def list_templates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    schema_id: Optional[UUID] = None,
    tags: Optional[List[str]] = Query(None),
    public_only: bool = Query(False),
    search: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List metadata templates with filtering and pagination"""
    try:
        pagination = PaginationParams(page=page, page_size=page_size)
        service = TemplateService(db, current_user["user_id"])
        return await service.list_templates(
            pagination, category, schema_id, tags, public_only, search
        )
    except Exception as e:
        logger.error("Failed to list templates", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@template_router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: UUID,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get a specific metadata template"""
    try:
        service = TemplateService(db, current_user["user_id"])
        return await service.get_template(template_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to get template", error=str(e), template_id=str(template_id))
        raise HTTPException(status_code=500, detail="Internal server error")


@template_router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: UUID,
    name: Optional[str] = None,
    description: Optional[str] = None,
    default_values: Optional[dict] = None,
    tags: Optional[List[str]] = None,
    is_public: Optional[bool] = None,
    shared_with: Optional[List[UUID]] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a metadata template"""
    try:
        service = TemplateService(db, current_user["user_id"])
        return await service.update_template(
            template_id, name, description, default_values, tags, is_public, shared_with
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except DuplicateResourceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to update template", error=str(e), template_id=str(template_id))
        raise HTTPException(status_code=500, detail="Internal server error")


@template_router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: UUID,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a metadata template"""
    try:
        service = TemplateService(db, current_user["user_id"])
        await service.delete_template(template_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to delete template", error=str(e), template_id=str(template_id))
        raise HTTPException(status_code=500, detail="Internal server error")


@template_router.post("/{template_id}/use")
async def use_template(
    template_id: UUID,
    overrides: Optional[dict] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Use a template to generate metadata with optional overrides"""
    try:
        service = TemplateService(db, current_user["user_id"])
        return await service.use_template(template_id, overrides)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("Failed to use template", error=str(e), template_id=str(template_id))
        raise HTTPException(status_code=500, detail="Internal server error")


@template_router.post("/{template_id}/duplicate", response_model=TemplateResponse)
async def duplicate_template(
    template_id: UUID,
    new_name: str,
    new_description: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Duplicate an existing template"""
    try:
        service = TemplateService(db, current_user["user_id"])
        return await service.duplicate_template(template_id, new_name, new_description)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DuplicateResourceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to duplicate template", error=str(e), template_id=str(template_id))
        raise HTTPException(status_code=500, detail="Internal server error")


@template_router.get("/suggestions/{schema_id}", response_model=List[TemplateResponse])
async def get_template_suggestions(
    schema_id: UUID,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get template suggestions for a specific schema"""
    try:
        service = TemplateService(db, current_user["user_id"])
        return await service.get_template_suggestions(schema_id, limit)
    except Exception as e:
        logger.error("Failed to get template suggestions", error=str(e), schema_id=str(schema_id))
        raise HTTPException(status_code=500, detail="Internal server error")


@template_router.get("/popular", response_model=List[TemplateResponse])
async def get_popular_templates(
    category: Optional[str] = None,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get popular public templates"""
    try:
        service = TemplateService(db, current_user["user_id"])
        return await service.get_popular_templates(category, limit)
    except Exception as e:
        logger.error("Failed to get popular templates", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@template_router.post("/{template_id}/share", response_model=TemplateResponse)
async def share_template(
    template_id: UUID,
    user_ids: List[UUID],
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Share a template with specific users"""
    try:
        service = TemplateService(db, current_user["user_id"])
        return await service.share_template(template_id, user_ids)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to share template", error=str(e), template_id=str(template_id))
        raise HTTPException(status_code=500, detail="Internal server error")


@template_router.post("/{template_id}/unshare", response_model=TemplateResponse)
async def unshare_template(
    template_id: UUID,
    user_ids: List[UUID],
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Unshare a template from specific users"""
    try:
        service = TemplateService(db, current_user["user_id"])
        return await service.unshare_template(template_id, user_ids)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to unshare template", error=str(e), template_id=str(template_id))
        raise HTTPException(status_code=500, detail="Internal server error")


@template_router.get("/statistics", response_model=dict)
async def get_template_statistics(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get template statistics"""
    try:
        service = TemplateService(db, current_user["user_id"])
        return await service.get_template_statistics()
    except Exception as e:
        logger.error("Failed to get template statistics", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


# Extraction Endpoints
@extraction_router.post("/technical/{asset_id}", status_code=status.HTTP_202_ACCEPTED)
async def extract_technical_metadata(
    asset_id: UUID,
    extraction_request: ExtractionRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Start technical metadata extraction for an asset"""
    try:
        service = ExtractionService(db, current_user["user_id"])
        task_id = await service.start_extraction(asset_id, extraction_request)
        return {"task_id": task_id, "status": "accepted"}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to start extraction", error=str(e), asset_id=str(asset_id))
        raise HTTPException(status_code=500, detail="Internal server error")


@extraction_router.get("/task/{task_id}")
async def get_extraction_status(
    task_id: UUID,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get extraction task status"""
    try:
        service = ExtractionService(db, current_user["user_id"])
        return await service.get_task_status(task_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to get extraction status", error=str(e), task_id=str(task_id))
        raise HTTPException(status_code=500, detail="Internal server error")


# Search Endpoints
@search_router.post("/metadata")
async def search_metadata(
    query: dict,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Search metadata using MongoDB queries"""
    try:
        service = MetadataService(db, current_user["user_id"])
        pagination = PaginationParams(page=page, page_size=page_size)
        return await service.search_metadata(query, pagination)
    except Exception as e:
        logger.error("Failed to search metadata", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


# EXIF Extraction Endpoints
@extraction_router.post("/exif/{asset_id}", status_code=status.HTTP_202_ACCEPTED)
async def extract_exif_metadata(
    asset_id: UUID,
    file_path: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Extract EXIF metadata from image file"""
    try:
        service = ExtractionService(db, current_user["user_id"])
        exif_data = await service.extract_exif_metadata(asset_id, file_path)
        return {"asset_id": asset_id, "exif_data": exif_data}
    except Exception as e:
        logger.error("Failed to extract EXIF metadata", error=str(e), asset_id=str(asset_id))
        raise HTTPException(status_code=500, detail="Internal server error")


@extraction_router.post("/image-info/{asset_id}", status_code=status.HTTP_202_ACCEPTED)
async def extract_basic_image_info(
    asset_id: UUID,
    file_path: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Extract basic image information"""
    try:
        service = ExtractionService(db, current_user["user_id"])
        image_info = await service.extract_basic_image_info(asset_id, file_path)
        return {"asset_id": asset_id, "image_info": image_info}
    except Exception as e:
        logger.error("Failed to extract image info", error=str(e), asset_id=str(asset_id))
        raise HTTPException(status_code=500, detail="Internal server error")


@extraction_router.post("/batch-exif", status_code=status.HTTP_202_ACCEPTED)
async def extract_batch_exif(
    extractions: List[Dict[str, Any]],
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Extract EXIF metadata from multiple files"""
    try:
        service = ExtractionService(db, current_user["user_id"])
        results = await service.extract_batch_exif(extractions)
        return {"results": results}
    except Exception as e:
        logger.error("Failed to extract batch EXIF", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@extraction_router.post("/process-task/{task_id}", status_code=status.HTTP_202_ACCEPTED)
async def process_extraction_task(
    task_id: UUID,
    file_path: str,
    file_size: int,
    mime_type: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Process an extraction task"""
    try:
        service = ExtractionService(db, current_user["user_id"])
        await service.process_extraction_task(task_id, file_path, file_size, mime_type)
        return {"task_id": task_id, "status": "processing"}
    except Exception as e:
        logger.error("Failed to process extraction task", error=str(e), task_id=str(task_id))
        raise HTTPException(status_code=500, detail="Internal server error")


# Video Metadata Extraction Endpoints
@extraction_router.post("/video/{asset_id}", status_code=status.HTTP_202_ACCEPTED)
async def extract_video_metadata(
    asset_id: UUID,
    file_path: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Extract video metadata using FFprobe"""
    try:
        service = ExtractionService(db, current_user["user_id"])
        video_data = await service.extract_video_metadata(asset_id, file_path)
        return {"asset_id": asset_id, "video_data": video_data}
    except Exception as e:
        logger.error("Failed to extract video metadata", error=str(e), asset_id=str(asset_id))
        raise HTTPException(status_code=500, detail="Internal server error")


@extraction_router.post("/ffprobe/{asset_id}", status_code=status.HTTP_202_ACCEPTED)
async def extract_ffprobe_metadata(
    asset_id: UUID,
    file_path: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Extract media metadata using FFprobe (alias for video extraction)"""
    try:
        service = ExtractionService(db, current_user["user_id"])
        video_data = await service.extract_video_metadata(asset_id, file_path)
        return {"asset_id": asset_id, "ffprobe_data": video_data}
    except Exception as e:
        logger.error("Failed to extract FFprobe metadata", error=str(e), asset_id=str(asset_id))
        raise HTTPException(status_code=500, detail="Internal server error")


@extraction_router.post("/batch-video", status_code=status.HTTP_202_ACCEPTED)
async def extract_batch_video(
    extractions: List[Dict[str, Any]],
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Extract video metadata from multiple files"""
    try:
        service = ExtractionService(db, current_user["user_id"])
        results = await service.extract_batch_video(extractions)
        return {"results": results}
    except Exception as e:
        logger.error("Failed to extract batch video metadata", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


# Audio Metadata Extraction Endpoints
@extraction_router.post("/audio/{asset_id}", status_code=status.HTTP_202_ACCEPTED)
async def extract_audio_metadata(
    asset_id: UUID,
    file_path: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Extract audio metadata using multiple audio libraries"""
    try:
        service = ExtractionService(db, current_user["user_id"])
        audio_data = await service.extract_audio_metadata(asset_id, file_path)
        return {"asset_id": asset_id, "audio_data": audio_data}
    except Exception as e:
        logger.error("Failed to extract audio metadata", error=str(e), asset_id=str(asset_id))
        raise HTTPException(status_code=500, detail="Internal server error")


@extraction_router.post("/id3/{asset_id}", status_code=status.HTTP_202_ACCEPTED)
async def extract_id3_metadata(
    asset_id: UUID,
    file_path: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Extract ID3 and audio metadata (alias for audio extraction)"""
    try:
        service = ExtractionService(db, current_user["user_id"])
        audio_data = await service.extract_audio_metadata(asset_id, file_path)
        return {"asset_id": asset_id, "id3_data": audio_data}
    except Exception as e:
        logger.error("Failed to extract ID3 metadata", error=str(e), asset_id=str(asset_id))
        raise HTTPException(status_code=500, detail="Internal server error")


@extraction_router.post("/batch-audio", status_code=status.HTTP_202_ACCEPTED)
async def extract_batch_audio(
    extractions: List[Dict[str, Any]],
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Extract audio metadata from multiple files"""
    try:
        service = ExtractionService(db, current_user["user_id"])
        results = await service.extract_batch_audio(extractions)
        return {"results": results}
    except Exception as e:
        logger.error("Failed to extract batch audio metadata", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@extraction_router.get("/audio-summary/{asset_id}")
async def get_audio_summary(
    asset_id: UUID,
    file_path: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get audio file summary"""
    try:
        service = ExtractionService(db, current_user["user_id"])
        summary = await service.get_audio_summary(asset_id, file_path)
        return summary
    except Exception as e:
        logger.error("Failed to get audio summary", error=str(e), asset_id=str(asset_id))
        raise HTTPException(status_code=500, detail="Internal server error")


# Document Metadata Extraction Endpoints
@extraction_router.post("/document/{asset_id}", status_code=status.HTTP_202_ACCEPTED)
async def extract_document_metadata(
    asset_id: UUID,
    file_path: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Extract document metadata using document extractor"""
    try:
        service = ExtractionService(db, current_user["user_id"])
        document_data = await service.extract_document_metadata(asset_id, file_path)
        return {"asset_id": asset_id, "document_data": document_data}
    except Exception as e:
        logger.error("Failed to extract document metadata", error=str(e), asset_id=str(asset_id))
        raise HTTPException(status_code=500, detail="Internal server error")


@extraction_router.post("/pdf/{asset_id}", status_code=status.HTTP_202_ACCEPTED)
async def extract_pdf_metadata(
    asset_id: UUID,
    file_path: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Extract PDF metadata (alias for document extraction)"""
    try:
        service = ExtractionService(db, current_user["user_id"])
        document_data = await service.extract_document_metadata(asset_id, file_path)
        return {"asset_id": asset_id, "pdf_data": document_data}
    except Exception as e:
        logger.error("Failed to extract PDF metadata", error=str(e), asset_id=str(asset_id))
        raise HTTPException(status_code=500, detail="Internal server error")


@extraction_router.post("/office/{asset_id}", status_code=status.HTTP_202_ACCEPTED)
async def extract_office_metadata(
    asset_id: UUID,
    file_path: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Extract Office document metadata (alias for document extraction)"""
    try:
        service = ExtractionService(db, current_user["user_id"])
        document_data = await service.extract_document_metadata(asset_id, file_path)
        return {"asset_id": asset_id, "office_data": document_data}
    except Exception as e:
        logger.error("Failed to extract Office metadata", error=str(e), asset_id=str(asset_id))
        raise HTTPException(status_code=500, detail="Internal server error")


@extraction_router.post("/batch-documents", status_code=status.HTTP_202_ACCEPTED)
async def extract_batch_documents(
    extractions: List[Dict[str, Any]],
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Extract document metadata from multiple files"""
    try:
        service = ExtractionService(db, current_user["user_id"])
        results = await service.extract_batch_documents(extractions)
        return {"results": results}
    except Exception as e:
        logger.error("Failed to extract batch document metadata", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@extraction_router.get("/document-summary/{asset_id}")
async def get_document_summary(
    asset_id: UUID,
    file_path: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get document file summary"""
    try:
        service = ExtractionService(db, current_user["user_id"])
        summary = await service.get_document_summary(asset_id, file_path)
        return summary
    except Exception as e:
        logger.error("Failed to get document summary", error=str(e), asset_id=str(asset_id))
        raise HTTPException(status_code=500, detail="Internal server error")


# Sidecar File Management Endpoints
@extraction_router.get("/sidecar/find/{asset_id}")
async def find_sidecar_files(
    asset_id: UUID,
    media_file_path: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Find sidecar files for a media file"""
    try:
        service = ExtractionService(db, current_user["user_id"])
        sidecar_files = await service.find_sidecar_files(media_file_path)
        return {
            "asset_id": asset_id,
            "media_file": media_file_path,
            "sidecar_files": sidecar_files
        }
    except Exception as e:
        logger.error("Failed to find sidecar files", error=str(e), asset_id=str(asset_id))
        raise HTTPException(status_code=500, detail="Internal server error")


@extraction_router.post("/sidecar/extract/{asset_id}", status_code=status.HTTP_202_ACCEPTED)
async def extract_sidecar_metadata(
    asset_id: UUID,
    media_file_path: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Extract metadata from sidecar files"""
    try:
        service = ExtractionService(db, current_user["user_id"])
        sidecar_data = await service.extract_sidecar_metadata(asset_id, media_file_path)
        return {"asset_id": asset_id, "sidecar_data": sidecar_data}
    except Exception as e:
        logger.error("Failed to extract sidecar metadata", error=str(e), asset_id=str(asset_id))
        raise HTTPException(status_code=500, detail="Internal server error")


@extraction_router.get("/sidecar/read")
async def read_sidecar_file(
    sidecar_path: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Read metadata from a specific sidecar file"""
    try:
        service = ExtractionService(db, current_user["user_id"])
        sidecar_data = await service.read_sidecar_metadata(sidecar_path)
        return {"sidecar_path": sidecar_path, "data": sidecar_data}
    except Exception as e:
        logger.error("Failed to read sidecar file", error=str(e), sidecar_path=sidecar_path)
        raise HTTPException(status_code=500, detail="Internal server error")


@extraction_router.post("/sidecar/write/{asset_id}", status_code=status.HTTP_201_CREATED)
async def write_sidecar_file(
    asset_id: UUID,
    media_file_path: str,
    metadata: Dict[str, Any],
    format_type: str = "json",
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Write metadata to a sidecar file"""
    try:
        service = ExtractionService(db, current_user["user_id"])
        sidecar_path = await service.write_sidecar_metadata(
            asset_id, media_file_path, metadata, format_type
        )
        return {
            "asset_id": asset_id,
            "media_file": media_file_path,
            "sidecar_path": sidecar_path,
            "format": format_type
        }
    except Exception as e:
        logger.error("Failed to write sidecar file", error=str(e), asset_id=str(asset_id))
        raise HTTPException(status_code=500, detail="Internal server error")


@extraction_router.post("/sidecar/sync/{asset_id}")
async def sync_sidecar_files(
    asset_id: UUID,
    media_file_path: str,
    metadata: Dict[str, Any],
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Synchronize sidecar files with current metadata"""
    try:
        service = ExtractionService(db, current_user["user_id"])
        updated_files = await service.sync_sidecar_files(asset_id, media_file_path, metadata)
        return {
            "asset_id": asset_id,
            "media_file": media_file_path,
            "updated_files": updated_files
        }
    except Exception as e:
        logger.error("Failed to sync sidecar files", error=str(e), asset_id=str(asset_id))
        raise HTTPException(status_code=500, detail="Internal server error")


@extraction_router.get("/sidecar/validate")
async def validate_sidecar_file(
    sidecar_path: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Validate a sidecar file"""
    try:
        service = ExtractionService(db, current_user["user_id"])
        validation_result = await service.validate_sidecar_file(sidecar_path)
        return {
            "sidecar_path": sidecar_path,
            "validation": validation_result
        }
    except Exception as e:
        logger.error("Failed to validate sidecar file", error=str(e), sidecar_path=sidecar_path)
        raise HTTPException(status_code=500, detail="Internal server error")


# Combine all routers
def get_router() -> APIRouter:
    """Get combined router for all endpoints"""
    router = APIRouter()
    router.include_router(schema_router)
    router.include_router(metadata_router)
    router.include_router(template_router)
    router.include_router(extraction_router)
    router.include_router(search_router)
    return router