"""
Tests for SearchAnalyticsService
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta

from src.services.search_analytics_service import SearchAnalyticsService
from src.models.schemas import (
    SearchAnalyticsAggregation, SearchAnalyticsTimeRange, SearchAnalyticsFilter,
    SearchAnalyticsReport, SearchPerformanceMetrics, SearchTrendData,
    SearchType
)
from src.core.exceptions import ValidationError


@pytest.fixture
def mock_db():
    """Create a mock MongoDB database"""
    return Mock()


@pytest.fixture
def mock_analytics_model():
    """Create a mock SearchAnalyticsModel"""
    return Mock()


@pytest.fixture
def search_analytics_service(mock_db, mock_analytics_model):
    """Create a SearchAnalyticsService instance"""
    service = SearchAnalyticsService(mock_db)
    service.analytics_model = mock_analytics_model
    return service


@pytest.fixture
def sample_time_range():
    """Create a sample time range"""
    return SearchAnalyticsTimeRange(
        start_time=datetime.utcnow() - timedelta(days=7),
        end_time=datetime.utcnow(),
        interval="1h"
    )


@pytest.fixture
def sample_filters():
    """Create sample analytics filters"""
    return SearchAnalyticsFilter(
        search_type=SearchType.BASIC,
        query_contains="video",
        min_results=1,
        max_results=100
    )


class TestSearchAnalyticsService:
    """Test SearchAnalyticsService functionality"""
    
    @pytest.mark.asyncio
    async def test_log_search_analytics_success(
        self, 
        search_analytics_service, 
        mock_analytics_model
    ):
        """Test successful search analytics logging"""
        # Setup mocks
        mock_analytics_model.create.return_value = "507f1f77bcf86cd799439011"
        
        # Execute
        result = await search_analytics_service.log_search_analytics(
            query="test video",
            search_type=SearchType.BASIC,
            user_id="user123",
            session_id="session456",
            indices=["assets"],
            filters={"asset_type": "video"},
            results_count=25,
            response_time_ms=120,
            clicked_results=["asset1", "asset2"],
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            referrer="https://example.com",
            location={"country": "US", "city": "New York"}
        )
        
        # Verify
        assert result == "507f1f77bcf86cd799439011"
        
        # Verify model call
        mock_analytics_model.create.assert_called_once()
        create_args = mock_analytics_model.create.call_args[0][0]
        assert create_args["query"] == "test video"
        assert create_args["search_type"] == "basic"
        assert create_args["user_id"] == "user123"
        assert create_args["session_id"] == "session456"
        assert create_args["indices"] == ["assets"]
        assert create_args["filters"] == {"asset_type": "video"}
        assert create_args["results_count"] == 25
        assert create_args["response_time_ms"] == 120
        assert create_args["clicked_results"] == ["asset1", "asset2"]
        assert create_args["ip_address"] == "192.168.1.1"
        assert create_args["user_agent"] == "Mozilla/5.0"
        assert create_args["referrer"] == "https://example.com"
        assert create_args["location"] == {"country": "US", "city": "New York"}
    
    @pytest.mark.asyncio
    async def test_log_search_analytics_failure(
        self, 
        search_analytics_service, 
        mock_analytics_model
    ):
        """Test search analytics logging failure"""
        # Setup mocks
        mock_analytics_model.create.side_effect = Exception("Database error")
        
        # Execute - should not raise exception
        result = await search_analytics_service.log_search_analytics(
            query="test video",
            search_type=SearchType.BASIC
        )
        
        # Verify that failure doesn't break the service
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_search_analytics_success(
        self, 
        search_analytics_service, 
        mock_analytics_model,
        sample_time_range
    ):
        """Test successful search analytics retrieval"""
        # Setup mocks
        mock_analytics_model.get_aggregated_stats.return_value = {
            "total_searches": 1000,
            "unique_queries": 500,
            "unique_users": 200,
            "unique_sessions": 800,
            "avg_response_time_ms": 150.5,
            "avg_results_per_search": 25.3,
            "avg_clicks_per_search": 2.1,
            "click_through_rate": 35.7,
            "zero_result_rate": 8.2
        }
        
        mock_analytics_model.get_top_queries.return_value = [
            {"query": "video", "count": 100, "avg_response_time_ms": 120}
        ]
        
        mock_analytics_model.get_top_filters.return_value = [
            {"filter": {"asset_type": "video"}, "count": 50}
        ]
        
        mock_analytics_model.get_search_trends.return_value = [
            {"timestamp": "2024-01-15 10:00:00", "search_count": 10}
        ]
        
        mock_analytics_model.get_performance_metrics.return_value = {
            "avg_response_time_ms": 150.5,
            "p95_response_time_ms": 300.0
        }
        
        # Execute
        result = await search_analytics_service.get_search_analytics(
            time_range=sample_time_range
        )
        
        # Verify
        assert isinstance(result, SearchAnalyticsAggregation)
        assert result.total_searches == 1000
        assert result.unique_queries == 500
        assert result.unique_users == 200
        assert result.avg_response_time_ms == 150.5
        assert result.click_through_rate == 35.7
        assert result.zero_result_rate == 8.2
        assert len(result.top_queries) == 1
        assert len(result.top_filters) == 1
        assert len(result.search_patterns) == 1
        
        # Verify model calls
        mock_analytics_model.get_aggregated_stats.assert_called_once()
        mock_analytics_model.get_top_queries.assert_called_once()
        mock_analytics_model.get_top_filters.assert_called_once()
        mock_analytics_model.get_search_trends.assert_called_once()
        mock_analytics_model.get_performance_metrics.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_search_analytics_with_filters(
        self, 
        search_analytics_service, 
        mock_analytics_model,
        sample_time_range,
        sample_filters
    ):
        """Test search analytics with filters"""
        # Setup mocks
        mock_analytics_model.get_aggregated_stats.return_value = {
            "total_searches": 100,
            "unique_queries": 50,
            "unique_users": 20,
            "unique_sessions": 80,
            "avg_response_time_ms": 140.0,
            "avg_results_per_search": 30.0,
            "avg_clicks_per_search": 2.5,
            "click_through_rate": 40.0,
            "zero_result_rate": 5.0
        }
        
        mock_analytics_model.get_top_queries.return_value = []
        mock_analytics_model.get_top_filters.return_value = []
        mock_analytics_model.get_search_trends.return_value = []
        mock_analytics_model.get_performance_metrics.return_value = {
            "avg_response_time_ms": 140.0
        }
        
        # Execute
        result = await search_analytics_service.get_search_analytics(
            time_range=sample_time_range,
            filters=sample_filters
        )
        
        # Verify
        assert isinstance(result, SearchAnalyticsAggregation)
        assert result.total_searches == 100
        
        # Verify that filters were applied
        call_args = mock_analytics_model.get_aggregated_stats.call_args
        filters_arg = call_args[1]['filters']
        assert filters_arg["search_type"] == "basic"
        assert filters_arg["query"]["$regex"] == "video"
        assert filters_arg["results_count"]["$gte"] == 1
        assert filters_arg["results_count"]["$lte"] == 100
    
    @pytest.mark.asyncio
    async def test_get_search_performance_metrics(
        self, 
        search_analytics_service, 
        mock_analytics_model,
        sample_time_range
    ):
        """Test search performance metrics retrieval"""
        # Setup mocks
        mock_analytics_model.get_performance_metrics.return_value = {
            "avg_response_time_ms": 150.5,
            "p50_response_time_ms": 120.0,
            "p95_response_time_ms": 350.0,
            "p99_response_time_ms": 500.0,
            "slowest_queries": [{"query": "slow", "response_time_ms": 500}],
            "fastest_queries": [{"query": "fast", "response_time_ms": 50}],
            "error_rate": 2.5,
            "timeout_rate": 0.8
        }
        
        # Execute
        result = await search_analytics_service.get_search_performance_metrics(
            time_range=sample_time_range
        )
        
        # Verify
        assert isinstance(result, SearchPerformanceMetrics)
        assert result.avg_response_time_ms == 150.5
        assert result.p50_response_time_ms == 120.0
        assert result.p95_response_time_ms == 350.0
        assert result.p99_response_time_ms == 500.0
        assert result.error_rate == 2.5
        assert result.timeout_rate == 0.8
        assert len(result.slowest_queries) == 1
        assert len(result.fastest_queries) == 1
    
    @pytest.mark.asyncio
    async def test_get_search_trends(
        self, 
        search_analytics_service, 
        mock_analytics_model,
        sample_time_range
    ):
        """Test search trends retrieval"""
        # Setup mocks
        mock_analytics_model.get_search_trends.return_value = [
            {
                "timestamp": "2024-01-15 10:00:00",
                "search_count": 10,
                "unique_users": 5,
                "avg_response_time_ms": 120.0,
                "avg_results": 25.0,
                "click_through_rate": 30.0
            },
            {
                "timestamp": "2024-01-15 11:00:00",
                "search_count": 15,
                "unique_users": 8,
                "avg_response_time_ms": 130.0,
                "avg_results": 28.0,
                "click_through_rate": 35.0
            }
        ]
        
        # Execute
        result = await search_analytics_service.get_search_trends(
            time_range=sample_time_range
        )
        
        # Verify
        assert isinstance(result, list)
        assert len(result) == 2
        
        for trend in result:
            assert isinstance(trend, SearchTrendData)
            assert isinstance(trend.timestamp, datetime)
            assert trend.search_count > 0
            assert trend.unique_users > 0
            assert trend.avg_response_time_ms > 0
            assert trend.avg_results > 0
            assert trend.click_through_rate >= 0
    
    @pytest.mark.asyncio
    async def test_get_user_segments(
        self, 
        search_analytics_service, 
        mock_analytics_model,
        sample_time_range
    ):
        """Test user segments analysis"""
        # Setup mocks
        mock_analytics_model.get_user_segments.return_value = [
            {
                "user_id": "user1",
                "search_count": 50,
                "segment": "power_user",
                "avg_response_time_ms": 140.0,
                "total_clicks": 25
            },
            {
                "user_id": "user2",
                "search_count": 15,
                "segment": "regular_user",
                "avg_response_time_ms": 160.0,
                "total_clicks": 8
            }
        ]
        
        # Execute
        result = await search_analytics_service.get_user_segments(
            time_range=sample_time_range
        )
        
        # Verify
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["segment"] == "power_user"
        assert result[1]["segment"] == "regular_user"
    
    @pytest.mark.asyncio
    async def test_generate_analytics_report(
        self, 
        search_analytics_service, 
        mock_analytics_model,
        sample_time_range
    ):
        """Test comprehensive analytics report generation"""
        # Setup mocks for all required data
        mock_analytics_model.get_aggregated_stats.return_value = {
            "total_searches": 1000,
            "unique_queries": 500,
            "unique_users": 200,
            "unique_sessions": 800,
            "avg_response_time_ms": 150.5,
            "avg_results_per_search": 25.3,
            "avg_clicks_per_search": 2.1,
            "click_through_rate": 35.7,
            "zero_result_rate": 8.2
        }
        
        mock_analytics_model.get_top_queries.return_value = [
            {"query": "video", "count": 100}
        ]
        
        mock_analytics_model.get_top_filters.return_value = []
        
        mock_analytics_model.get_search_trends.return_value = [
            {
                "timestamp": "2024-01-15 10:00:00",
                "search_count": 10,
                "unique_users": 5,
                "avg_response_time_ms": 120.0,
                "avg_results": 25.0,
                "click_through_rate": 30.0
            }
        ]
        
        mock_analytics_model.get_performance_metrics.return_value = {
            "avg_response_time_ms": 150.5,
            "p50_response_time_ms": 120.0,
            "p95_response_time_ms": 350.0,
            "p99_response_time_ms": 500.0,
            "slowest_queries": [],
            "fastest_queries": [],
            "error_rate": 2.5,
            "timeout_rate": 0.8
        }
        
        mock_analytics_model.get_user_segments.return_value = []
        
        # Execute
        result = await search_analytics_service.generate_analytics_report(
            time_range=sample_time_range
        )
        
        # Verify
        assert isinstance(result, SearchAnalyticsReport)
        assert isinstance(result.summary, SearchAnalyticsAggregation)
        assert isinstance(result.trends, list)
        assert isinstance(result.performance, SearchPerformanceMetrics)
        assert isinstance(result.top_queries, list)
        assert isinstance(result.search_patterns, list)
        assert isinstance(result.user_segments, list)
        assert isinstance(result.generated_at, datetime)
        assert result.time_range == sample_time_range
    
    @pytest.mark.asyncio
    async def test_log_search_click_success(
        self, 
        search_analytics_service, 
        mock_analytics_model
    ):
        """Test successful search click logging"""
        # Setup mocks
        mock_analytics_model.create.return_value = "507f1f77bcf86cd799439011"
        
        # Execute
        result = await search_analytics_service.log_search_click(
            search_id="search123",
            asset_id="asset456",
            user_id="user789",
            session_id="session101"
        )
        
        # Verify
        assert result == True
        
        # Verify model call
        mock_analytics_model.create.assert_called_once()
        create_args = mock_analytics_model.create.call_args[0][0]
        assert create_args["query"] == "click:search123"
        assert create_args["search_type"] == "click"
        assert create_args["user_id"] == "user789"
        assert create_args["session_id"] == "session101"
        assert create_args["clicked_results"] == ["asset456"]
    
    @pytest.mark.asyncio
    async def test_log_search_click_failure(
        self, 
        search_analytics_service, 
        mock_analytics_model
    ):
        """Test search click logging failure"""
        # Setup mocks
        mock_analytics_model.create.side_effect = Exception("Database error")
        
        # Execute
        result = await search_analytics_service.log_search_click(
            search_id="search123",
            asset_id="asset456"
        )
        
        # Verify that failure doesn't break the service
        assert result == False
    
    @pytest.mark.asyncio
    async def test_cleanup_old_analytics_success(
        self, 
        search_analytics_service, 
        mock_analytics_model
    ):
        """Test successful analytics cleanup"""
        # Setup mocks
        mock_analytics_model.cleanup_old_analytics.return_value = 500
        
        # Execute
        result = await search_analytics_service.cleanup_old_analytics(
            older_than_days=90
        )
        
        # Verify
        assert result == 500
        
        # Verify model call
        mock_analytics_model.cleanup_old_analytics.assert_called_once_with(90)
    
    @pytest.mark.asyncio
    async def test_cleanup_old_analytics_invalid_days(
        self, 
        search_analytics_service
    ):
        """Test analytics cleanup with invalid days"""
        # Execute and verify exception
        with pytest.raises(ValidationError) as exc_info:
            await search_analytics_service.cleanup_old_analytics(
                older_than_days=0
            )
        
        assert "older_than_days must be at least 1" in str(exc_info.value)
    
    def test_extract_session_info(self, search_analytics_service):
        """Test session information extraction"""
        # Create mock request
        mock_request = Mock()
        mock_request.headers = {
            "x-session-id": "session123",
            "user-agent": "Mozilla/5.0 (Test Browser)",
            "referer": "https://example.com/search"
        }
        mock_request.client.host = "192.168.1.1"
        
        # Execute
        result = search_analytics_service.extract_session_info(mock_request)
        
        # Verify
        assert result["session_id"] == "session123"
        assert result["ip_address"] == "192.168.1.1"
        assert result["user_agent"] == "Mozilla/5.0 (Test Browser)"
        assert result["referrer"] == "https://example.com/search"
    
    def test_extract_session_info_no_session_id(self, search_analytics_service):
        """Test session info extraction when no session ID provided"""
        # Create mock request without session ID
        mock_request = Mock()
        mock_request.headers = {
            "user-agent": "Mozilla/5.0 (Test Browser)"
        }
        mock_request.client.host = "192.168.1.1"
        
        # Execute
        result = search_analytics_service.extract_session_info(mock_request)
        
        # Verify that a session ID was generated
        assert "session_id" in result
        assert result["session_id"] is not None
        assert len(result["session_id"]) > 0
        assert result["ip_address"] == "192.168.1.1"
        assert result["user_agent"] == "Mozilla/5.0 (Test Browser)"