"""
Tests for Search Template Service
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from pymongo.errors import DuplicateKeyError
import uuid

from src.services.search_template_service import SearchTemplateService
from src.models.schemas import (
    SearchTemplateCreate, SearchTemplateUpdate, SearchTemplate, SearchTemplateList,
    SearchTemplateExecute, SearchTemplateExecuteResponse, SearchTemplateStats,
    SearchTemplateExport, SearchTemplateImport, SearchTemplateShare,
    SearchTemplateType, SearchTemplateCategory, SearchTemplateConfig,
    SearchTemplateParameter, SearchType, IndexType, SortOrder
)
from src.core.exceptions import SearchError, NotFoundError, ValidationError


class TestSearchTemplateService:
    """Test cases for SearchTemplateService"""
    
    @pytest.fixture
    def mock_mongodb(self):
        """Mock MongoDB database"""
        mock_db = MagicMock()
        mock_db.search_templates = AsyncMock()
        mock_db.search_template_favorites = AsyncMock()
        mock_db.search_template_stats = AsyncMock()
        mock_db.search_template_shares = AsyncMock()
        return mock_db
    
    @pytest.fixture
    def mock_search_service(self):
        """Mock SearchService"""
        return AsyncMock()
    
    @pytest.fixture
    def search_template_service(self, mock_mongodb, mock_search_service):
        """Create SearchTemplateService instance"""
        service = SearchTemplateService(mock_mongodb, mock_search_service)
        return service
    
    @pytest.fixture
    def sample_template_config(self):
        """Sample template configuration"""
        return SearchTemplateConfig(
            search_type=SearchType.BASIC,
            default_query="test query",
            indices=[IndexType.ASSETS],
            fields=["title", "description"],
            default_filters=[]
        )
    
    @pytest.fixture
    def sample_template_create(self, sample_template_config):
        """Sample template creation data"""
        return SearchTemplateCreate(
            name="Test Template",
            description="A test search template",
            category=SearchTemplateCategory.GENERAL,
            template_type=SearchTemplateType.BASIC,
            config=sample_template_config,
            parameters=[
                SearchTemplateParameter(
                    name="query",
                    type="string",
                    description="Search query",
                    required=True
                )
            ],
            tags=["test", "basic"],
            is_public=False
        )
    
    @pytest.fixture
    def sample_template_doc(self):
        """Sample template document"""
        return {
            "id": str(uuid.uuid4()),
            "name": "Test Template",
            "description": "A test search template",
            "category": SearchTemplateCategory.GENERAL,
            "template_type": SearchTemplateType.BASIC,
            "config": {
                "search_type": "basic",
                "default_query": "test query",
                "indices": ["assets"],
                "fields": ["title", "description"],
                "default_filters": []
            },
            "parameters": [
                {
                    "name": "query",
                    "type": "string",
                    "description": "Search query",
                    "required": True
                }
            ],
            "tags": ["test", "basic"],
            "is_public": False,
            "created_by": "test-user-123",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "version": 1
        }
    
    @pytest.mark.asyncio
    async def test_create_template_success(self, search_template_service, sample_template_create, mock_mongodb):
        """Test successful template creation"""
        # Mock database operations
        mock_mongodb.search_templates.insert_one = AsyncMock()
        mock_mongodb.search_template_stats.insert_one = AsyncMock()
        
        # Mock _ensure_indexes
        search_template_service._ensure_indexes = AsyncMock()
        
        # Create template
        result = await search_template_service.create_template(
            template_data=sample_template_create,
            user_id="test-user-123"
        )
        
        # Verify template was created
        assert isinstance(result, SearchTemplate)
        assert result.name == sample_template_create.name
        assert result.description == sample_template_create.description
        assert result.created_by == "test-user-123"
        assert result.version == 1
        
        # Verify database calls
        mock_mongodb.search_templates.insert_one.assert_called_once()
        mock_mongodb.search_template_stats.insert_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_template_duplicate_name(self, search_template_service, sample_template_create, mock_mongodb):
        """Test template creation with duplicate name"""
        # Mock duplicate key error
        mock_mongodb.search_templates.insert_one = AsyncMock(side_effect=DuplicateKeyError("duplicate"))
        
        # Mock _ensure_indexes
        search_template_service._ensure_indexes = AsyncMock()
        
        # Try to create template
        with pytest.raises(ValidationError, match="Template with this name already exists"):
            await search_template_service.create_template(
                template_data=sample_template_create,
                user_id="test-user-123"
            )
    
    @pytest.mark.asyncio
    async def test_get_template_success(self, search_template_service, sample_template_doc, mock_mongodb):
        """Test successful template retrieval"""
        # Mock database query
        mock_mongodb.search_templates.find_one = AsyncMock(return_value=sample_template_doc)
        
        # Mock access check
        search_template_service._has_access = AsyncMock(return_value=True)
        
        # Get template
        result = await search_template_service.get_template(
            template_id=sample_template_doc["id"],
            user_id="test-user-123"
        )
        
        # Verify result
        assert isinstance(result, SearchTemplate)
        assert result.name == sample_template_doc["name"]
        assert result.id == sample_template_doc["id"]
    
    @pytest.mark.asyncio
    async def test_get_template_not_found(self, search_template_service, mock_mongodb):
        """Test template retrieval when template doesn't exist"""
        # Mock database query
        mock_mongodb.search_templates.find_one = AsyncMock(return_value=None)
        
        # Try to get template
        with pytest.raises(NotFoundError):
            await search_template_service.get_template(
                template_id="non-existent-id",
                user_id="test-user-123"
            )
    
    @pytest.mark.asyncio
    async def test_get_template_access_denied(self, search_template_service, sample_template_doc, mock_mongodb):
        """Test template retrieval with access denied"""
        # Mock database query
        mock_mongodb.search_templates.find_one = AsyncMock(return_value=sample_template_doc)
        
        # Mock access check
        search_template_service._has_access = AsyncMock(return_value=False)
        
        # Try to get template
        with pytest.raises(ValidationError, match="Access denied"):
            await search_template_service.get_template(
                template_id=sample_template_doc["id"],
                user_id="other-user"
            )
    
    @pytest.mark.asyncio
    async def test_update_template_success(self, search_template_service, sample_template_doc, mock_mongodb):
        """Test successful template update"""
        # Mock database operations
        mock_mongodb.search_templates.find_one = AsyncMock(return_value=sample_template_doc)
        mock_mongodb.search_templates.update_one = AsyncMock()
        
        # Updated template doc
        updated_doc = sample_template_doc.copy()
        updated_doc["name"] = "Updated Template"
        updated_doc["version"] = 2
        mock_mongodb.search_templates.find_one.side_effect = [sample_template_doc, updated_doc]
        
        # Mock validation
        search_template_service._validate_template_config = AsyncMock()
        
        # Update template
        update_data = SearchTemplateUpdate(name="Updated Template")
        result = await search_template_service.update_template(
            template_id=sample_template_doc["id"],
            template_data=update_data,
            user_id="test-user-123"
        )
        
        # Verify result
        assert isinstance(result, SearchTemplate)
        assert result.name == "Updated Template"
        assert result.version == 2
        
        # Verify database calls
        mock_mongodb.search_templates.update_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_template_permission_denied(self, search_template_service, sample_template_doc, mock_mongodb):
        """Test template update with permission denied"""
        # Mock database query
        mock_mongodb.search_templates.find_one = AsyncMock(return_value=sample_template_doc)
        
        # Try to update template as different user
        update_data = SearchTemplateUpdate(name="Updated Template")
        with pytest.raises(ValidationError, match="Only the template creator can update"):
            await search_template_service.update_template(
                template_id=sample_template_doc["id"],
                template_data=update_data,
                user_id="other-user"
            )
    
    @pytest.mark.asyncio
    async def test_delete_template_success(self, search_template_service, sample_template_doc, mock_mongodb):
        """Test successful template deletion"""
        # Mock database operations
        mock_mongodb.search_templates.find_one = AsyncMock(return_value=sample_template_doc)
        mock_mongodb.search_templates.delete_one = AsyncMock()
        mock_mongodb.search_template_stats.delete_one = AsyncMock()
        mock_mongodb.search_template_favorites.delete_many = AsyncMock()
        mock_mongodb.search_template_shares.delete_many = AsyncMock()
        
        # Delete template
        result = await search_template_service.delete_template(
            template_id=sample_template_doc["id"],
            user_id="test-user-123"
        )
        
        # Verify result
        assert result is True
        
        # Verify database calls
        mock_mongodb.search_templates.delete_one.assert_called_once()
        mock_mongodb.search_template_stats.delete_one.assert_called_once()
        mock_mongodb.search_template_favorites.delete_many.assert_called_once()
        mock_mongodb.search_template_shares.delete_many.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_templates_success(self, search_template_service, mock_mongodb):
        """Test successful template listing"""
        # Mock database operations
        sample_templates = [
            {
                "id": str(uuid.uuid4()),
                "name": "Template 1",
                "description": "First template",
                "category": SearchTemplateCategory.GENERAL,
                "template_type": SearchTemplateType.BASIC,
                "config": {},
                "parameters": [],
                "tags": [],
                "is_public": True,
                "created_by": "user1",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "version": 1
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Template 2",
                "description": "Second template",
                "category": SearchTemplateCategory.GENERAL,
                "template_type": SearchTemplateType.ADVANCED,
                "config": {},
                "parameters": [],
                "tags": [],
                "is_public": True,
                "created_by": "user2",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "version": 1
            }
        ]
        
        mock_cursor = AsyncMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=sample_templates)
        
        mock_mongodb.search_templates.find.return_value = mock_cursor
        mock_mongodb.search_templates.count_documents = AsyncMock(return_value=2)
        mock_mongodb.search_template_stats.find_one = AsyncMock(return_value={"usage_count": 5, "favorite_count": 2})
        
        # Mock shared template IDs
        search_template_service._get_shared_template_ids = AsyncMock(return_value=[])
        
        # List templates
        result = await search_template_service.list_templates(
            user_id="test-user-123",
            page=1,
            limit=20
        )
        
        # Verify result
        assert isinstance(result, SearchTemplateList)
        assert len(result.templates) == 2
        assert result.total == 2
        assert result.page == 1
        assert result.limit == 20
        assert result.pages == 1
    
    @pytest.mark.asyncio
    async def test_execute_template_success(self, search_template_service, sample_template_doc, mock_mongodb):
        """Test successful template execution"""
        # Mock get_template
        search_template_service.get_template = AsyncMock(return_value=SearchTemplate(**sample_template_doc))
        
        # Mock _build_search_query
        from src.models.schemas import SearchQuery
        mock_search_query = SearchQuery(
            query="test query",
            search_type=SearchType.BASIC,
            indices=[IndexType.ASSETS]
        )
        search_template_service._build_search_query = AsyncMock(return_value=mock_search_query)
        
        # Mock search service
        from src.models.schemas import SearchResponse
        mock_search_response = SearchResponse(
            hits=[],
            total=0,
            took=10,
            aggregations={}
        )
        search_template_service.search_service.search = AsyncMock(return_value=mock_search_response)
        
        # Mock _update_usage_stats
        search_template_service._update_usage_stats = AsyncMock()
        
        # Execute template
        execution_data = SearchTemplateExecute(parameters={"query": "test"})
        result = await search_template_service.execute_template(
            template_id=sample_template_doc["id"],
            execution_data=execution_data,
            user_id="test-user-123"
        )
        
        # Verify result
        assert isinstance(result, SearchTemplateExecuteResponse)
        assert result.template_id == sample_template_doc["id"]
        assert result.template_name == sample_template_doc["name"]
        assert result.search_response == mock_search_response
        assert result.execution_time > 0
    
    @pytest.mark.asyncio
    async def test_add_to_favorites_success(self, search_template_service, sample_template_doc, mock_mongodb):
        """Test successful template favorite addition"""
        # Mock get_template
        search_template_service.get_template = AsyncMock(return_value=SearchTemplate(**sample_template_doc))
        
        # Mock database operations
        mock_mongodb.search_template_favorites.insert_one = AsyncMock()
        mock_mongodb.search_template_stats.update_one = AsyncMock()
        
        # Add to favorites
        result = await search_template_service.add_to_favorites(
            template_id=sample_template_doc["id"],
            user_id="test-user-123"
        )
        
        # Verify result
        assert result is True
        
        # Verify database calls
        mock_mongodb.search_template_favorites.insert_one.assert_called_once()
        mock_mongodb.search_template_stats.update_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_template_stats_success(self, search_template_service, sample_template_doc, mock_mongodb):
        """Test successful template stats retrieval"""
        # Mock get_template
        search_template_service.get_template = AsyncMock(return_value=SearchTemplate(**sample_template_doc))
        
        # Mock database query
        stats_doc = {
            "template_id": sample_template_doc["id"],
            "usage_count": 10,
            "favorite_count": 5,
            "last_used": datetime.utcnow(),
            "created_at": datetime.utcnow()
        }
        mock_mongodb.search_template_stats.find_one = AsyncMock(return_value=stats_doc)
        
        # Get stats
        result = await search_template_service.get_template_stats(
            template_id=sample_template_doc["id"],
            user_id="test-user-123"
        )
        
        # Verify result
        assert isinstance(result, SearchTemplateStats)
        assert result.template_id == sample_template_doc["id"]
        assert result.usage_count == 10
        assert result.favorite_count == 5
    
    @pytest.mark.asyncio
    async def test_export_template_success(self, search_template_service, sample_template_doc):
        """Test successful template export"""
        # Mock get_template
        search_template_service.get_template = AsyncMock(return_value=SearchTemplate(**sample_template_doc))
        
        # Export template
        result = await search_template_service.export_template(
            template_id=sample_template_doc["id"],
            user_id="test-user-123"
        )
        
        # Verify result
        assert isinstance(result, SearchTemplateExport)
        assert result.template.id == sample_template_doc["id"]
        assert result.exported_by == "test-user-123"
        assert result.format_version == "1.0"
    
    @pytest.mark.asyncio
    async def test_import_template_success(self, search_template_service, sample_template_doc, mock_mongodb):
        """Test successful template import"""
        # Mock create_template
        search_template_service.create_template = AsyncMock(return_value=SearchTemplate(**sample_template_doc))
        
        # Mock database query for name conflict check
        mock_mongodb.search_templates.find_one = AsyncMock(return_value=None)
        
        # Create import data
        import_data = SearchTemplateImport(
            template=SearchTemplate(**sample_template_doc),
            format_version="1.0"
        )
        
        # Import template
        result = await search_template_service.import_template(
            import_data=import_data,
            user_id="test-user-123"
        )
        
        # Verify result
        assert isinstance(result, SearchTemplate)
        assert result.id == sample_template_doc["id"]
        
        # Verify create_template was called
        search_template_service.create_template.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_share_template_success(self, search_template_service, sample_template_doc, mock_mongodb):
        """Test successful template sharing"""
        # Mock database operations
        mock_mongodb.search_templates.find_one = AsyncMock(return_value=sample_template_doc)
        mock_mongodb.search_template_shares.update_one = AsyncMock()
        
        # Share template
        share_data = SearchTemplateShare(
            shared_with=["user1", "user2"],
            permissions=["read", "execute"]
        )
        result = await search_template_service.share_template(
            template_id=sample_template_doc["id"],
            share_data=share_data,
            user_id="test-user-123"
        )
        
        # Verify result
        assert result is True
        
        # Verify database calls (one per shared user)
        assert mock_mongodb.search_template_shares.update_one.call_count == 2
    
    @pytest.mark.asyncio
    async def test_has_access_public_template(self, search_template_service):
        """Test access check for public template"""
        template = {"is_public": True}
        
        result = await search_template_service._has_access(template, "any-user")
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_has_access_owner(self, search_template_service):
        """Test access check for template owner"""
        template = {"is_public": False, "created_by": "test-user"}
        
        result = await search_template_service._has_access(template, "test-user")
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_has_access_shared_user(self, search_template_service, mock_mongodb):
        """Test access check for shared user"""
        template = {"id": "template-123", "is_public": False, "created_by": "owner"}
        
        # Mock shared template check
        mock_mongodb.search_template_shares.find_one = AsyncMock(return_value={"template_id": "template-123"})
        
        result = await search_template_service._has_access(template, "shared-user")
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_has_access_denied(self, search_template_service, mock_mongodb):
        """Test access check denial"""
        template = {"id": "template-123", "is_public": False, "created_by": "owner"}
        
        # Mock no shared template
        mock_mongodb.search_template_shares.find_one = AsyncMock(return_value=None)
        
        result = await search_template_service._has_access(template, "random-user")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_build_search_query_basic(self, search_template_service, sample_template_doc):
        """Test building search query from template"""
        template = SearchTemplate(**sample_template_doc)
        parameters = {"query": "test search"}
        
        result = await search_template_service._build_search_query(template, parameters)
        
        assert result.query == "test query"  # Default query from template
        assert result.search_type == SearchType.BASIC
        assert result.indices == [IndexType.ASSETS]
        assert result.page == 1
        assert result.limit == 20
    
    @pytest.mark.asyncio
    async def test_build_search_query_with_parameters(self, search_template_service, sample_template_doc):
        """Test building search query with parameters"""
        # Update template config to use parameter substitution
        sample_template_doc["config"]["default_query"] = "search for {query}"
        template = SearchTemplate(**sample_template_doc)
        parameters = {"query": "videos", "page": 2, "limit": 10}
        
        result = await search_template_service._build_search_query(template, parameters)
        
        assert result.query == "search for videos"
        assert result.page == 2
        assert result.limit == 10