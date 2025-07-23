"""
Tests for SearchHistoryService
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta

from src.services.search_history_service import SearchHistoryService
from src.models.schemas import (
    SearchHistoryEntry, SearchHistoryList, SearchHistoryStats,
    SearchType
)
from src.core.exceptions import ValidationError, NotFoundError


@pytest.fixture
def mock_db():
    """Create a mock MongoDB database"""
    return Mock()


@pytest.fixture
def mock_search_history_model():
    """Create a mock SearchHistoryModel"""
    return Mock()


@pytest.fixture
def search_history_service(mock_db, mock_search_history_model):
    """Create a SearchHistoryService instance"""
    service = SearchHistoryService(mock_db)
    service.search_history_model = mock_search_history_model
    return service


@pytest.fixture
def sample_history_entry():
    """Create a sample search history entry"""
    return {
        "id": "507f1f77bcf86cd799439011",
        "user_id": "user123",
        "query": "test video",
        "search_type": "basic",
        "indices": ["assets", "metadata"],
        "filters": {"asset_type": "video"},
        "results_count": 25,
        "response_time_ms": 120,
        "ip_address": "192.168.1.1",
        "user_agent": "Mozilla/5.0 (Test Browser)",
        "timestamp": datetime.utcnow()
    }


class TestSearchHistoryService:
    """Test SearchHistoryService functionality"""
    
    @pytest.mark.asyncio
    async def test_log_search_success(
        self, 
        search_history_service, 
        mock_search_history_model
    ):
        """Test successful search logging"""
        # Setup mocks
        mock_search_history_model.create.return_value = "507f1f77bcf86cd799439011"
        
        # Execute
        result = await search_history_service.log_search(
            user_id="user123",
            query="test video",
            search_type=SearchType.BASIC,
            indices=["assets"],
            filters={"asset_type": "video"},
            results_count=25,
            response_time_ms=120,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0"
        )
        
        # Verify
        assert result == "507f1f77bcf86cd799439011"
        
        # Verify model call
        mock_search_history_model.create.assert_called_once()
        create_call_args = mock_search_history_model.create.call_args[0][0]
        assert create_call_args["user_id"] == "user123"
        assert create_call_args["query"] == "test video"
        assert create_call_args["search_type"] == "basic"
        assert create_call_args["indices"] == ["assets"]
        assert create_call_args["filters"] == {"asset_type": "video"}
        assert create_call_args["results_count"] == 25
        assert create_call_args["response_time_ms"] == 120
        assert create_call_args["ip_address"] == "192.168.1.1"
        assert create_call_args["user_agent"] == "Mozilla/5.0"
    
    @pytest.mark.asyncio
    async def test_log_search_failure(
        self, 
        search_history_service, 
        mock_search_history_model
    ):
        """Test search logging failure"""
        # Setup mocks
        mock_search_history_model.create.side_effect = Exception("Database error")
        
        # Execute and verify exception
        with pytest.raises(ValidationError) as exc_info:
            await search_history_service.log_search(
                user_id="user123",
                query="test video",
                search_type=SearchType.BASIC,
                indices=["assets"]
            )
        
        assert "Failed to log search" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_user_history_success(
        self, 
        search_history_service, 
        mock_search_history_model,
        sample_history_entry
    ):
        """Test successful user history retrieval"""
        # Setup mocks
        mock_search_history_model.get_user_history.return_value = ([sample_history_entry], 1)
        
        # Execute
        result = await search_history_service.get_user_history(
            user_id="user123",
            page=1,
            per_page=20
        )
        
        # Verify
        assert isinstance(result, SearchHistoryList)
        assert len(result.entries) == 1
        assert result.total == 1
        assert result.page == 1
        assert result.per_page == 20
        assert result.total_pages == 1
        
        # Verify entry format
        entry = result.entries[0]
        assert isinstance(entry, SearchHistoryEntry)
        assert entry.user_id == "user123"
        assert entry.query == "test video"
        assert entry.search_type == SearchType.BASIC
        
        # Verify model call
        mock_search_history_model.get_user_history.assert_called_once_with(
            user_id="user123",
            skip=0,
            limit=20,
            search_type=None,
            query_filter=None
        )
    
    @pytest.mark.asyncio
    async def test_get_user_history_with_filters(
        self, 
        search_history_service, 
        mock_search_history_model,
        sample_history_entry
    ):
        """Test user history retrieval with filters"""
        # Setup mocks
        mock_search_history_model.get_user_history.return_value = ([sample_history_entry], 1)
        
        # Execute
        result = await search_history_service.get_user_history(
            user_id="user123",
            page=2,
            per_page=10,
            search_type="basic",
            query_filter="video"
        )
        
        # Verify
        assert isinstance(result, SearchHistoryList)
        assert result.page == 2
        assert result.per_page == 10
        
        # Verify model call with filters
        mock_search_history_model.get_user_history.assert_called_once_with(
            user_id="user123",
            skip=10,
            limit=10,
            search_type="basic",
            query_filter="video"
        )
    
    @pytest.mark.asyncio
    async def test_get_user_history_per_page_limit(
        self, 
        search_history_service, 
        mock_search_history_model
    ):
        """Test per_page limit enforcement"""
        # Setup mocks
        mock_search_history_model.get_user_history.return_value = ([], 0)
        
        # Execute with per_page > 100
        await search_history_service.get_user_history(
            user_id="user123",
            per_page=150
        )
        
        # Verify per_page was limited to 100
        mock_search_history_model.get_user_history.assert_called_once_with(
            user_id="user123",
            skip=0,
            limit=100,
            search_type=None,
            query_filter=None
        )
    
    @pytest.mark.asyncio
    async def test_get_user_stats_success(
        self, 
        search_history_service, 
        mock_search_history_model
    ):
        """Test successful user stats retrieval"""
        # Setup mocks
        mock_stats = {
            "total_searches": 50,
            "unique_queries": 25,
            "avg_response_time_ms": 150.5,
            "avg_results_per_search": 30.2,
            "most_common_search_type": "basic"
        }
        mock_search_history_model.get_user_stats.return_value = mock_stats
        
        mock_top_queries = [
            {"query": "video", "count": 10, "avg_results": 25, "avg_response_time_ms": 120, "last_used": datetime.utcnow()}
        ]
        mock_search_history_model.get_top_queries.return_value = mock_top_queries
        
        mock_volume_data = [
            {"date": "2024-01-15", "count": 5}
        ]
        mock_search_history_model.get_search_volume_by_day.return_value = mock_volume_data
        
        # Execute
        result = await search_history_service.get_user_stats(
            user_id="user123",
            days=30
        )
        
        # Verify
        assert isinstance(result, SearchHistoryStats)
        assert result.total_searches == 50
        assert result.unique_queries == 25
        assert result.avg_response_time_ms == 150.5
        assert result.avg_results_per_search == 30.2
        assert result.most_common_search_type == SearchType.BASIC
        assert len(result.top_queries) == 1
        assert len(result.search_volume_by_day) == 1
        
        # Verify model calls
        mock_search_history_model.get_user_stats.assert_called_once_with("user123", 30)
        mock_search_history_model.get_top_queries.assert_called_once_with("user123", days=30)
        mock_search_history_model.get_search_volume_by_day.assert_called_once_with("user123", 30)
    
    @pytest.mark.asyncio
    async def test_get_user_stats_days_limit(
        self, 
        search_history_service, 
        mock_search_history_model
    ):
        """Test days limit enforcement in get_user_stats"""
        # Setup mocks
        mock_search_history_model.get_user_stats.return_value = {
            "total_searches": 0,
            "unique_queries": 0,
            "avg_response_time_ms": 0,
            "avg_results_per_search": 0,
            "most_common_search_type": "basic"
        }
        mock_search_history_model.get_top_queries.return_value = []
        mock_search_history_model.get_search_volume_by_day.return_value = []
        
        # Execute with days > 365
        await search_history_service.get_user_stats(
            user_id="user123",
            days=400
        )
        
        # Verify days was limited to 365
        mock_search_history_model.get_user_stats.assert_called_once_with("user123", 365)
        mock_search_history_model.get_top_queries.assert_called_once_with("user123", days=365)
        mock_search_history_model.get_search_volume_by_day.assert_called_once_with("user123", 365)
    
    @pytest.mark.asyncio
    async def test_delete_user_history_success(
        self, 
        search_history_service, 
        mock_search_history_model
    ):
        """Test successful user history deletion"""
        # Setup mocks
        mock_search_history_model.delete_user_history.return_value = 10
        
        # Execute
        result = await search_history_service.delete_user_history(
            user_id="user123",
            older_than_days=90
        )
        
        # Verify
        assert result == 10
        
        # Verify model call
        mock_search_history_model.delete_user_history.assert_called_once_with(
            user_id="user123",
            older_than_days=90
        )
    
    @pytest.mark.asyncio
    async def test_delete_user_history_invalid_days(
        self, 
        search_history_service, 
        mock_search_history_model
    ):
        """Test delete user history with invalid days"""
        # Execute and verify exception
        with pytest.raises(ValidationError) as exc_info:
            await search_history_service.delete_user_history(
                user_id="user123",
                older_than_days=0
            )
        
        assert "older_than_days must be at least 1" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_clear_user_history_success(
        self, 
        search_history_service, 
        mock_search_history_model
    ):
        """Test successful user history clearing"""
        # Setup mocks
        mock_search_history_model.clear_user_history.return_value = 25
        
        # Execute
        result = await search_history_service.clear_user_history(user_id="user123")
        
        # Verify
        assert result == 25
        
        # Verify model call
        mock_search_history_model.clear_user_history.assert_called_once_with("user123")
    
    def test_format_history_entry(self, search_history_service, sample_history_entry):
        """Test formatting history entry"""
        # Execute
        result = search_history_service._format_history_entry(sample_history_entry)
        
        # Verify
        assert isinstance(result, SearchHistoryEntry)
        assert result.id == "507f1f77bcf86cd799439011"
        assert result.user_id == "user123"
        assert result.query == "test video"
        assert result.search_type == SearchType.BASIC
        assert result.indices == ["assets", "metadata"]
        assert result.filters == {"asset_type": "video"}
        assert result.results_count == 25
        assert result.response_time_ms == 120
        assert result.ip_address == "192.168.1.1"
        assert result.user_agent == "Mozilla/5.0 (Test Browser)"
        assert isinstance(result.timestamp, datetime)
    
    def test_extract_request_info(self, search_history_service):
        """Test extracting request information"""
        # Create mock request
        mock_request = Mock()
        mock_request.client.host = "192.168.1.1"
        mock_request.headers = {"user-agent": "Mozilla/5.0 (Test Browser)"}
        
        # Execute
        result = search_history_service.extract_request_info(mock_request)
        
        # Verify
        assert result["ip_address"] == "192.168.1.1"
        assert result["user_agent"] == "Mozilla/5.0 (Test Browser)"
    
    def test_extract_request_info_no_client(self, search_history_service):
        """Test extracting request info when client is None"""
        # Create mock request without client
        mock_request = Mock()
        mock_request.client = None
        mock_request.headers = {"user-agent": "Mozilla/5.0 (Test Browser)"}
        
        # Execute
        result = search_history_service.extract_request_info(mock_request)
        
        # Verify
        assert result["ip_address"] is None
        assert result["user_agent"] == "Mozilla/5.0 (Test Browser)"