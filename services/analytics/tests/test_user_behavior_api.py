"""
Tests for User Behavior API Endpoints

This module contains comprehensive tests for the user behavior tracking API.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from fastapi import FastAPI

from src.api.v1.user_behavior import router, BehaviorTracker
from src.models.analytics import UserBehavior, BehaviorPattern


@pytest.fixture
def app():
    """Create FastAPI app for testing."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/behavior")
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
def mock_behavior_tracker():
    """Mock behavior tracker."""
    tracker = AsyncMock(spec=BehaviorTracker)
    return tracker


@pytest.fixture
def sample_user_insights():
    """Sample user insights data."""
    return {
        "user_id": "test-user-123",
        "segment": "power_user",
        "activity_level": "high",
        "current_metrics": {
            "sessions_count": 25,
            "total_time_minutes": 480,
            "actions_count": 150,
            "assets_viewed": 30,
            "assets_uploaded": 5,
            "searches_performed": 20
        },
        "trends": {
            "sessions_trend": 5,
            "time_trend": 60,
            "activity_trend": 25
        },
        "feature_usage": {
            "search": 50,
            "upload": 15,
            "download": 25,
            "workflow": 10
        },
        "recent_activity": [
            {
                "timestamp": "2025-07-19T10:00:00Z",
                "action": "asset_upload",
                "category": "content",
                "properties": {"file_size": 1024000}
            }
        ],
        "recommendations": [
            "Try creating automated workflows for your uploads",
            "Explore search results more thoroughly",
            "Consider using keyboard shortcuts"
        ]
    }


class TestUserBehaviorAPI:
    """Test cases for user behavior API endpoints."""
    
    @pytest.mark.asyncio
    async def test_track_user_action_success(self, client, app, mock_current_user):
        """Test successful user action tracking."""
        request_data = {
            "action": "asset_upload",
            "context": {"asset_id": "test-asset-123", "file_size": 1024000},
            "session_id": "test-session-456"
        }
        
        with patch("src.api.v1.user_behavior.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.user_behavior.get_session"), \
             patch("src.api.v1.user_behavior.behavior_tracker") as mock_tracker:
            
            response = await client.post("/api/v1/behavior/track", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "accepted"
            assert data["message"] == "Action tracking queued"
    
    @pytest.mark.asyncio
    async def test_track_user_action_missing_action(self, client, app, mock_current_user):
        """Test user action tracking with missing action."""
        request_data = {
            "context": {"asset_id": "test-asset-123"}
        }
        
        with patch("src.api.v1.user_behavior.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.user_behavior.get_session"):
            
            response = await client.post("/api/v1/behavior/track", json=request_data)
            
            assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_get_user_insights_success(self, client, app, mock_current_user, sample_user_insights):
        """Test successful user insights retrieval."""
        user_id = "test-user-123"
        
        with patch("src.api.v1.user_behavior.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.user_behavior.get_session"), \
             patch("src.api.v1.user_behavior.behavior_tracker.get_user_insights", 
                   return_value=sample_user_insights):
            
            response = await client.get(f"/api/v1/behavior/insights/{user_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == user_id
            assert data["segment"] == "power_user"
            assert data["activity_level"] == "high"
            assert "current_metrics" in data
            assert "trends" in data
            assert "recommendations" in data
    
    @pytest.mark.asyncio
    async def test_get_user_insights_permission_denied(self, client, app, mock_current_user):
        """Test user insights with insufficient permissions."""
        different_user_id = "different-user-456"
        mock_current_user.has_permission.return_value = False
        
        with patch("src.api.v1.user_behavior.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.user_behavior.get_session"):
            
            response = await client.get(f"/api/v1/behavior/insights/{different_user_id}")
            
            assert response.status_code == 403
            data = response.json()
            assert data["detail"] == "Insufficient permissions"
    
    @pytest.mark.asyncio
    async def test_get_user_insights_not_found(self, client, app, mock_current_user):
        """Test user insights for non-existent user."""
        user_id = "nonexistent-user"
        error_response = {"error": "No behavior data found for user"}
        
        with patch("src.api.v1.user_behavior.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.user_behavior.get_session"), \
             patch("src.api.v1.user_behavior.behavior_tracker.get_user_insights",
                   return_value=error_response):
            
            response = await client.get(f"/api/v1/behavior/insights/{user_id}")
            
            assert response.status_code == 404
            data = response.json()
            assert data["detail"] == "No behavior data found for user"
    
    @pytest.mark.asyncio
    async def test_get_my_insights_success(self, client, app, mock_current_user, sample_user_insights):
        """Test successful current user insights retrieval."""
        with patch("src.api.v1.user_behavior.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.user_behavior.get_session"), \
             patch("src.api.v1.user_behavior.behavior_tracker.get_user_insights",
                   return_value=sample_user_insights):
            
            response = await client.get("/api/v1/behavior/my-insights")
            
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == "test-user-123"
            assert data["segment"] == "power_user"
    
    @pytest.mark.asyncio
    async def test_get_user_segmentation_success(self, client, app, mock_current_user):
        """Test successful user segmentation retrieval."""
        segments_data = {
            "power_user": ["user1", "user2"],
            "casual_user": ["user3", "user4", "user5"],
            "content_creator": ["user6"]
        }
        
        with patch("src.api.v1.user_behavior.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.user_behavior.get_session"), \
             patch("src.api.v1.user_behavior.behavior_tracker.segment_users",
                   return_value=segments_data):
            
            response = await client.get("/api/v1/behavior/segments")
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_users"] == 6
            assert "power_user" in data["segments"]
            assert len(data["segments"]["casual_user"]) == 3
            assert "segmentation_timestamp" in data
    
    @pytest.mark.asyncio
    async def test_get_user_segmentation_no_permission(self, client, app, mock_current_user):
        """Test user segmentation with no permission."""
        mock_current_user.has_permission.return_value = False
        
        with patch("src.api.v1.user_behavior.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.user_behavior.get_session"):
            
            response = await client.get("/api/v1/behavior/segments")
            
            assert response.status_code == 403
            data = response.json()
            assert data["detail"] == "Insufficient permissions"
    
    @pytest.mark.asyncio
    async def test_get_behavior_patterns_success(self, client, app, mock_current_user):
        """Test successful behavior patterns retrieval."""
        patterns_data = [
            BehaviorPattern(
                pattern_id="pattern_1",
                pattern_name="power_user",
                description="Highly engaged users",
                metrics={"avg_sessions": 25.0, "avg_time": 400.0},
                users_count=15,
                confidence=0.85
            ),
            BehaviorPattern(
                pattern_id="pattern_2",
                pattern_name="searcher",
                description="Search-focused users",
                metrics={"avg_sessions": 10.0, "avg_searches": 50.0},
                users_count=8,
                confidence=0.72
            )
        ]
        
        with patch("src.api.v1.user_behavior.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.user_behavior.get_session"), \
             patch("src.api.v1.user_behavior.behavior_tracker.analyze_user_patterns",
                   return_value=patterns_data):
            
            response = await client.get("/api/v1/behavior/patterns")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["patterns"]) == 2
            assert data["patterns"][0]["pattern_name"] == "power_user"
            assert data["patterns"][0]["users_count"] == 15
            assert data["patterns"][0]["confidence"] == 0.85
            assert "analysis_timestamp" in data
    
    @pytest.mark.asyncio
    async def test_get_engagement_metrics_success(self, client, app, mock_current_user):
        """Test successful engagement metrics retrieval."""
        metrics_data = {
            "total_active_users": 150,
            "avg_session_duration_minutes": 18.5,
            "segments_distribution": {
                "power_user": 25,
                "casual_user": 80,
                "content_creator": 45
            },
            "feature_adoption_rates": {
                "search": 85.5,
                "upload": 62.3,
                "workflow": 34.7
            },
            "retention_metrics": {
                "week_7_retention_percent": 45.2,
                "month_30_retention_percent": 28.8
            },
            "generated_at": "2025-07-19T10:00:00Z"
        }
        
        with patch("src.api.v1.user_behavior.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.user_behavior.get_session"), \
             patch("src.api.v1.user_behavior.behavior_tracker.get_engagement_metrics",
                   return_value=metrics_data):
            
            response = await client.get("/api/v1/behavior/engagement")
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_active_users"] == 150
            assert data["avg_session_duration_minutes"] == 18.5
            assert "segments_distribution" in data
            assert "feature_adoption_rates" in data
            assert "retention_metrics" in data
    
    @pytest.mark.asyncio
    async def test_get_engagement_metrics_failure(self, client, app, mock_current_user):
        """Test engagement metrics retrieval failure."""
        with patch("src.api.v1.user_behavior.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.user_behavior.get_session"), \
             patch("src.api.v1.user_behavior.behavior_tracker.get_engagement_metrics",
                   return_value=None):
            
            response = await client.get("/api/v1/behavior/engagement")
            
            assert response.status_code == 500
            data = response.json()
            assert data["detail"] == "Failed to generate engagement metrics"
    
    @pytest.mark.asyncio
    async def test_get_cohort_analysis_placeholder(self, client, app, mock_current_user):
        """Test cohort analysis placeholder endpoint."""
        with patch("src.api.v1.user_behavior.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.user_behavior.get_session"):
            
            response = await client.get("/api/v1/behavior/cohort-analysis?cohort_size=weekly&periods=8")
            
            assert response.status_code == 200
            data = response.json()
            assert data["cohort_analysis"]["cohort_size"] == "weekly"
            assert data["cohort_analysis"]["periods"] == 8
            assert "implementation in progress" in data["cohort_analysis"]["message"]
    
    @pytest.mark.asyncio
    async def test_get_funnel_analysis_placeholder(self, client, app, mock_current_user):
        """Test funnel analysis placeholder endpoint."""
        funnel_steps = ["login", "search", "view_asset", "download"]
        
        with patch("src.api.v1.user_behavior.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.user_behavior.get_session"):
            
            response = await client.get(
                f"/api/v1/behavior/funnel-analysis?"
                f"funnel_steps={funnel_steps[0]}&"
                f"funnel_steps={funnel_steps[1]}&"
                f"funnel_steps={funnel_steps[2]}&"
                f"funnel_steps={funnel_steps[3]}&"
                f"timeframe=30d"
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["funnel_analysis"]["steps"] == funnel_steps
            assert data["funnel_analysis"]["timeframe"] == "30d"
    
    @pytest.mark.asyncio
    async def test_get_feature_usage_analytics(self, client, app, mock_current_user):
        """Test feature usage analytics endpoint."""
        with patch("src.api.v1.user_behavior.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.user_behavior.get_session"):
            
            response = await client.get("/api/v1/behavior/feature-usage?timeframe=7d&segment=power_user")
            
            assert response.status_code == 200
            data = response.json()
            assert data["feature_usage"]["timeframe"] == "7d"
            assert data["feature_usage"]["segment_filter"] == "power_user"
            assert "analysis_period" in data
    
    @pytest.mark.asyncio
    async def test_trigger_user_segmentation_success(self, client, app, mock_current_user):
        """Test successful user segmentation trigger."""
        mock_current_user.has_permission = MagicMock(side_effect=lambda perm: perm == "analytics.admin")
        
        with patch("src.api.v1.user_behavior.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.user_behavior.get_session"):
            
            response = await client.post("/api/v1/behavior/segment-users")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "accepted"
            assert "segmentation analysis queued" in data["message"]
            assert "triggered_at" in data
    
    @pytest.mark.asyncio
    async def test_trigger_user_segmentation_no_permission(self, client, app, mock_current_user):
        """Test user segmentation trigger without permission."""
        mock_current_user.has_permission.return_value = False
        
        with patch("src.api.v1.user_behavior.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.user_behavior.get_session"):
            
            response = await client.post("/api/v1/behavior/segment-users")
            
            assert response.status_code == 403
            data = response.json()
            assert data["detail"] == "Insufficient permissions"
    
    @pytest.mark.asyncio
    async def test_trigger_pattern_analysis_success(self, client, app, mock_current_user):
        """Test successful pattern analysis trigger."""
        mock_current_user.has_permission = MagicMock(side_effect=lambda perm: perm == "analytics.admin")
        
        with patch("src.api.v1.user_behavior.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.user_behavior.get_session"):
            
            response = await client.post("/api/v1/behavior/analyze-patterns")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "accepted"
            assert "pattern analysis queued" in data["message"]
            assert "triggered_at" in data
    
    @pytest.mark.asyncio
    async def test_trigger_pattern_analysis_no_permission(self, client, app, mock_current_user):
        """Test pattern analysis trigger without permission."""
        mock_current_user.has_permission.return_value = False
        
        with patch("src.api.v1.user_behavior.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.user_behavior.get_session"):
            
            response = await client.post("/api/v1/behavior/analyze-patterns")
            
            assert response.status_code == 403
            data = response.json()
            assert data["detail"] == "Insufficient permissions"
    
    @pytest.mark.asyncio
    async def test_health_check(self, client, app):
        """Test behavior tracking service health check."""
        response = await client.get("/api/v1/behavior/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "user_behavior_tracking"
        assert "timestamp" in data


class TestUserBehaviorModels:
    """Test cases for user behavior request/response models."""
    
    def test_user_action_request_validation(self):
        """Test UserActionRequest model validation."""
        from src.api.v1.user_behavior import UserActionRequest
        
        # Valid request
        valid_request = UserActionRequest(
            action="asset_upload",
            context={"asset_id": "123", "file_size": 1024},
            session_id="session-456"
        )
        assert valid_request.action == "asset_upload"
        assert valid_request.context["asset_id"] == "123"
        assert valid_request.session_id == "session-456"
        
        # Request without optional fields
        minimal_request = UserActionRequest(action="search")
        assert minimal_request.action == "search"
        assert minimal_request.context == {}
        assert minimal_request.session_id is None
    
    def test_behavior_insights_response_structure(self):
        """Test BehaviorInsightsResponse model structure."""
        from src.api.v1.user_behavior import BehaviorInsightsResponse
        
        response = BehaviorInsightsResponse(
            user_id="test-user",
            segment="power_user",
            activity_level="high",
            current_metrics={"sessions": 10},
            trends={"sessions_trend": 2},
            feature_usage={"search": 5},
            recent_activity=[{"action": "login"}],
            recommendations=["Use shortcuts"]
        )
        
        assert response.user_id == "test-user"
        assert response.segment == "power_user"
        assert response.activity_level == "high"
        assert isinstance(response.current_metrics, dict)
        assert isinstance(response.trends, dict)
        assert isinstance(response.feature_usage, dict)
        assert isinstance(response.recent_activity, list)
        assert isinstance(response.recommendations, list)
    
    def test_engagement_metrics_response_structure(self):
        """Test EngagementMetricsResponse model structure."""
        from src.api.v1.user_behavior import EngagementMetricsResponse
        
        response = EngagementMetricsResponse(
            total_active_users=100,
            avg_session_duration_minutes=15.5,
            segments_distribution={"power_user": 20},
            feature_adoption_rates={"search": 85.5},
            retention_metrics={"week_7": 45.0},
            generated_at="2025-07-19T10:00:00Z"
        )
        
        assert response.total_active_users == 100
        assert response.avg_session_duration_minutes == 15.5
        assert isinstance(response.segments_distribution, dict)
        assert isinstance(response.feature_adoption_rates, dict)
        assert isinstance(response.retention_metrics, dict)
        assert response.generated_at == "2025-07-19T10:00:00Z"


@pytest.mark.asyncio
async def test_user_behavior_api_error_handling(client, app, mock_current_user):
    """Test API error handling for unexpected exceptions."""
    with patch("src.api.v1.user_behavior.get_current_user", return_value=mock_current_user), \
         patch("src.api.v1.user_behavior.get_session"), \
         patch("src.api.v1.user_behavior.behavior_tracker.get_user_insights",
               side_effect=Exception("Database connection failed")):
        
        response = await client.get("/api/v1/behavior/my-insights")
        
        # The API should handle the exception gracefully
        assert response.status_code == 404  # Returns error from tracker