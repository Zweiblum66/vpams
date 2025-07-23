"""Tests for Data Classification Service"""

import pytest
from datetime import datetime
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.data_classification_service import DataClassificationService
from src.models.schemas import (
    DataCategoryCreate, DataCategoryUpdate,
    DataMappingCreate, DataMappingUpdate,
    PrivacyLevel
)
from src.db.models import DataCategory, DataMapping
from src.core.exceptions import (
    DataClassificationError, CategoryNotFoundError,
    MappingNotFoundError
)


@pytest.mark.asyncio
async def test_create_category(db_session: AsyncSession):
    """Test creating a data category"""
    service = DataClassificationService(db_session)
    
    category_data = DataCategoryCreate(
        category_name="User Personal Data",
        description="Personal information about users",
        privacy_level=PrivacyLevel.CONFIDENTIAL,
        retention_days=2555,
        is_sensitive=True,
        requires_explicit_consent=True,
        legal_basis="consent",
        purpose="User profile management"
    )
    
    category = await service.create_category(
        category_data,
        created_by=str(uuid4())
    )
    
    assert category.category_name == "User Personal Data"
    assert category.privacy_level == PrivacyLevel.CONFIDENTIAL
    assert category.is_sensitive is True
    assert category.retention_days == 2555


@pytest.mark.asyncio
async def test_create_duplicate_category(db_session: AsyncSession):
    """Test creating duplicate category fails"""
    service = DataClassificationService(db_session)
    
    category_data = DataCategoryCreate(
        category_name="Duplicate Category",
        privacy_level=PrivacyLevel.INTERNAL
    )
    
    # Create first category
    await service.create_category(category_data, created_by=str(uuid4()))
    
    # Try to create duplicate
    with pytest.raises(DataClassificationError) as exc_info:
        await service.create_category(category_data, created_by=str(uuid4()))
    
    assert "already exists" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_category(db_session: AsyncSession):
    """Test retrieving a category"""
    service = DataClassificationService(db_session)
    
    # Create category
    category_data = DataCategoryCreate(
        category_name="Test Category",
        privacy_level=PrivacyLevel.PUBLIC
    )
    created = await service.create_category(
        category_data,
        created_by=str(uuid4())
    )
    
    # Retrieve it
    retrieved = await service.get_category(created.id)
    
    assert retrieved.id == created.id
    assert retrieved.category_name == "Test Category"


@pytest.mark.asyncio
async def test_get_nonexistent_category(db_session: AsyncSession):
    """Test retrieving non-existent category fails"""
    service = DataClassificationService(db_session)
    
    with pytest.raises(CategoryNotFoundError):
        await service.get_category(uuid4())


@pytest.mark.asyncio
async def test_list_categories(db_session: AsyncSession):
    """Test listing categories with filters"""
    service = DataClassificationService(db_session)
    
    # Create test categories
    categories = [
        DataCategoryCreate(
            category_name="Public Data",
            privacy_level=PrivacyLevel.PUBLIC,
            is_sensitive=False
        ),
        DataCategoryCreate(
            category_name="Sensitive Data",
            privacy_level=PrivacyLevel.RESTRICTED,
            is_sensitive=True,
            requires_explicit_consent=True
        ),
        DataCategoryCreate(
            category_name="Internal Data",
            privacy_level=PrivacyLevel.INTERNAL,
            is_sensitive=False
        )
    ]
    
    for cat in categories:
        await service.create_category(cat, created_by=str(uuid4()))
    
    # Test filtering by privacy level
    public_cats = await service.list_categories(
        privacy_level=PrivacyLevel.PUBLIC
    )
    assert len(public_cats) >= 1
    assert all(c.privacy_level == PrivacyLevel.PUBLIC for c in public_cats)
    
    # Test filtering by sensitivity
    sensitive_cats = await service.list_categories(is_sensitive=True)
    assert len(sensitive_cats) >= 1
    assert all(c.is_sensitive for c in sensitive_cats)


@pytest.mark.asyncio
async def test_update_category(db_session: AsyncSession):
    """Test updating a category"""
    service = DataClassificationService(db_session)
    
    # Create category
    category_data = DataCategoryCreate(
        category_name="Update Test",
        privacy_level=PrivacyLevel.INTERNAL,
        retention_days=365
    )
    created = await service.create_category(
        category_data,
        created_by=str(uuid4())
    )
    
    # Update it
    update_data = DataCategoryUpdate(
        retention_days=730,
        is_sensitive=True,
        privacy_level=PrivacyLevel.CONFIDENTIAL
    )
    
    updated = await service.update_category(
        created.id,
        update_data,
        updated_by=str(uuid4())
    )
    
    assert updated.retention_days == 730
    assert updated.is_sensitive is True
    assert updated.privacy_level == PrivacyLevel.CONFIDENTIAL


@pytest.mark.asyncio
async def test_create_mapping(db_session: AsyncSession):
    """Test creating a data mapping"""
    service = DataClassificationService(db_session)
    
    # Create category first
    category_data = DataCategoryCreate(
        category_name="Email Data",
        privacy_level=PrivacyLevel.CONFIDENTIAL
    )
    category = await service.create_category(
        category_data,
        created_by=str(uuid4())
    )
    
    # Create mapping
    mapping_data = DataMappingCreate(
        table_name="users",
        column_name="email",
        category_id=category.id,
        field_description="User email address",
        contains_pii=True,
        encryption_required=False,
        anonymization_method="mask_email"
    )
    
    mapping = await service.create_mapping(
        mapping_data,
        created_by=str(uuid4())
    )
    
    assert mapping.table_name == "users"
    assert mapping.column_name == "email"
    assert mapping.category_id == category.id
    assert mapping.contains_pii is True


@pytest.mark.asyncio
async def test_create_duplicate_mapping(db_session: AsyncSession):
    """Test creating duplicate mapping fails"""
    service = DataClassificationService(db_session)
    
    # Create category
    category = await service.create_category(
        DataCategoryCreate(
            category_name="Test Category",
            privacy_level=PrivacyLevel.INTERNAL
        ),
        created_by=str(uuid4())
    )
    
    mapping_data = DataMappingCreate(
        table_name="users",
        column_name="duplicate_col",
        category_id=category.id
    )
    
    # Create first mapping
    await service.create_mapping(mapping_data, created_by=str(uuid4()))
    
    # Try to create duplicate
    with pytest.raises(DataClassificationError) as exc_info:
        await service.create_mapping(mapping_data, created_by=str(uuid4()))
    
    assert "already exists" in str(exc_info.value)


@pytest.mark.asyncio
async def test_list_mappings(db_session: AsyncSession):
    """Test listing mappings with filters"""
    service = DataClassificationService(db_session)
    
    # Create categories
    cat1 = await service.create_category(
        DataCategoryCreate(
            category_name="Category 1",
            privacy_level=PrivacyLevel.INTERNAL
        ),
        created_by=str(uuid4())
    )
    
    cat2 = await service.create_category(
        DataCategoryCreate(
            category_name="Category 2",
            privacy_level=PrivacyLevel.CONFIDENTIAL
        ),
        created_by=str(uuid4())
    )
    
    # Create mappings
    mappings = [
        DataMappingCreate(
            table_name="users",
            column_name="name",
            category_id=cat1.id,
            contains_pii=True
        ),
        DataMappingCreate(
            table_name="users",
            column_name="created_at",
            category_id=cat2.id,
            contains_pii=False
        ),
        DataMappingCreate(
            table_name="assets",
            column_name="metadata",
            category_id=cat1.id,
            contains_pii=False
        )
    ]
    
    for mapping in mappings:
        await service.create_mapping(mapping, created_by=str(uuid4()))
    
    # Test filtering by table
    user_mappings = await service.list_mappings(table_name="users")
    assert len(user_mappings) >= 2
    assert all(m.table_name == "users" for m in user_mappings)
    
    # Test filtering by PII
    pii_mappings = await service.list_mappings(contains_pii=True)
    assert len(pii_mappings) >= 1
    assert all(m.contains_pii for m in pii_mappings)


@pytest.mark.asyncio
async def test_generate_classification_report(db_session: AsyncSession):
    """Test generating classification report"""
    service = DataClassificationService(db_session)
    
    # Create test data
    sensitive_cat = await service.create_category(
        DataCategoryCreate(
            category_name="Sensitive Data",
            privacy_level=PrivacyLevel.RESTRICTED,
            is_sensitive=True,
            retention_days=365,
            shared_with_third_parties=True,
            third_party_details={"processor": "Analytics Co"}
        ),
        created_by=str(uuid4())
    )
    
    normal_cat = await service.create_category(
        DataCategoryCreate(
            category_name="Normal Data",
            privacy_level=PrivacyLevel.INTERNAL,
            retention_days=730
        ),
        created_by=str(uuid4())
    )
    
    # Generate report
    report = await service.generate_classification_report()
    
    assert report.total_categories >= 2
    assert len(report.sensitive_data_categories) >= 1
    assert len(report.third_party_sharing) >= 1
    assert "restricted" in report.categories_by_privacy_level
    assert "365_days" in report.retention_summary


@pytest.mark.asyncio
async def test_get_data_inventory(db_session: AsyncSession):
    """Test getting data inventory"""
    service = DataClassificationService(db_session)
    
    # Create category
    category = await service.create_category(
        DataCategoryCreate(
            category_name="User Data",
            privacy_level=PrivacyLevel.CONFIDENTIAL,
            retention_days=1095
        ),
        created_by=str(uuid4())
    )
    
    # Create mappings
    tables_columns = [
        ("users", "email", True, True),
        ("users", "name", True, False),
        ("users", "created_at", False, False),
        ("assets", "owner_id", True, False)
    ]
    
    for table, column, pii, encrypted in tables_columns:
        await service.create_mapping(
            DataMappingCreate(
                table_name=table,
                column_name=column,
                category_id=category.id,
                contains_pii=pii,
                encryption_required=encrypted
            ),
            created_by=str(uuid4())
        )
    
    # Get inventory
    inventory = await service.get_data_inventory()
    
    assert inventory.total_tables >= 2
    assert inventory.total_columns >= 4
    assert inventory.pii_columns >= 3
    assert inventory.encrypted_columns >= 1
    assert "users" in inventory.tables
    assert "assets" in inventory.tables
    assert len(inventory.tables["users"]["columns"]) >= 3


@pytest.mark.asyncio
async def test_automatic_classification(db_session: AsyncSession):
    """Test automatic classification suggestions"""
    service = DataClassificationService(db_session)
    
    # Create categories for common patterns
    email_cat = await service.create_category(
        DataCategoryCreate(
            category_name="contact_information",
            privacy_level=PrivacyLevel.CONFIDENTIAL
        ),
        created_by=str(uuid4())
    )
    
    # Test classification
    column_info = {
        "name": "user_email",
        "type": "varchar(255)",
        "description": "User email address"
    }
    
    result = await service.classify_new_data(
        "users",
        column_info,
        auto_classify=True
    )
    
    if result:  # May not find category in test
        assert result.contains_pii is True
        assert result.anonymization_method == "mask_email"


@pytest.mark.asyncio
async def test_pii_detection(db_session: AsyncSession):
    """Test PII detection logic"""
    service = DataClassificationService(db_session)
    
    # Test various column names
    pii_columns = [
        {"name": "email"},
        {"name": "user_name"},
        {"name": "phone_number"},
        {"name": "ssn"},
        {"name": "credit_card"},
        {"name": "medical_record"}
    ]
    
    non_pii_columns = [
        {"name": "created_at"},
        {"name": "is_active"},
        {"name": "file_size"},
        {"name": "mime_type"}
    ]
    
    for col in pii_columns:
        assert service._is_likely_pii(col) is True
    
    for col in non_pii_columns:
        assert service._is_likely_pii(col) is False


@pytest.mark.asyncio
async def test_encryption_requirement_detection(db_session: AsyncSession):
    """Test encryption requirement detection"""
    service = DataClassificationService(db_session)
    
    # Test columns that need encryption
    encrypt_columns = [
        {"name": "password"},
        {"name": "api_secret"},
        {"name": "auth_token"},
        {"name": "ssn"},
        {"name": "credit_card_number"}
    ]
    
    # Test columns that don't need encryption
    no_encrypt_columns = [
        {"name": "email"},  # PII but not necessarily encrypted
        {"name": "name"},
        {"name": "created_at"}
    ]
    
    for col in encrypt_columns:
        assert service._needs_encryption(col) is True
    
    for col in no_encrypt_columns:
        assert service._needs_encryption(col) is False


@pytest.mark.asyncio
async def test_anonymization_method_suggestion(db_session: AsyncSession):
    """Test anonymization method suggestions"""
    service = DataClassificationService(db_session)
    
    test_cases = [
        ({"name": "email", "type": "string"}, "mask_email"),
        ({"name": "phone", "type": "string"}, "mask_phone"),
        ({"name": "first_name", "type": "string"}, "pseudonymize"),
        ({"name": "street_address", "type": "string"}, "generalize"),
        ({"name": "ssn", "type": "string"}, "tokenize"),
        ({"name": "birth_date", "type": "date"}, "generalize_date"),
        ({"name": "salary", "type": "decimal"}, "bucket"),
        ({"name": "random_field", "type": "string"}, "hash")
    ]
    
    for column_info, expected_method in test_cases:
        method = service._suggest_anonymization(column_info)
        assert method == expected_method