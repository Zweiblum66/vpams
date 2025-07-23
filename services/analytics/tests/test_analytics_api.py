"""
Tests for Unified Analytics API

This module contains comprehensive tests for the unified analytics API endpoints.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from fastapi import FastAPI

from src.api.v1.analytics import router
from src.models.analytics import EventType


@pytest.fixture
def app():
    """Create FastAPI app for testing."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/analytics")
    return app


@pytest.fixture
async def client(app):
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_current_user():
    """Mock current user."""
    user = MagicMock()
    user.id = "test-user-123"
    user.has_permission = MagicMock(return_value=True)
    return user


@pytest.fixture
def sample_overview_data():
    """Sample analytics overview data."""
    return {
        "total_events": 15420,
        "unique_users": 1250,
        "active_sessions": 320,
        "top_events": [
            {"event_name": "page_view", "count": 8500, "percentage": 55.1},
            {"event_name": "asset_upload", "count": 2300, "percentage": 14.9}
        ],
        "bounce_rate": 0.123,
        "conversion_rate": 0.047,
        "avg_session_duration": 18.5,
        "page_views": 18500
    }


@pytest.fixture
def sample_engagement_data():
    """Sample engagement metrics data."""
    return {
        "total_active_users": 150,
        "avg_session_duration_minutes": 18.5,
        "segments_distribution": {
            "power_user": 25,
            "casual_user": 80,
            "new_user": 45
        },
        "feature_adoption_rates": {
            "search": 85.5,
            "upload": 62.3,
            "workflow": 34.7
        },
        "retention_metrics": {
            "week_7_retention_percent": 45.2,
            "month_30_retention_percent": 28.8
        }
    }


class TestAnalyticsAPI:
    """Test cases for unified analytics API endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_analytics_overview_success(self, client, app, mock_current_user, sample_overview_data, sample_engagement_data):
        """Test successful analytics overview retrieval."""
        with patch("src.api.v1.analytics.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.analytics.get_session"), \
             patch("src.api.v1.analytics.analytics_engine.get_overview_metrics") as mock_overview, \
             patch("src.api.v1.analytics.behavior_tracker.segment_users") as mock_segments, \
             patch("src.api.v1.analytics.behavior_tracker.get_engagement_metrics") as mock_engagement:
            
            mock_overview.return_value = sample_overview_data
            mock_segments.return_value = {
                "power_user": ["user1", "user2"],
                "casual_user": ["user3", "user4", "user5"]
            }
            mock_engagement.return_value = sample_engagement_data
            
            response = await client.get("/api/v1/analytics/overview?timeframe=24h")
            
            assert response.status_code == 200
            data = response.json()
            assert data["timeframe"] == "24h"
            assert data["total_events"] == 15420
            assert data["unique_users"] == 1250
            assert data["active_sessions"] == 320
            assert len(data["top_events"]) == 2
            assert "user_segments" in data
            assert "key_metrics" in data
            assert "trends" in data
            assert "generated_at" in data
    
    @pytest.mark.asyncio
    async def test_get_analytics_overview_invalid_timeframe(self, client, app, mock_current_user):
        """Test analytics overview with invalid timeframe."""
        with patch("src.api.v1.analytics.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.analytics.get_session"):
            
            response = await client.get("/api/v1/analytics/overview?timeframe=invalid")
            
            assert response.status_code == 400
            data = response.json()
            assert data["detail"] == "Invalid timeframe"
    
    @pytest.mark.asyncio
    async def test_get_analytics_overview_no_permission(self, client, app, mock_current_user):
        """Test analytics overview without permission."""
        mock_current_user.has_permission.return_value = False
        
        with patch("src.api.v1.analytics.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.analytics.get_session"):
            
            response = await client.get("/api/v1/analytics/overview")
            
            assert response.status_code == 403
            data = response.json()
            assert data["detail"] == "Insufficient permissions"
    
    @pytest.mark.asyncio
    async def test_track_event_success(self, client, app, mock_current_user):
        """Test successful event tracking."""
        event_data = {
            "event_type": EventType.USER_ACTION,
            "event_name": "asset_upload",
            "category": "content",
            "properties": {
                "asset_id": "asset-123",
                "file_size": 1024000
            },
            "session_id": "sess-456",
            "duration_ms": 1500
        }
        
        with patch("src.api.v1.analytics.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.analytics.get_session"):
            
            response = await client.post("/api/v1/analytics/events/track", json=event_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "accepted"
            assert data["message"] == "Event tracking queued"
            assert "timestamp" in data
    
    @pytest.mark.asyncio
    async def test_track_event_invalid_data(self, client, app, mock_current_user):
        """Test event tracking with invalid data."""
        invalid_event_data = {
            "event_type": "invalid_type",
            "event_name": ""  # Empty name should fail validation
        }
        
        with patch("src.api.v1.analytics.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.analytics.get_session"):
            
            response = await client.post("/api/v1/analytics/events/track", json=invalid_event_data)
            
            assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_track_events_batch_success(self, client, app, mock_current_user):
        """Test successful batch event tracking."""
        events_data = [
            {
                "event_type": EventType.PAGE_VIEW,
                "event_name": "dashboard",
                "category": "navigation",
                "properties": {"page": "/dashboard"}
            },
            {
                "event_type": EventType.USER_ACTION,
                "event_name": "search",
                "category": "search",
                "properties": {"query": "video files"}
            }
        ]
        
        with patch("src.api.v1.analytics.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.analytics.get_session"):
            
            response = await client.post("/api/v1/analytics/events/batch", json=events_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "accepted"
            assert "Batch of 2 events queued" in data["message"]
            assert "timestamp" in data
    
    @pytest.mark.asyncio
    async def test_track_events_batch_too_large(self, client, app, mock_current_user):
        """Test batch event tracking with too many events."""
        # Create a batch of 101 events (exceeds limit of 100)
        events_data = [
            {
                "event_type": EventType.PAGE_VIEW,
                "event_name": f"page_{i}",
                "category": "navigation"
            }
            for i in range(101)
        ]
        
        with patch("src.api.v1.analytics.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.analytics.get_session"):
            
            response = await client.post("/api/v1/analytics/events/batch", json=events_data)
            
            assert response.status_code == 400
            data = response.json()
            assert "Maximum 100 events per batch" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_query_metrics_success(self, client, app, mock_current_user):
        """Test successful metrics query."""
        query_data = {
            "metric_names": ["page_views", "user_sessions"],
            "start_date": "2025-07-12T00:00:00Z",
            "end_date": "2025-07-19T00:00:00Z",
            "granularity": "day",
            "group_by": ["date"],
            "filters": {"user_segment": ["power_user"]}
        }
        
        mock_metrics_data = [
            {
                "metric_name": "page_views",
                "data": [
                    {
                        "timestamp": "2025-07-19T00:00:00Z",
                        "value": 1250,
                        "dimensions": {"date": "2025-07-19"}
                    }
                ]
            }
        ]
        
        with patch("src.api.v1.analytics.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.analytics.get_session"), \
             patch("src.api.v1.analytics.analytics_engine.query_metrics") as mock_query:
            
            mock_query.return_value = mock_metrics_data
            
            response = await client.post("/api/v1/analytics/metrics/query", json=query_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "metrics" in data
            assert "query_parameters" in data
            assert "generated_at" in data
            assert data["query_parameters"]["metric_names"] == ["page_views", "user_sessions"]
    
    @pytest.mark.asyncio
    async def test_get_available_metrics(self, client, app, mock_current_user):
        """Test getting available metrics."""
        with patch("src.api.v1.analytics.get_current_user", return_value=mock_current_user):
            
            response = await client.get("/api/v1/analytics/metrics/available")
            
            assert response.status_code == 200
            data = response.json()
            assert "metrics" in data
            assert len(data["metrics"]) > 0
            
            # Check structure of first metric
            first_metric = data["metrics"][0]
            assert "name" in first_metric
            assert "description" in first_metric
            assert "type" in first_metric
            assert "dimensions" in first_metric
    
    @pytest.mark.asyncio
    async def test_get_trends_success(self, client, app, mock_current_user):
        """Test successful trends retrieval."""
        mock_trend_data = [
            {"timestamp": "2025-07-19T09:00:00Z", "value": 125},
            {"timestamp": "2025-07-19T10:00:00Z", "value": 142}
        ]
        
        with patch("src.api.v1.analytics.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.analytics.get_session"), \
             patch("src.api.v1.analytics.analytics_engine.get_trend_data") as mock_trends:
            
            mock_trends.return_value = mock_trend_data
            
            response = await client.get("/api/v1/analytics/trends?metric=page_views&timeframe=7d&comparison=true")
            
            assert response.status_code == 200
            data = response.json()
            assert data["metric"] == "page_views"
            assert data["timeframe"] == "7d"
            assert "data" in data
            assert "comparison" in data
            assert "generated_at" in data
    
    @pytest.mark.asyncio
    async def test_get_executive_dashboard_success(self, client, app, mock_current_user, sample_overview_data, sample_engagement_data):
        """Test successful executive dashboard retrieval."""
        mock_current_user.has_permission = MagicMock(side_effect=lambda perm: perm == "analytics.view_executive")
        
        with patch("src.api.v1.analytics.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.analytics.get_session"), \
             patch("src.api.v1.analytics.analytics_engine.get_overview_metrics") as mock_overview, \
             patch("src.api.v1.analytics.behavior_tracker.get_engagement_metrics") as mock_engagement, \
             patch("src.api.v1.analytics.behavior_tracker.segment_users") as mock_segments:
            
            mock_overview.return_value = sample_overview_data
            mock_engagement.return_value = sample_engagement_data
            mock_segments.return_value = {
                "power_user": ["user1", "user2"],
                "casual_user": ["user3", "user4"]
            }
            
            response = await client.get("/api/v1/analytics/dashboards/executive?period=30d")
            
            assert response.status_code == 200
            data = response.json()
            assert data["period"] == "30d"
            assert "kpis" in data
            assert "user_distribution" in data
            assert "trends" in data
            assert "generated_at" in data
            
            # Check KPIs structure
            kpis = data["kpis"]
            assert "total_users" in kpis
            assert "active_users" in kpis
            assert "retention_rate" in kpis
            assert "feature_adoption" in kpis
    
    @pytest.mark.asyncio
    async def test_get_executive_dashboard_no_permission(self, client, app, mock_current_user):
        """Test executive dashboard without permission."""
        mock_current_user.has_permission.return_value = False
        
        with patch("src.api.v1.analytics.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.analytics.get_session"):
            
            response = await client.get("/api/v1/analytics/dashboards/executive")
            
            assert response.status_code == 403
            data = response.json()
            assert data["detail"] == "Insufficient permissions"
    
    @pytest.mark.asyncio
    async def test_get_operational_dashboard_success(self, client, app, mock_current_user, sample_overview_data):
        """Test successful operational dashboard retrieval."""
        with patch("src.api.v1.analytics.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.analytics.get_session"), \
             patch("src.api.v1.analytics.analytics_engine.get_overview_metrics") as mock_overview:
            
            mock_overview.return_value = sample_overview_data
            
            response = await client.get("/api/v1/analytics/dashboards/operational?timeframe=24h")
            
            assert response.status_code == 200
            data = response.json()
            assert data["timeframe"] == "24h"
            assert "system_health" in data
            assert "traffic_metrics" in data
            assert "user_activity" in data
            assert "alerts" in data
            assert "generated_at" in data
            
            # Check system health structure
            system_health = data["system_health"]
            assert "api_response_time_ms" in system_health
            assert "error_rate_percent" in system_health
            assert "cpu_usage_percent" in system_health
    
    @pytest.mark.asyncio
    async def test_export_analytics_data_success(self, client, app, mock_current_user):
        """Test successful analytics data export."""
        mock_current_user.has_permission = MagicMock(side_effect=lambda perm: perm == "analytics.export")
        
        mock_export_data = {
            "export_id": "exp_123456",
            "download_url": "https://api.example.com/exports/exp_123456/download",
            "expires_at": "2025-07-20T10:00:00Z"
        }
        
        with patch("src.api.v1.analytics.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.analytics.get_session"), \
             patch("src.api.v1.analytics.analytics_engine.export_data") as mock_export:
            
            mock_export.return_value = mock_export_data
            
            response = await client.get("/api/v1/analytics/export?format=csv&data_types=events&data_types=sessions")
            
            assert response.status_code == 200
            data = response.json()
            assert data["export_id"] == "exp_123456"
            assert data["format"] == "csv"
            assert "events" in data["data_types"]
            assert "sessions" in data["data_types"]
            assert "download_url" in data
            assert "expires_at" in data
            assert "generated_at" in data
    
    @pytest.mark.asyncio
    async def test_export_analytics_data_date_range_too_large(self, client, app, mock_current_user):
        """Test export with date range too large."""
        mock_current_user.has_permission = MagicMock(side_effect=lambda perm: perm == "analytics.export")
        
        # Date range of more than 365 days
        start_date = "2023-01-01T00:00:00Z"
        end_date = "2025-01-01T00:00:00Z"
        
        with patch("src.api.v1.analytics.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.analytics.get_session"):
            
            response = await client.get(f"/api/v1/analytics/export?start_date={start_date}&end_date={end_date}")
            
            assert response.status_code == 400
            data = response.json()
            assert "Date range cannot exceed 365 days" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_health_check(self, client, app):
        """Test analytics API health check."""
        response = await client.get("/api/v1/analytics/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "unified_analytics_api"
        assert data["version"] == "1.0.0"
        assert "timestamp" in data
        assert "components" in data
        
        # Check components
        components = data["components"]
        assert "analytics_engine" in components
        assert "behavior_tracker" in components
        assert "report_generator" in components
    
    @pytest.mark.asyncio
    async def test_get_service_status_success(self, client, app, mock_current_user):
        """Test service status retrieval."""
        mock_current_user.has_permission = MagicMock(side_effect=lambda perm: perm == "analytics.admin")
        
        mock_stats = {
            "uptime_minutes": 1440,
            "total_events": 50000,
            "events_24h": 1500,
            "active_users": 250,
            "reports_count": 15,
            "storage_mb": 1024,
            "avg_query_time": 45,
            "cache_hit_rate": 0.85,
            "queue_size": 10
        }
        
        with patch("src.api.v1.analytics.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.analytics.get_session"), \
             patch("src.api.v1.analytics.analytics_engine.get_service_statistics") as mock_get_stats:
            
            mock_get_stats.return_value = mock_stats
            
            response = await client.get("/api/v1/analytics/status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "analytics"
            assert data["status"] == "operational"
            assert "statistics" in data
            assert "performance" in data
            assert "last_updated" in data
            
            # Check statistics
            stats = data["statistics"]
            assert stats["total_events_processed"] == 50000
            assert stats["events_last_24h"] == 1500
            assert stats["active_users_count"] == 250
    
    @pytest.mark.asyncio
    async def test_get_service_status_no_permission(self, client, app, mock_current_user):
        """Test service status without admin permission."""
        mock_current_user.has_permission.return_value = False
        
        with patch("src.api.v1.analytics.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.analytics.get_session"):
            
            response = await client.get("/api/v1/analytics/status")
            
            assert response.status_code == 403
            data = response.json()
            assert data["detail"] == "Insufficient permissions"
    
    @pytest.mark.asyncio
    async def test_get_api_schema(self, client, app):
        """Test API schema retrieval."""
        response = await client.get("/api/v1/analytics/schema")
        
        assert response.status_code == 200
        data = response.json()
        assert data["api_version"] == "1.0.0"
        assert data["title"] == "MAMS Analytics API"
        assert "endpoints" in data
        assert "event_types" in data
        assert "available_timeframes" in data
        assert "supported_formats" in data
        assert "rate_limits" in data
        
        # Check endpoints structure
        endpoints = data["endpoints"]
        assert "overview" in endpoints
        assert "track_event" in endpoints
        assert "query_metrics" in endpoints
        
        # Check event types
        event_types = data["event_types"]
        assert "page_view" in event_types
        assert "user_action" in event_types
        
        # Check timeframes
        timeframes = data["available_timeframes"]
        assert "1h" in timeframes
        assert "24h" in timeframes
        assert "7d" in timeframes


class TestAnalyticsModels:
    """Test cases for analytics request/response models."""
    
    def test_event_tracking_request_validation(self):
        """Test EventTrackingRequest model validation."""
        from src.api.v1.analytics import EventTrackingRequest
        
        # Valid request
        valid_request = EventTrackingRequest(
            event_type=EventType.USER_ACTION,
            event_name="asset_upload",
            category="content",
            properties={"asset_id": "123"},
            session_id="sess-456",
            duration_ms=1500
        )
        
        assert valid_request.event_type == EventType.USER_ACTION
        assert valid_request.event_name == "asset_upload"
        assert valid_request.category == "content"
        assert valid_request.properties == {"asset_id": "123"}
        assert valid_request.session_id == "sess-456"
        assert valid_request.duration_ms == 1500
    
    def test_metrics_query_validation(self):
        """Test MetricsQuery model validation."""
        from src.api.v1.analytics import MetricsQuery
        
        # Valid query
        valid_query = MetricsQuery(
            metric_names=["page_views", "user_sessions"],
            start_date="2025-07-12T00:00:00Z",
            end_date="2025-07-19T00:00:00Z",
            granularity="day",
            group_by=["date", "user_segment"],
            filters={"user_segment": ["power_user"]}
        )
        
        assert valid_query.metric_names == ["page_views", "user_sessions"]
        assert valid_query.start_date == "2025-07-12T00:00:00Z"
        assert valid_query.granularity == "day"
        assert valid_query.group_by == ["date", "user_segment"]
        assert valid_query.filters == {"user_segment": ["power_user"]}
    
    def test_analytics_overview_response_structure(self):
        """Test AnalyticsOverviewResponse model structure."""
        from src.api.v1.analytics import AnalyticsOverviewResponse
        
        response = AnalyticsOverviewResponse(
            timeframe="24h",
            total_events=15420,
            unique_users=1250,
            active_sessions=320,
            top_events=[{"event_name": "page_view", "count": 8500}],
            user_segments={"power_user": 25},
            key_metrics={"avg_session_duration_minutes": 18.5},
            trends={"total_events_change_percent": 15.2},
            generated_at="2025-07-19T10:00:00Z"
        )
        
        assert response.timeframe == "24h"
        assert response.total_events == 15420
        assert response.unique_users == 1250
        assert response.active_sessions == 320
        assert isinstance(response.top_events, list)
        assert isinstance(response.user_segments, dict)
        assert isinstance(response.key_metrics, dict)
        assert isinstance(response.trends, dict)


@pytest.mark.asyncio
async def test_analytics_api_error_handling(client, app, mock_current_user):
    """Test API error handling for unexpected exceptions."""
    with patch("src.api.v1.analytics.get_current_user", return_value=mock_current_user), \
         patch("src.api.v1.analytics.get_session"), \
         patch("src.api.v1.analytics.analytics_engine.get_overview_metrics",
               side_effect=Exception("Database connection failed")):
        
        response = await client.get("/api/v1/analytics/overview")
        
        # The API should handle the exception gracefully
        assert response.status_code == 500
        data = response.json()
        assert "Failed to get analytics overview" in data["detail"]