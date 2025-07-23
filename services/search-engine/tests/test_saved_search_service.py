"""
Tests for SavedSearchService
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from src.services.saved_search_service import SavedSearchService
from src.models.schemas import (
    SavedSearchCreate, SavedSearchUpdate, SavedSearch, SavedSearchList,
    SavedSearchExecute, FilteredSearchQuery, FilteredSearchResponse,
    FilterCondition, FilterType, SearchType, SortOrder
)
from src.core.exceptions import SearchError, NotFoundError, ValidationError


@pytest.fixture
def mock_db():
    """Create a mock MongoDB database"""
    return Mock()


@pytest.fixture
def mock_saved_search_model():
    """Create a mock SavedSearchModel"""
    return Mock()


@pytest.fixture
def saved_search_service(mock_db, mock_saved_search_model):
    """Create a SavedSearchService instance"""
    service = SavedSearchService(mock_db)
    service.saved_search_model = mock_saved_search_model
    return service


@pytest.fixture
def sample_query():
    """Create a sample FilteredSearchQuery"""
    return FilteredSearchQuery(
        query="test video",
        filters=[
            FilterCondition(field="asset_type", type=FilterType.TERM, value="video")
        ],
        size=20,
        from_=0
    )


@pytest.fixture
def sample_saved_search_create(sample_query):
    """Create a sample SavedSearchCreate"""
    return SavedSearchCreate(
        name="Test Video Search",
        description="A search for test videos",
        query=sample_query,
        is_public=False,
        tags=["video", "test"],
        notify_on_new_results=True
    )


@pytest.fixture
def sample_saved_search_doc():
    """Create a sample saved search document"""
    return {
        "id": "507f1f77bcf86cd799439011",
        "user_id": "user123",
        "name": "Test Video Search",
        "description": "A search for test videos",
        "query": {
            "query": "test video",
            "filters": [
                {"field": "asset_type", "type": "term", "value": "video"}
            ],
            "size": 20,
            "from": 0
        },
        "is_public": False,
        "tags": ["video", "test"],
        "notify_on_new_results": True,
        "usage_count": 5,
        "last_used_at": datetime.utcnow(),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }


class TestSavedSearchService:
    """Test SavedSearchService functionality"""
    
    @pytest.mark.asyncio
    async def test_create_saved_search_success(
        self, 
        saved_search_service, 
        mock_saved_search_model,
        sample_saved_search_create,
        sample_saved_search_doc
    ):
        """Test successful saved search creation"""
        # Setup mocks
        mock_saved_search_model.check_name_exists.return_value = False
        mock_saved_search_model.create.return_value = "507f1f77bcf86cd799439011"
        mock_saved_search_model.get_by_id.return_value = sample_saved_search_doc
        
        # Execute
        result = await saved_search_service.create_saved_search(
            user_id="user123",
            saved_search=sample_saved_search_create
        )
        
        # Verify
        assert isinstance(result, SavedSearch)
        assert result.name == "Test Video Search"
        assert result.user_id == "user123"
        assert result.is_public == False
        assert len(result.tags) == 2
        
        # Verify model calls
        mock_saved_search_model.check_name_exists.assert_called_once_with("user123", "Test Video Search")
        mock_saved_search_model.create.assert_called_once()
        mock_saved_search_model.get_by_id.assert_called_once_with("507f1f77bcf86cd799439011")
    
    @pytest.mark.asyncio
    async def test_create_saved_search_duplicate_name(
        self, 
        saved_search_service, 
        mock_saved_search_model,
        sample_saved_search_create
    ):
        """Test creating saved search with duplicate name"""
        # Setup mocks
        mock_saved_search_model.check_name_exists.return_value = True
        
        # Execute and verify exception
        with pytest.raises(ValidationError) as exc_info:
            await saved_search_service.create_saved_search(
                user_id="user123",
                saved_search=sample_saved_search_create
            )
        
        assert "already exists" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_saved_search_success(
        self, 
        saved_search_service, 
        mock_saved_search_model,
        sample_saved_search_doc
    ):
        """Test successful saved search retrieval"""
        # Setup mocks
        mock_saved_search_model.get_by_id.return_value = sample_saved_search_doc
        
        # Execute
        result = await saved_search_service.get_saved_search(
            search_id="507f1f77bcf86cd799439011",
            user_id="user123"
        )
        
        # Verify
        assert isinstance(result, SavedSearch)
        assert result.id == "507f1f77bcf86cd799439011"
        assert result.name == "Test Video Search"
    
    @pytest.mark.asyncio
    async def test_get_saved_search_not_found(
        self, 
        saved_search_service, 
        mock_saved_search_model
    ):
        """Test getting non-existent saved search"""
        # Setup mocks
        mock_saved_search_model.get_by_id.return_value = None
        
        # Execute and verify exception
        with pytest.raises(NotFoundError):
            await saved_search_service.get_saved_search(
                search_id="507f1f77bcf86cd799439011",
                user_id="user123"
            )
    
    @pytest.mark.asyncio
    async def test_list_user_searches(
        self, 
        saved_search_service, 
        mock_saved_search_model,
        sample_saved_search_doc
    ):
        """Test listing user's saved searches"""
        # Setup mocks
        mock_saved_search_model.get_user_searches.return_value = ([sample_saved_search_doc], 1)
        
        # Execute
        result = await saved_search_service.list_user_searches(
            user_id="user123",
            page=1,
            per_page=20
        )
        
        # Verify
        assert isinstance(result, SavedSearchList)
        assert len(result.searches) == 1
        assert result.total == 1
        assert result.page == 1
        assert result.per_page == 20
        assert result.total_pages == 1
        
        # Verify model call
        mock_saved_search_model.get_user_searches.assert_called_once_with(
            "user123", skip=0, limit=20, include_public=True
        )
    
    @pytest.mark.asyncio
    async def test_search_by_tags(
        self, 
        saved_search_service, 
        mock_saved_search_model,
        sample_saved_search_doc
    ):
        """Test searching saved searches by tags"""
        # Setup mocks
        mock_saved_search_model.search_by_tags.return_value = ([sample_saved_search_doc], 1)
        
        # Execute
        result = await saved_search_service.search_by_tags(
            tags=["video", "test"],
            page=1,
            per_page=20
        )
        
        # Verify
        assert isinstance(result, SavedSearchList)
        assert len(result.searches) == 1
        assert result.total == 1
        
        # Verify model call
        mock_saved_search_model.search_by_tags.assert_called_once_with(
            ["video", "test"], skip=0, limit=20
        )
    
    @pytest.mark.asyncio
    async def test_get_popular_searches(
        self, 
        saved_search_service, 
        mock_saved_search_model,
        sample_saved_search_doc
    ):
        """Test getting popular searches"""
        # Setup mocks
        mock_saved_search_model.get_popular_searches.return_value = [sample_saved_search_doc]
        
        # Execute
        result = await saved_search_service.get_popular_searches(limit=10)
        
        # Verify
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], SavedSearch)
        
        # Verify model call
        mock_saved_search_model.get_popular_searches.assert_called_once_with(10)
    
    @pytest.mark.asyncio
    async def test_update_saved_search_success(
        self, 
        saved_search_service, 
        mock_saved_search_model,
        sample_saved_search_doc
    ):
        """Test successful saved search update"""
        # Setup mocks
        mock_saved_search_model.get_by_id.return_value = sample_saved_search_doc
        mock_saved_search_model.check_name_exists.return_value = False
        mock_saved_search_model.update.return_value = True
        
        updated_doc = sample_saved_search_doc.copy()
        updated_doc["name"] = "Updated Search Name"
        mock_saved_search_model.get_by_id.return_value = updated_doc
        
        # Execute
        update_data = SavedSearchUpdate(name="Updated Search Name")
        result = await saved_search_service.update_saved_search(
            search_id="507f1f77bcf86cd799439011",
            user_id="user123",
            update_data=update_data
        )
        
        # Verify
        assert isinstance(result, SavedSearch)
        assert result.name == "Updated Search Name"
        
        # Verify model calls
        mock_saved_search_model.update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_saved_search_not_owner(
        self, 
        saved_search_service, 
        mock_saved_search_model,
        sample_saved_search_doc
    ):
        """Test updating saved search by non-owner"""
        # Setup mocks - different user_id
        doc = sample_saved_search_doc.copy()
        doc["user_id"] = "other_user"
        mock_saved_search_model.get_by_id.return_value = doc
        
        # Execute and verify exception
        update_data = SavedSearchUpdate(name="Updated Search Name")
        with pytest.raises(ValidationError) as exc_info:
            await saved_search_service.update_saved_search(
                search_id="507f1f77bcf86cd799439011",
                user_id="user123",
                update_data=update_data
            )
        
        assert "only update your own" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_delete_saved_search_success(
        self, 
        saved_search_service, 
        mock_saved_search_model
    ):
        """Test successful saved search deletion"""
        # Setup mocks
        mock_saved_search_model.delete.return_value = True
        
        # Execute
        result = await saved_search_service.delete_saved_search(
            search_id="507f1f77bcf86cd799439011",
            user_id="user123"
        )
        
        # Verify
        assert result == True
        
        # Verify model call
        mock_saved_search_model.delete.assert_called_once_with(
            "507f1f77bcf86cd799439011", "user123"
        )
    
    @pytest.mark.asyncio
    async def test_delete_saved_search_not_found(
        self, 
        saved_search_service, 
        mock_saved_search_model
    ):
        """Test deleting non-existent saved search"""
        # Setup mocks
        mock_saved_search_model.delete.return_value = False
        
        # Execute and verify exception
        with pytest.raises(NotFoundError):
            await saved_search_service.delete_saved_search(
                search_id="507f1f77bcf86cd799439011",
                user_id="user123"
            )
    
    @pytest.mark.asyncio
    async def test_execute_saved_search_success(
        self, 
        saved_search_service, 
        mock_saved_search_model,
        sample_saved_search_doc
    ):
        """Test successful saved search execution"""
        # Setup mocks
        mock_saved_search_model.get_by_id.return_value = sample_saved_search_doc
        mock_saved_search_model.increment_usage.return_value = True
        
        # Mock the search service
        mock_search_response = FilteredSearchResponse(
            query="test video",
            total_hits=10,
            hits=[],
            facets=[],
            applied_filters=[],
            took=50,
            timed_out=False,
            page=1,
            per_page=20,
            total_pages=1
        )
        
        with patch('src.services.saved_search_service.get_search_service') as mock_get_search:
            mock_search_service = AsyncMock()
            mock_search_service.filtered_search.return_value = mock_search_response
            mock_get_search.return_value = mock_search_service
            
            # Execute
            result = await saved_search_service.execute_saved_search(
                search_id="507f1f77bcf86cd799439011",
                user_id="user123"
            )
        
        # Verify
        assert isinstance(result, FilteredSearchResponse)
        assert result.total_hits == 10
        
        # Verify model calls
        mock_saved_search_model.increment_usage.assert_called_once_with("507f1f77bcf86cd799439011")
        mock_search_service.filtered_search.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_saved_search_with_overrides(
        self, 
        saved_search_service, 
        mock_saved_search_model,
        sample_saved_search_doc
    ):
        """Test executing saved search with parameter overrides"""
        # Setup mocks
        mock_saved_search_model.get_by_id.return_value = sample_saved_search_doc
        mock_saved_search_model.increment_usage.return_value = True
        
        # Mock the search service
        mock_search_response = FilteredSearchResponse(
            query="test video",
            total_hits=5,
            hits=[],
            facets=[],
            applied_filters=[],
            took=30,
            timed_out=False,
            page=1,
            per_page=10,
            total_pages=1
        )
        
        with patch('src.services.saved_search_service.get_search_service') as mock_get_search:
            mock_search_service = AsyncMock()
            mock_search_service.filtered_search.return_value = mock_search_response
            mock_get_search.return_value = mock_search_service
            
            # Execute with overrides
            execute_params = SavedSearchExecute(
                size=10,
                from_=0,
                sort_by="created_at",
                sort_order=SortOrder.DESC,
                additional_filters=[
                    FilterCondition(field="status", type=FilterType.TERM, value="active")
                ]
            )
            
            result = await saved_search_service.execute_saved_search(
                search_id="507f1f77bcf86cd799439011",
                user_id="user123",
                execute_params=execute_params
            )
        
        # Verify
        assert isinstance(result, FilteredSearchResponse)
        assert result.total_hits == 5
        
        # Verify the query was modified with overrides
        called_query = mock_search_service.filtered_search.call_args[0][0]
        assert called_query.size == 10
        assert called_query.sort_by == "created_at"
        assert called_query.sort_order == SortOrder.DESC
        assert len(called_query.filters) == 2  # Original + additional
    
    def test_format_saved_search(self, saved_search_service, sample_saved_search_doc):
        """Test formatting saved search document"""
        # Execute
        result = saved_search_service._format_saved_search(sample_saved_search_doc)
        
        # Verify
        assert isinstance(result, SavedSearch)
        assert result.id == "507f1f77bcf86cd799439011"
        assert result.name == "Test Video Search"
        assert result.user_id == "user123"
        assert isinstance(result.query, FilteredSearchQuery)
        assert result.usage_count == 5
        assert result.is_public == False
        assert len(result.tags) == 2