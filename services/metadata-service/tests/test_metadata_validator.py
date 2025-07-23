"""
Tests for metadata validation functionality
"""

import pytest
from datetime import datetime
from uuid import UUID, uuid4

from src.services.metadata_validator import MetadataValidator
from src.db.models import MetadataSchema, FieldDefinition, FieldType, SchemaStatus
from src.core.exceptions import ValidationError


class TestMetadataValidator:
    """Test cases for MetadataValidator"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.validator = MetadataValidator()
        
        # Create a test schema
        self.test_schema = MetadataSchema(
            schema_id=uuid4(),
            name="test_schema",
            display_name="Test Schema",
            description="Test schema for validation",
            version=1,
            category="test",
            fields=[
                FieldDefinition(
                    name="title",
                    display_name="Title",
                    field_type=FieldType.STRING,
                    required=True,
                    constraints={"min_length": 1, "max_length": 100}
                ),
                FieldDefinition(
                    name="description",
                    display_name="Description",
                    field_type=FieldType.TEXT,
                    required=False,
                    constraints={"max_length": 1000}
                ),
                FieldDefinition(
                    name="priority",
                    display_name="Priority",
                    field_type=FieldType.INTEGER,
                    required=False,
                    constraints={"min_value": 1, "max_value": 10}
                ),
                FieldDefinition(
                    name="score",
                    display_name="Score",
                    field_type=FieldType.FLOAT,
                    required=False,
                    constraints={"min_value": 0.0, "max_value": 10.0}
                ),
                FieldDefinition(
                    name="active",
                    display_name="Active",
                    field_type=FieldType.BOOLEAN,
                    required=False,
                    default_value=True
                ),
                FieldDefinition(
                    name="created_date",
                    display_name="Created Date",
                    field_type=FieldType.DATE,
                    required=False
                ),
                FieldDefinition(
                    name="created_at",
                    display_name="Created At",
                    field_type=FieldType.DATETIME,
                    required=False
                ),
                FieldDefinition(
                    name="tags",
                    display_name="Tags",
                    field_type=FieldType.ARRAY,
                    array_type=FieldType.STRING,
                    required=False,
                    constraints={"min_length": 0, "max_length": 10}
                ),
                FieldDefinition(
                    name="status",
                    display_name="Status",
                    field_type=FieldType.ENUM,
                    required=False,
                    constraints={"enum_values": ["draft", "published", "archived"]}
                ),
                FieldDefinition(
                    name="owner_id",
                    display_name="Owner ID",
                    field_type=FieldType.REFERENCE,
                    required=False,
                    reference_collection="users"
                )
            ],
            status=SchemaStatus.ACTIVE,
            is_system=False,
            is_default=False,
            created_by=uuid4(),
            created_at=datetime.utcnow(),
            allow_custom_fields=True,
            strict_mode=False
        )
    
    @pytest.mark.asyncio
    async def test_validate_valid_metadata(self):
        """Test validation with valid metadata"""
        metadata = {
            "title": "Test Title",
            "description": "Test description",
            "priority": 5,
            "score": 8.5,
            "active": True,
            "created_date": "2024-01-01",
            "created_at": "2024-01-01T10:00:00Z",
            "tags": ["tag1", "tag2"],
            "status": "published",
            "owner_id": str(uuid4())
        }
        
        result = await self.validator.validate_metadata(metadata, self.test_schema)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert result["validated_data"]["title"] == "Test Title"
        assert result["validated_data"]["priority"] == 5
        assert result["validated_data"]["active"] is True
    
    @pytest.mark.asyncio
    async def test_validate_missing_required_field(self):
        """Test validation with missing required field"""
        metadata = {
            "description": "Test description",
            "priority": 5
        }
        
        result = await self.validator.validate_metadata(metadata, self.test_schema)
        
        assert result["valid"] is False
        assert len(result["errors"]) == 1
        assert result["errors"][0]["field"] == "title"
        assert result["errors"][0]["type"] == "missing_required"
    
    @pytest.mark.asyncio
    async def test_validate_string_constraints(self):
        """Test string field validation with constraints"""
        # Test string too short
        metadata = {"title": ""}
        result = await self.validator.validate_metadata(metadata, self.test_schema)
        
        assert result["valid"] is False
        assert "title" in [error["field"] for error in result["errors"]]
        
        # Test string too long
        metadata = {"title": "x" * 101}
        result = await self.validator.validate_metadata(metadata, self.test_schema)
        
        assert result["valid"] is False
        assert "title" in [error["field"] for error in result["errors"]]
    
    @pytest.mark.asyncio
    async def test_validate_integer_constraints(self):
        """Test integer field validation with constraints"""
        metadata = {"title": "Test", "priority": 0}
        result = await self.validator.validate_metadata(metadata, self.test_schema)
        
        assert result["valid"] is False
        assert "priority" in [error["field"] for error in result["errors"]]
        
        metadata = {"title": "Test", "priority": 11}
        result = await self.validator.validate_metadata(metadata, self.test_schema)
        
        assert result["valid"] is False
        assert "priority" in [error["field"] for error in result["errors"]]
    
    @pytest.mark.asyncio
    async def test_validate_float_constraints(self):
        """Test float field validation with constraints"""
        metadata = {"title": "Test", "score": -1.0}
        result = await self.validator.validate_metadata(metadata, self.test_schema)
        
        assert result["valid"] is False
        assert "score" in [error["field"] for error in result["errors"]]
        
        metadata = {"title": "Test", "score": 11.0}
        result = await self.validator.validate_metadata(metadata, self.test_schema)
        
        assert result["valid"] is False
        assert "score" in [error["field"] for error in result["errors"]]
    
    @pytest.mark.asyncio
    async def test_validate_boolean_field(self):
        """Test boolean field validation"""
        metadata = {"title": "Test", "active": "true"}
        result = await self.validator.validate_metadata(metadata, self.test_schema)
        
        assert result["valid"] is True
        assert result["validated_data"]["active"] is True
        
        metadata = {"title": "Test", "active": "false"}
        result = await self.validator.validate_metadata(metadata, self.test_schema)
        
        assert result["valid"] is True
        assert result["validated_data"]["active"] is False
    
    @pytest.mark.asyncio
    async def test_validate_array_field(self):
        """Test array field validation"""
        metadata = {"title": "Test", "tags": ["tag1", "tag2", "tag3"]}
        result = await self.validator.validate_metadata(metadata, self.test_schema)
        
        assert result["valid"] is True
        assert len(result["validated_data"]["tags"]) == 3
        
        # Test array too long
        metadata = {"title": "Test", "tags": ["tag"] * 11}
        result = await self.validator.validate_metadata(metadata, self.test_schema)
        
        assert result["valid"] is False
        assert "tags" in [error["field"] for error in result["errors"]]
    
    @pytest.mark.asyncio
    async def test_validate_enum_field(self):
        """Test enum field validation"""
        metadata = {"title": "Test", "status": "published"}
        result = await self.validator.validate_metadata(metadata, self.test_schema)
        
        assert result["valid"] is True
        assert result["validated_data"]["status"] == "published"
        
        # Test invalid enum value
        metadata = {"title": "Test", "status": "invalid"}
        result = await self.validator.validate_metadata(metadata, self.test_schema)
        
        assert result["valid"] is False
        assert "status" in [error["field"] for error in result["errors"]]
    
    @pytest.mark.asyncio
    async def test_validate_reference_field(self):
        """Test reference field validation"""
        valid_uuid = str(uuid4())
        metadata = {"title": "Test", "owner_id": valid_uuid}
        result = await self.validator.validate_metadata(metadata, self.test_schema)
        
        assert result["valid"] is True
        assert result["validated_data"]["owner_id"] == valid_uuid
        
        # Test invalid UUID
        metadata = {"title": "Test", "owner_id": "invalid-uuid"}
        result = await self.validator.validate_metadata(metadata, self.test_schema)
        
        assert result["valid"] is False
        assert "owner_id" in [error["field"] for error in result["errors"]]
    
    @pytest.mark.asyncio
    async def test_validate_custom_fields(self):
        """Test custom field handling"""
        metadata = {
            "title": "Test",
            "custom_field": "custom_value"
        }
        
        result = await self.validator.validate_metadata(metadata, self.test_schema)
        
        assert result["valid"] is True
        assert result["custom_fields"]["custom_field"] == "custom_value"
        
        # Test strict mode
        self.test_schema.strict_mode = True
        result = await self.validator.validate_metadata(metadata, self.test_schema)
        
        assert result["valid"] is False
        assert "custom_field" in [error["field"] for error in result["errors"]]
    
    @pytest.mark.asyncio
    async def test_validate_default_values(self):
        """Test default value handling"""
        metadata = {
            "title": "Test"
        }
        
        result = await self.validator.validate_metadata(metadata, self.test_schema)
        
        assert result["valid"] is True
        # The active field should get its default value
        assert result["validated_data"]["active"] is True
    
    @pytest.mark.asyncio
    async def test_validate_date_field(self):
        """Test date field validation"""
        metadata = {"title": "Test", "created_date": "2024-01-01"}
        result = await self.validator.validate_metadata(metadata, self.test_schema)
        
        assert result["valid"] is True
        assert result["validated_data"]["created_date"] == "2024-01-01"
        
        # Test invalid date
        metadata = {"title": "Test", "created_date": "invalid-date"}
        result = await self.validator.validate_metadata(metadata, self.test_schema)
        
        assert result["valid"] is False
        assert "created_date" in [error["field"] for error in result["errors"]]
    
    @pytest.mark.asyncio
    async def test_validate_datetime_field(self):
        """Test datetime field validation"""
        metadata = {"title": "Test", "created_at": "2024-01-01T10:00:00Z"}
        result = await self.validator.validate_metadata(metadata, self.test_schema)
        
        assert result["valid"] is True
        assert result["validated_data"]["created_at"] == "2024-01-01T10:00:00Z"
        
        # Test invalid datetime
        metadata = {"title": "Test", "created_at": "invalid-datetime"}
        result = await self.validator.validate_metadata(metadata, self.test_schema)
        
        assert result["valid"] is False
        assert "created_at" in [error["field"] for error in result["errors"]]
    
    @pytest.mark.asyncio
    async def test_validate_email_field(self):
        """Test email field validation"""
        # Add email field to schema
        email_field = FieldDefinition(
            name="email",
            display_name="Email",
            field_type=FieldType.EMAIL,
            required=False
        )
        self.test_schema.fields.append(email_field)
        
        metadata = {"title": "Test", "email": "test@example.com"}
        result = await self.validator.validate_metadata(metadata, self.test_schema)
        
        assert result["valid"] is True
        assert result["validated_data"]["email"] == "test@example.com"
        
        # Test invalid email
        metadata = {"title": "Test", "email": "invalid-email"}
        result = await self.validator.validate_metadata(metadata, self.test_schema)
        
        assert result["valid"] is False
        assert "email" in [error["field"] for error in result["errors"]]
    
    @pytest.mark.asyncio
    async def test_validate_url_field(self):
        """Test URL field validation"""
        # Add URL field to schema
        url_field = FieldDefinition(
            name="website",
            display_name="Website",
            field_type=FieldType.URL,
            required=False
        )
        self.test_schema.fields.append(url_field)
        
        metadata = {"title": "Test", "website": "https://example.com"}
        result = await self.validator.validate_metadata(metadata, self.test_schema)
        
        assert result["valid"] is True
        assert result["validated_data"]["website"] == "https://example.com"
        
        # Test invalid URL
        metadata = {"title": "Test", "website": "invalid-url"}
        result = await self.validator.validate_metadata(metadata, self.test_schema)
        
        assert result["valid"] is False
        assert "website" in [error["field"] for error in result["errors"]]
    
    @pytest.mark.asyncio
    async def test_validate_phone_field(self):
        """Test phone field validation"""
        # Add phone field to schema
        phone_field = FieldDefinition(
            name="phone",
            display_name="Phone",
            field_type=FieldType.PHONE,
            required=False
        )
        self.test_schema.fields.append(phone_field)
        
        metadata = {"title": "Test", "phone": "+1234567890"}
        result = await self.validator.validate_metadata(metadata, self.test_schema)
        
        assert result["valid"] is True
        assert result["validated_data"]["phone"] == "+1234567890"
        
        # Test invalid phone
        metadata = {"title": "Test", "phone": "invalid-phone"}
        result = await self.validator.validate_metadata(metadata, self.test_schema)
        
        assert result["valid"] is False
        assert "phone" in [error["field"] for error in result["errors"]]
    
    @pytest.mark.asyncio
    async def test_validate_json_field(self):
        """Test JSON field validation"""
        # Add JSON field to schema
        json_field = FieldDefinition(
            name="config",
            display_name="Configuration",
            field_type=FieldType.JSON,
            required=False
        )
        self.test_schema.fields.append(json_field)
        
        metadata = {"title": "Test", "config": {"key": "value", "number": 42}}
        result = await self.validator.validate_metadata(metadata, self.test_schema)
        
        assert result["valid"] is True
        assert result["validated_data"]["config"] == {"key": "value", "number": 42}
        
        # Test invalid JSON type
        metadata = {"title": "Test", "config": object()}
        result = await self.validator.validate_metadata(metadata, self.test_schema)
        
        assert result["valid"] is False
        assert "config" in [error["field"] for error in result["errors"]]
    
    @pytest.mark.asyncio
    async def test_validate_object_field(self):
        """Test object field validation with nested schema"""
        # Add object field with nested schema
        object_field = FieldDefinition(
            name="metadata",
            display_name="Metadata",
            field_type=FieldType.OBJECT,
            required=False,
            object_schema=[
                FieldDefinition(
                    name="type",
                    display_name="Type",
                    field_type=FieldType.STRING,
                    required=True
                ),
                FieldDefinition(
                    name="value",
                    display_name="Value",
                    field_type=FieldType.STRING,
                    required=False
                )
            ]
        )
        self.test_schema.fields.append(object_field)
        
        metadata = {
            "title": "Test",
            "metadata": {
                "type": "test_type",
                "value": "test_value"
            }
        }
        result = await self.validator.validate_metadata(metadata, self.test_schema)
        
        assert result["valid"] is True
        assert result["validated_data"]["metadata"]["type"] == "test_type"
        assert result["validated_data"]["metadata"]["value"] == "test_value"
        
        # Test missing required nested field
        metadata = {
            "title": "Test",
            "metadata": {
                "value": "test_value"
            }
        }
        result = await self.validator.validate_metadata(metadata, self.test_schema)
        
        assert result["valid"] is False
        assert any("type" in error["error"] for error in result["errors"])