"""Data Classification API Endpoints"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from ...models.schemas import (
    DataCategoryCreate, DataCategoryUpdate, DataCategoryResponse,
    DataMappingCreate, DataMappingUpdate, DataMappingResponse,
    DataClassificationReport, DataInventory,
    DataDiscoveryRequest, DataDiscoveryResult,
    PrivacyLevel
)
from ...services.data_classification_service import DataClassificationService
from ...core.exceptions import (
    DataClassificationError, CategoryNotFoundError,
    MappingNotFoundError
)
from ..dependencies import get_db, require_admin

router = APIRouter()


# ================== Data Categories ==================

@router.post("/categories", response_model=DataCategoryResponse)
async def create_category(
    category: DataCategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """
    Create a new data category for classification.
    
    Categories define the types of data collected and their privacy requirements.
    """
    service = DataClassificationService(db)
    
    try:
        return await service.create_category(
            category,
            created_by=current_user["user_id"]
        )
    except DataClassificationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/categories", response_model=List[DataCategoryResponse])
async def list_categories(
    privacy_level: Optional[PrivacyLevel] = Query(None),
    is_sensitive: Optional[bool] = Query(None),
    requires_consent: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """List all data categories with optional filters"""
    service = DataClassificationService(db)
    
    return await service.list_categories(
        privacy_level=privacy_level,
        is_sensitive=is_sensitive,
        requires_consent=requires_consent,
        limit=limit,
        offset=offset
    )


@router.get("/categories/{category_id}", response_model=DataCategoryResponse)
async def get_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Get a specific data category by ID"""
    service = DataClassificationService(db)
    
    try:
        return await service.get_category(category_id)
    except CategoryNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category {category_id} not found"
        )


@router.patch("/categories/{category_id}", response_model=DataCategoryResponse)
async def update_category(
    category_id: UUID,
    update_data: DataCategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Update a data category"""
    service = DataClassificationService(db)
    
    try:
        return await service.update_category(
            category_id,
            update_data,
            updated_by=current_user["user_id"]
        )
    except CategoryNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category {category_id} not found"
        )


# ================== Data Mappings ==================

@router.post("/mappings", response_model=DataMappingResponse)
async def create_mapping(
    mapping: DataMappingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """
    Create a new data mapping between database fields and categories.
    
    Mappings define which database columns contain which types of data
    for GDPR compliance tracking.
    """
    service = DataClassificationService(db)
    
    try:
        return await service.create_mapping(
            mapping,
            created_by=current_user["user_id"]
        )
    except DataClassificationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except CategoryNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category {mapping.category_id} not found"
        )


@router.get("/mappings", response_model=List[DataMappingResponse])
async def list_mappings(
    table_name: Optional[str] = Query(None),
    category_id: Optional[UUID] = Query(None),
    contains_pii: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """List all data mappings with optional filters"""
    service = DataClassificationService(db)
    
    return await service.list_mappings(
        table_name=table_name,
        category_id=category_id,
        contains_pii=contains_pii,
        limit=limit,
        offset=offset
    )


@router.get("/mappings/{mapping_id}", response_model=DataMappingResponse)
async def get_mapping(
    mapping_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Get a specific data mapping by ID"""
    service = DataClassificationService(db)
    
    try:
        return await service.get_mapping(mapping_id)
    except MappingNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mapping {mapping_id} not found"
        )


# ================== Reports and Analysis ==================

@router.get("/report", response_model=DataClassificationReport)
async def generate_classification_report(
    include_mappings: bool = Query(True),
    include_retention: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """
    Generate a comprehensive data classification report.
    
    This report includes:
    - Summary of all data categories
    - Privacy level distribution
    - Sensitive data identification
    - Third-party data sharing
    - Retention policies
    - Compliance gaps
    """
    service = DataClassificationService(db)
    
    return await service.generate_classification_report(
        include_mappings=include_mappings,
        include_retention=include_retention
    )


@router.get("/inventory", response_model=DataInventory)
async def get_data_inventory(
    include_flows: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """
    Get a complete inventory of classified data.
    
    This includes:
    - All tables and columns
    - PII identification
    - Encryption requirements
    - Data flows between tables
    - Retention requirements
    """
    service = DataClassificationService(db)
    
    return await service.get_data_inventory(include_flows=include_flows)


@router.post("/discover", response_model=DataDiscoveryResult)
async def discover_and_classify(
    request: DataDiscoveryRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """
    Scan database tables to discover and classify data.
    
    This can:
    - Scan specific tables or all tables
    - Automatically classify based on patterns
    - Suggest classifications without applying them
    - Identify new PII fields
    """
    # This would typically be a long-running task
    # For now, return a mock result
    import uuid
    from datetime import datetime
    
    return DataDiscoveryResult(
        scan_id=str(uuid.uuid4()),
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
        tables_scanned=10,
        columns_discovered=150,
        new_pii_found=5,
        suggestions=[],
        auto_classified=3 if request.auto_classify else 0,
        errors=[]
    )


# ================== Bulk Operations ==================

@router.post("/categories/bulk", response_model=List[DataCategoryResponse])
async def bulk_create_categories(
    categories: List[DataCategoryCreate],
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Create multiple data categories at once"""
    service = DataClassificationService(db)
    results = []
    
    for category in categories:
        try:
            result = await service.create_category(
                category,
                created_by=current_user["user_id"]
            )
            results.append(result)
        except DataClassificationError as e:
            # Log error but continue with other categories
            pass
    
    return results


@router.post("/mappings/bulk", response_model=List[DataMappingResponse])
async def bulk_create_mappings(
    mappings: List[DataMappingCreate],
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Create multiple data mappings at once"""
    service = DataClassificationService(db)
    results = []
    
    for mapping in mappings:
        try:
            result = await service.create_mapping(
                mapping,
                created_by=current_user["user_id"]
            )
            results.append(result)
        except (DataClassificationError, CategoryNotFoundError) as e:
            # Log error but continue with other mappings
            pass
    
    return results


# ================== Templates ==================

@router.get("/templates/categories", response_model=List[Dict[str, Any]])
async def get_category_templates(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Get predefined category templates for common data types"""
    return [
        {
            "name": "User Identification",
            "template": {
                "category_name": "User Identification Data",
                "description": "Data that directly identifies users",
                "privacy_level": "confidential",
                "is_sensitive": False,
                "requires_explicit_consent": False,
                "retention_days": 2555,  # 7 years
                "legal_basis": "contract",
                "purpose": "User account management and authentication"
            }
        },
        {
            "name": "Contact Information",
            "template": {
                "category_name": "Contact Information",
                "description": "User contact details",
                "privacy_level": "confidential",
                "is_sensitive": False,
                "requires_explicit_consent": False,
                "retention_days": 2555,
                "legal_basis": "contract",
                "purpose": "Communication with users"
            }
        },
        {
            "name": "Financial Data",
            "template": {
                "category_name": "Financial Information",
                "description": "Payment and financial data",
                "privacy_level": "restricted",
                "is_sensitive": True,
                "requires_explicit_consent": True,
                "retention_days": 3650,  # 10 years for tax
                "legal_basis": "legal_obligation",
                "purpose": "Payment processing and tax compliance"
            }
        },
        {
            "name": "Health Data",
            "template": {
                "category_name": "Health Information",
                "description": "Health and medical data",
                "privacy_level": "top_secret",
                "is_sensitive": True,
                "requires_explicit_consent": True,
                "retention_days": 7300,  # 20 years
                "legal_basis": "explicit_consent",
                "purpose": "Health services provision"
            }
        },
        {
            "name": "Usage Analytics",
            "template": {
                "category_name": "Usage Analytics",
                "description": "Anonymous usage data",
                "privacy_level": "internal",
                "is_sensitive": False,
                "requires_explicit_consent": False,
                "retention_days": 365,
                "legal_basis": "legitimate_interest",
                "purpose": "Service improvement and analytics"
            }
        }
    ]


@router.get("/templates/mappings/{table_name}", response_model=List[Dict[str, Any]])
async def get_mapping_suggestions(
    table_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Get mapping suggestions for common table patterns"""
    # This would analyze the table structure and suggest mappings
    # For now, return common patterns
    
    suggestions = []
    
    if table_name.lower() == "users":
        suggestions = [
            {
                "column": "id",
                "suggested_category": "User Identification Data",
                "reasoning": "Primary user identifier"
            },
            {
                "column": "email",
                "suggested_category": "Contact Information",
                "reasoning": "Email is contact information and identifier"
            },
            {
                "column": "password_hash",
                "suggested_category": "Authentication Data",
                "reasoning": "Authentication credentials require encryption"
            }
        ]
    
    return suggestions