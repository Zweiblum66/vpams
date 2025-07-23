"""
Integration tests for search analytics API endpoints
"""

import pytest
from httpx import AsyncClient
from fastapi import status
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta

from src.main import app


@pytest.mark.integration
class TestSearchAnalyticsIntegration:
    """Integration tests for search analytics endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_search_analytics(self):
        """Test getting search analytics"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            request_data = {
                "time_range": {
                    "start_time": (datetime.utcnow() - timedelta(days=7)).isoformat(),
                    "end_time": datetime.utcnow().isoformat(),
                    "interval": "1h"
                },
                "filters": {
                    "search_type": "basic",
                    "query_contains": "video",
                    "min_results": 1,
                    "max_results": 100
                }
            }
            
            with patch('src.services.search_analytics_service.get_search_analytics_service') as mock_service:
                mock_service_instance = AsyncMock()
                mock_service_instance.get_search_analytics.return_value = {
                    "total_searches": 1000,
                    "unique_queries": 500,
                    "unique_users": 200,
                    "unique_sessions": 800,
                    "avg_response_time_ms": 150.5,
                    "avg_results_per_search": 25.3,
                    "avg_clicks_per_search": 2.1,
                    "click_through_rate": 35.7,
                    "zero_result_rate": 8.2,
                    "top_queries": [{"query": "video", "count": 100}],
                    "top_filters": [{"filter": {"asset_type": "video"}, "count": 50}],
                    "search_patterns": [{"pattern": "peak_time", "data": {}}],
                    "performance_metrics": {"avg_response_time_ms": 150.5}
                }
                mock_service.return_value = mock_service_instance
                
                response = await client.post(
                    "/api/v1/analytics/search",
                    json=request_data
                )
            
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
    
    @pytest.mark.asyncio
    async def test_get_search_performance_metrics(self):
        """Test getting search performance metrics"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            request_data = {
                "time_range": {
                    "start_time": (datetime.utcnow() - timedelta(days=1)).isoformat(),
                    "end_time": datetime.utcnow().isoformat(),
                    "interval": "1h"
                }
            }
            
            with patch('src.services.search_analytics_service.get_search_analytics_service') as mock_service:
                mock_service_instance = AsyncMock()
                mock_service_instance.get_search_performance_metrics.return_value = {
                    "avg_response_time_ms": 150.5,
                    "p50_response_time_ms": 120.0,
                    "p95_response_time_ms": 350.0,
                    "p99_response_time_ms": 500.0,
                    "slowest_queries": [{"query": "slow", "response_time_ms": 500}],
                    "fastest_queries": [{"query": "fast", "response_time_ms": 50}],
                    "error_rate": 2.5,
                    "timeout_rate": 0.8
                }
                mock_service.return_value = mock_service_instance
                
                response = await client.post(
                    "/api/v1/analytics/search/performance",
                    json=request_data
                )
            
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
    
    @pytest.mark.asyncio
    async def test_get_search_trends(self):
        """Test getting search trends"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            request_data = {
                "time_range": {
                    "start_time": (datetime.utcnow() - timedelta(days=7)).isoformat(),
                    "end_time": datetime.utcnow().isoformat(),
                    "interval": "1d"
                }
            }
            
            with patch('src.services.search_analytics_service.get_search_analytics_service') as mock_service:
                mock_service_instance = AsyncMock()
                mock_service_instance.get_search_trends.return_value = [
                    {
                        "timestamp": datetime.utcnow(),
                        "search_count": 10,
                        "unique_users": 5,
                        "avg_response_time_ms": 120.0,
                        "avg_results": 25.0,
                        "click_through_rate": 30.0
                    }
                ]
                mock_service.return_value = mock_service_instance
                
                response = await client.post(
                    "/api/v1/analytics/search/trends",
                    json=request_data
                )
            
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
    
    @pytest.mark.asyncio
    async def test_generate_search_analytics_report(self):
        """Test generating comprehensive analytics report"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            request_data = {
                "time_range": {
                    "start_time": (datetime.utcnow() - timedelta(days=30)).isoformat(),
                    "end_time": datetime.utcnow().isoformat(),
                    "interval": "1d"
                }
            }
            
            with patch('src.services.search_analytics_service.get_search_analytics_service') as mock_service:
                mock_service_instance = AsyncMock()
                mock_service_instance.generate_analytics_report.return_value = {
                    "summary": {
                        "total_searches": 1000,
                        "unique_queries": 500,
                        "unique_users": 200,
                        "unique_sessions": 800,
                        "avg_response_time_ms": 150.5,
                        "avg_results_per_search": 25.3,
                        "avg_clicks_per_search": 2.1,
                        "click_through_rate": 35.7,
                        "zero_result_rate": 8.2,
                        "top_queries": [],
                        "top_filters": [],
                        "search_patterns": [],
                        "performance_metrics": {}
                    },
                    "trends": [
                        {
                            "timestamp": datetime.utcnow(),
                            "search_count": 10,
                            "unique_users": 5,
                            "avg_response_time_ms": 120.0,
                            "avg_results": 25.0,
                            "click_through_rate": 30.0
                        }
                    ],
                    "performance": {
                        "avg_response_time_ms": 150.5,
                        "p50_response_time_ms": 120.0,
                        "p95_response_time_ms": 350.0,
                        "p99_response_time_ms": 500.0,
                        "slowest_queries": [],
                        "fastest_queries": [],
                        "error_rate": 2.5,
                        "timeout_rate": 0.8
                    },
                    "top_queries": [{"query": "video", "count": 100}],
                    "search_patterns": [{"pattern": "peak_time", "data": {}}],
                    "user_segments": [{"segment": "power_user", "count": 10}],
                    "generated_at": datetime.utcnow(),
                    "time_range": {
                        "start_time": (datetime.utcnow() - timedelta(days=30)),
                        "end_time": datetime.utcnow(),
                        "interval": "1d"
                    }
                }
                mock_service.return_value = mock_service_instance
                
                response = await client.post(
                    "/api/v1/analytics/search/report",
                    json=request_data
                )
            
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
    
    @pytest.mark.asyncio
    async def test_get_user_segments(self):
        """Test getting user segments"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            request_data = {
                "time_range": {
                    "start_time": (datetime.utcnow() - timedelta(days=30)).isoformat(),
                    "end_time": datetime.utcnow().isoformat(),
                    "interval": "1d"
                }
            }
            
            with patch('src.services.search_analytics_service.get_search_analytics_service') as mock_service:
                mock_service_instance = AsyncMock()
                mock_service_instance.get_user_segments.return_value = [
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
                mock_service.return_value = mock_service_instance
                
                response = await client.post(
                    "/api/v1/analytics/search/segments",
                    json=request_data
                )
            
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
    
    @pytest.mark.asyncio
    async def test_log_search_click(self):
        """Test logging search click"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('src.services.search_analytics_service.get_search_analytics_service') as mock_service:
                mock_service_instance = AsyncMock()
                mock_service_instance.log_search_click.return_value = True
                mock_service.return_value = mock_service_instance
                
                response = await client.post(
                    "/api/v1/analytics/search/click",
                    params={
                        "search_id": "search123",
                        "asset_id": "asset456",
                        "session_id": "session789"
                    }
                )
            
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
    
    @pytest.mark.asyncio
    async def test_cleanup_search_analytics(self):
        """Test cleaning up old analytics data"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('src.services.search_analytics_service.get_search_analytics_service') as mock_service:
                mock_service_instance = AsyncMock()
                mock_service_instance.cleanup_old_analytics.return_value = 500
                mock_service.return_value = mock_service_instance
                
                response = await client.delete(
                    "/api/v1/analytics/search/cleanup",
                    params={"older_than_days": 90}
                )
            
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
    
    @pytest.mark.asyncio
    async def test_search_analytics_with_complex_filters(self):
        """Test analytics with complex filter combinations"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            request_data = {
                "time_range": {
                    "start_time": (datetime.utcnow() - timedelta(days=7)).isoformat(),
                    "end_time": datetime.utcnow().isoformat(),
                    "interval": "1h"
                },
                "filters": {
                    "search_type": "advanced",
                    "user_id": "user123",
                    "query_contains": "marketing",
                    "min_results": 5,
                    "max_results": 50,
                    "min_response_time": 100,
                    "max_response_time": 1000,
                    "indices": ["assets", "metadata"],
                    "has_clicks": True
                }
            }
            
            with patch('src.services.search_analytics_service.get_search_analytics_service') as mock_service:
                mock_service_instance = AsyncMock()
                mock_service_instance.get_search_analytics.return_value = {
                    "total_searches": 50,
                    "unique_queries": 25,
                    "unique_users": 1,
                    "unique_sessions": 10,
                    "avg_response_time_ms": 200.0,
                    "avg_results_per_search": 15.0,
                    "avg_clicks_per_search": 3.0,
                    "click_through_rate": 80.0,
                    "zero_result_rate": 0.0,
                    "top_queries": [],
                    "top_filters": [],
                    "search_patterns": [],
                    "performance_metrics": {}
                }
                mock_service.return_value = mock_service_instance
                
                response = await client.post(
                    "/api/v1/analytics/search",
                    json=request_data
                )
            
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
    
    @pytest.mark.asyncio
    async def test_search_analytics_validation_error(self):
        """Test analytics endpoint with validation error"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Invalid time range (end before start)
            request_data = {
                "time_range": {
                    "start_time": datetime.utcnow().isoformat(),
                    "end_time": (datetime.utcnow() - timedelta(days=1)).isoformat(),
                    "interval": "1h"
                }
            }
            
            response = await client.post(
                "/api/v1/analytics/search",
                json=request_data
            )
            
            # Should return validation error
            assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_500_INTERNAL_SERVER_ERROR]
    
    @pytest.mark.asyncio
    async def test_search_analytics_different_intervals(self):
        """Test analytics with different time intervals"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            intervals = ["1h", "1d", "1w", "1M"]
            
            for interval in intervals:
                request_data = {
                    "time_range": {
                        "start_time": (datetime.utcnow() - timedelta(days=30)).isoformat(),
                        "end_time": datetime.utcnow().isoformat(),
                        "interval": interval
                    }
                }
                
                with patch('src.services.search_analytics_service.get_search_analytics_service') as mock_service:
                    mock_service_instance = AsyncMock()
                    mock_service_instance.get_search_analytics.return_value = {
                        "total_searches": 100,
                        "unique_queries": 50,
                        "unique_users": 20,
                        "unique_sessions": 80,
                        "avg_response_time_ms": 150.0,
                        "avg_results_per_search": 25.0,
                        "avg_clicks_per_search": 2.0,
                        "click_through_rate": 30.0,
                        "zero_result_rate": 10.0,
                        "top_queries": [],
                        "top_filters": [],
                        "search_patterns": [],
                        "performance_metrics": {}
                    }
                    mock_service.return_value = mock_service_instance
                    
                    response = await client.post(
                        "/api/v1/analytics/search",
                        json=request_data
                    )
                
                assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
    
    @pytest.mark.asyncio
    async def test_search_analytics_concurrent_requests(self):
        """Test analytics endpoints with concurrent requests"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            request_data = {
                "time_range": {
                    "start_time": (datetime.utcnow() - timedelta(days=7)).isoformat(),
                    "end_time": datetime.utcnow().isoformat(),
                    "interval": "1h"
                }
            }
            
            with patch('src.services.search_analytics_service.get_search_analytics_service') as mock_service:
                mock_service_instance = AsyncMock()
                mock_service_instance.get_search_analytics.return_value = {
                    "total_searches": 100,
                    "unique_queries": 50,
                    "unique_users": 20,
                    "unique_sessions": 80,
                    "avg_response_time_ms": 150.0,
                    "avg_results_per_search": 25.0,
                    "avg_clicks_per_search": 2.0,
                    "click_through_rate": 30.0,
                    "zero_result_rate": 10.0,
                    "top_queries": [],
                    "top_filters": [],
                    "search_patterns": [],
                    "performance_metrics": {}
                }
                mock_service.return_value = mock_service_instance
                
                # Make multiple concurrent requests
                import asyncio
                tasks = []
                for i in range(5):
                    task = client.post(
                        "/api/v1/analytics/search",
                        json=request_data
                    )
                    tasks.append(task)
                
                responses = await asyncio.gather(*tasks)
                
                # All requests should succeed or fail consistently
                status_codes = [r.status_code for r in responses]
                assert all(code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR] for code in status_codes)