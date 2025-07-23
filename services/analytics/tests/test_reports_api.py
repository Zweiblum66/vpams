"""
Tests for Custom Reports API

This module contains comprehensive tests for the custom reports API endpoints.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from fastapi import FastAPI

from src.api.v1.reports import router
from src.services.report_generator import ReportType, ReportFormat, ChartType


@pytest.fixture
def app():
    """Create FastAPI app for testing."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/reports")
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
def sample_report_request():
    """Sample report definition request."""
    return {
        "name": "Test User Activity Report",
        "description": "Test report for user activity analysis",
        "report_type": ReportType.USER_ACTIVITY,
        "data_sources": ["events", "user_sessions"],
        "filters": [
            {
                "field": "event_type",
                "operator": "eq",
                "value": "user_action"
            }
        ],
        "date_range": {
            "relative": "last_7d"
        },
        "charts": [
            {
                "chart_type": ChartType.LINE,
                "title": "Daily Active Users",
                "x_axis": "timestamp",
                "y_axis": "user_count",
                "data_source": "events",
                "filters": [],
                "group_by": "date",
                "aggregation": "count"
            },
            {
                "chart_type": ChartType.PIE,
                "title": "User Segments",
                "x_axis": "segment",
                "y_axis": "count",
                "data_source": "user_behavior",
                "filters": [],
                "group_by": "user_segment",
                "aggregation": "count"
            }
        ],
        "format": ReportFormat.JSON,
        "tags": ["test", "user_activity"],
        "is_public": False
    }


@pytest.fixture
def sample_report_definitions():
    """Sample report definitions list."""
    return [
        {
            "id": "report-1",
            "name": "User Activity Report",
            "description": "Daily user activity metrics",
            "report_type": "user_activity",
            "created_by": "test-user-123",
            "created_at": "2025-07-19T10:00:00",
            "format": "json",
            "is_public": False,
            "last_generated": None,
            "tags": ["user", "activity"]
        },
        {
            "id": "report-2",
            "name": "Asset Usage Report",
            "description": "Asset interaction analytics",
            "report_type": "asset_usage",
            "created_by": "test-user-456",
            "created_at": "2025-07-19T11:00:00",
            "format": "pdf",
            "is_public": True,
            "last_generated": "2025-07-19T12:00:00",
            "tags": ["asset", "usage"]
        }
    ]


class TestReportsAPI:
    """Test cases for reports API endpoints."""
    
    @pytest.mark.asyncio
    async def test_create_report_definition_success(self, client, app, mock_current_user, sample_report_request):
        """Test successful report definition creation."""
        with patch("src.api.v1.reports.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.reports.get_session"), \
             patch("src.api.v1.reports.report_generator.create_report_definition") as mock_create:
            
            mock_create.return_value = "new-report-id"
            
            response = await client.post("/api/v1/reports/definitions", json=sample_report_request)
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "new-report-id"
            assert data["message"] == "Report definition created successfully"
            assert "created_at" in data
            
            # Verify the service was called
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_report_definition_no_permission(self, client, app, mock_current_user, sample_report_request):
        """Test report creation without permission."""
        mock_current_user.has_permission.return_value = False
        
        with patch("src.api.v1.reports.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.reports.get_session"):
            
            response = await client.post("/api/v1/reports/definitions", json=sample_report_request)
            
            assert response.status_code == 403
            data = response.json()
            assert data["detail"] == "Insufficient permissions"
    
    @pytest.mark.asyncio
    async def test_create_report_definition_invalid_data(self, client, app, mock_current_user):
        """Test report creation with invalid data."""
        invalid_request = {
            "name": "",  # Empty name should fail validation
            "report_type": "invalid_type"
        }
        
        with patch("src.api.v1.reports.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.reports.get_session"):
            
            response = await client.post("/api/v1/reports/definitions", json=invalid_request)
            
            assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_list_report_definitions_success(self, client, app, mock_current_user, sample_report_definitions):
        """Test successful report definitions listing."""
        with patch("src.api.v1.reports.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.reports.get_session"), \
             patch("src.api.v1.reports.report_generator.list_report_definitions") as mock_list:
            
            mock_list.return_value = sample_report_definitions
            
            response = await client.get("/api/v1/reports/definitions")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["name"] == "User Activity Report"
            assert data[1]["name"] == "Asset Usage Report"
    
    @pytest.mark.asyncio
    async def test_list_report_definitions_with_filters(self, client, app, mock_current_user, sample_report_definitions):
        """Test listing with filters."""
        with patch("src.api.v1.reports.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.reports.get_session"), \
             patch("src.api.v1.reports.report_generator.list_report_definitions") as mock_list:
            
            mock_list.return_value = sample_report_definitions
            
            response = await client.get("/api/v1/reports/definitions?is_public=true&tags=asset,usage")
            
            assert response.status_code == 200
            data = response.json()
            # Should filter for public reports with asset or usage tags
            assert len(data) == 1
            assert data[0]["is_public"] is True
    
    @pytest.mark.asyncio
    async def test_list_report_definitions_no_permission(self, client, app, mock_current_user):
        """Test listing without permission."""
        mock_current_user.has_permission.return_value = False
        
        with patch("src.api.v1.reports.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.reports.get_session"):
            
            response = await client.get("/api/v1/reports/definitions")
            
            assert response.status_code == 403
            data = response.json()
            assert data["detail"] == "Insufficient permissions"
    
    @pytest.mark.asyncio
    async def test_get_report_definition_success(self, client, app, mock_current_user, sample_report_definitions):
        """Test getting a specific report definition."""
        with patch("src.api.v1.reports.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.reports.get_session"), \
             patch("src.api.v1.reports.report_generator.list_report_definitions") as mock_list:
            
            mock_list.return_value = sample_report_definitions
            
            response = await client.get("/api/v1/reports/definitions/report-1")
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "report-1"
            assert data["name"] == "User Activity Report"
    
    @pytest.mark.asyncio
    async def test_get_report_definition_not_found(self, client, app, mock_current_user):
        """Test getting non-existent report definition."""
        with patch("src.api.v1.reports.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.reports.get_session"), \
             patch("src.api.v1.reports.report_generator.list_report_definitions") as mock_list:
            
            mock_list.return_value = []
            
            response = await client.get("/api/v1/reports/definitions/nonexistent")
            
            assert response.status_code == 404
            data = response.json()
            assert data["detail"] == "Report definition not found"
    
    @pytest.mark.asyncio
    async def test_get_report_definition_access_denied(self, client, app, mock_current_user, sample_report_definitions):
        """Test access denied for private report."""
        # User trying to access someone else's private report
        mock_current_user.id = "different-user"
        mock_current_user.has_permission = MagicMock(side_effect=lambda perm: perm != "analytics.view_all_reports")
        
        with patch("src.api.v1.reports.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.reports.get_session"), \
             patch("src.api.v1.reports.report_generator.list_report_definitions") as mock_list:
            
            mock_list.return_value = sample_report_definitions
            
            response = await client.get("/api/v1/reports/definitions/report-1")
            
            assert response.status_code == 403
            data = response.json()
            assert data["detail"] == "Access denied"
    
    @pytest.mark.asyncio
    async def test_update_report_definition_success(self, client, app, mock_current_user, sample_report_request, sample_report_definitions):
        """Test successful report definition update."""
        with patch("src.api.v1.reports.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.reports.get_session"), \
             patch("src.api.v1.reports.report_generator.list_report_definitions") as mock_list, \
             patch("src.api.v1.reports.report_generator.create_report_definition") as mock_create:
            
            mock_list.return_value = sample_report_definitions
            
            response = await client.put("/api/v1/reports/definitions/report-1", json=sample_report_request)
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "report-1"
            assert data["message"] == "Report definition updated successfully"
            
            # Verify the service was called
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_report_definition_not_found(self, client, app, mock_current_user, sample_report_request):
        """Test updating non-existent report definition."""
        with patch("src.api.v1.reports.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.reports.get_session"), \
             patch("src.api.v1.reports.report_generator.list_report_definitions") as mock_list:
            
            mock_list.return_value = []
            
            response = await client.put("/api/v1/reports/definitions/nonexistent", json=sample_report_request)
            
            assert response.status_code == 404
            data = response.json()
            assert data["detail"] == "Report definition not found"
    
    @pytest.mark.asyncio
    async def test_delete_report_definition_success(self, client, app, mock_current_user, sample_report_definitions):
        """Test successful report definition deletion."""
        with patch("src.api.v1.reports.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.reports.get_session"), \
             patch("src.api.v1.reports.report_generator.list_report_definitions") as mock_list, \
             patch("src.api.v1.reports.report_generator.delete_report_definition") as mock_delete:
            
            mock_list.return_value = sample_report_definitions
            mock_delete.return_value = True
            
            response = await client.delete("/api/v1/reports/definitions/report-1")
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Report definition deleted successfully"
            assert "deleted_at" in data
            
            # Verify the service was called
            mock_delete.assert_called_once_with("report-1")
    
    @pytest.mark.asyncio
    async def test_delete_report_definition_failed(self, client, app, mock_current_user, sample_report_definitions):
        """Test failed report definition deletion."""
        with patch("src.api.v1.reports.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.reports.get_session"), \
             patch("src.api.v1.reports.report_generator.list_report_definitions") as mock_list, \
             patch("src.api.v1.reports.report_generator.delete_report_definition") as mock_delete:
            
            mock_list.return_value = sample_report_definitions
            mock_delete.return_value = False
            
            response = await client.delete("/api/v1/reports/definitions/report-1")
            
            assert response.status_code == 500
            data = response.json()
            assert data["detail"] == "Failed to delete report definition"
    
    @pytest.mark.asyncio
    async def test_generate_report_success(self, client, app, mock_current_user, sample_report_definitions):
        """Test successful report generation."""
        generation_request = {
            "definition_id": "report-1",
            "custom_filters": [
                {
                    "field": "user_id",
                    "operator": "eq",
                    "value": "specific-user"
                }
            ]
        }
        
        mock_report = {
            "report_id": "report-1",
            "name": "User Activity Report",
            "data": {"events": []},
            "charts": [],
            "generated_at": "2025-07-19T10:00:00"
        }
        
        with patch("src.api.v1.reports.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.reports.get_session"), \
             patch("src.api.v1.reports.report_generator.list_report_definitions") as mock_list, \
             patch("src.api.v1.reports.report_generator.generate_report") as mock_generate:
            
            mock_list.return_value = sample_report_definitions
            mock_generate.return_value = mock_report
            
            response = await client.post("/api/v1/reports/generate", json=generation_request)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert "generated_at" in data
            assert "report" in data
            assert data["report"]["name"] == "User Activity Report"
            
            # Verify the service was called with custom filters
            mock_generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_report_not_found(self, client, app, mock_current_user):
        """Test generating report with non-existent definition."""
        generation_request = {
            "definition_id": "nonexistent",
            "custom_filters": []
        }
        
        with patch("src.api.v1.reports.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.reports.get_session"), \
             patch("src.api.v1.reports.report_generator.list_report_definitions") as mock_list:
            
            mock_list.return_value = []
            
            response = await client.post("/api/v1/reports/generate", json=generation_request)
            
            assert response.status_code == 404
            data = response.json()
            assert data["detail"] == "Report definition not found"
    
    @pytest.mark.asyncio
    async def test_generate_report_access_denied(self, client, app, mock_current_user, sample_report_definitions):
        """Test access denied for private report generation."""
        mock_current_user.id = "different-user"
        mock_current_user.has_permission = MagicMock(side_effect=lambda perm: perm not in ["analytics.view_all_reports"])
        
        generation_request = {
            "definition_id": "report-1",
            "custom_filters": []
        }
        
        with patch("src.api.v1.reports.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.reports.get_session"), \
             patch("src.api.v1.reports.report_generator.list_report_definitions") as mock_list:
            
            mock_list.return_value = sample_report_definitions
            
            response = await client.post("/api/v1/reports/generate", json=generation_request)
            
            assert response.status_code == 403
            data = response.json()
            assert data["detail"] == "Access denied"
    
    @pytest.mark.asyncio
    async def test_generate_report_async_success(self, client, app, mock_current_user, sample_report_definitions):
        """Test successful asynchronous report generation."""
        with patch("src.api.v1.reports.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.reports.get_session"), \
             patch("src.api.v1.reports.report_generator.list_report_definitions") as mock_list:
            
            mock_list.return_value = sample_report_definitions
            
            response = await client.post("/api/v1/reports/generate-async/report-1")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "queued"
            assert data["message"] == "Report generation started in background"
            assert "queued_at" in data
    
    @pytest.mark.asyncio
    async def test_get_report_result_success(self, client, app, mock_current_user):
        """Test getting async report result."""
        mock_report = {
            "report_id": "report-1",
            "data": {"events": []},
            "charts": []
        }
        
        with patch("src.api.v1.reports.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.reports.get_session"), \
             patch("src.api.v1.reports.report_generator._get_redis") as mock_redis_getter:
            
            mock_redis = AsyncMock()
            mock_redis_getter.return_value = mock_redis
            mock_redis.get.return_value = json.dumps(mock_report)
            
            response = await client.get("/api/v1/reports/result/report-1")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert "report" in data
    
    @pytest.mark.asyncio
    async def test_get_report_result_not_found(self, client, app, mock_current_user):
        """Test getting non-existent report result."""
        with patch("src.api.v1.reports.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.reports.get_session"), \
             patch("src.api.v1.reports.report_generator._get_redis") as mock_redis_getter:
            
            mock_redis = AsyncMock()
            mock_redis_getter.return_value = mock_redis
            mock_redis.get.return_value = None
            
            response = await client.get("/api/v1/reports/result/report-1")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "not_found"
            assert "No report result found" in data["message"]
    
    @pytest.mark.asyncio
    async def test_get_report_result_error(self, client, app, mock_current_user):
        """Test getting report result with error."""
        error_result = {"error": "Database connection failed"}
        
        with patch("src.api.v1.reports.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.reports.get_session"), \
             patch("src.api.v1.reports.report_generator._get_redis") as mock_redis_getter:
            
            mock_redis = AsyncMock()
            mock_redis_getter.return_value = mock_redis
            mock_redis.get.return_value = json.dumps(error_result)
            
            response = await client.get("/api/v1/reports/result/report-1")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert data["error"] == "Database connection failed"
    
    @pytest.mark.asyncio
    async def test_get_report_templates(self, client, app, mock_current_user):
        """Test getting report templates."""
        with patch("src.api.v1.reports.get_current_user", return_value=mock_current_user):
            
            response = await client.get("/api/v1/reports/templates")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 3  # user_activity_summary, asset_usage_report, search_analytics
            assert all("id" in template for template in data)
            assert all("name" in template for template in data)
            assert all("description" in template for template in data)
    
    @pytest.mark.asyncio
    async def test_get_available_data_sources(self, client, app, mock_current_user):
        """Test getting available data sources."""
        with patch("src.api.v1.reports.get_current_user", return_value=mock_current_user):
            
            response = await client.get("/api/v1/reports/data-sources")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 5  # events, user_sessions, asset_interactions, search_queries, user_behavior
            
            # Check structure
            for source in data:
                assert "name" in source
                assert "description" in source
                assert "fields" in source
                assert isinstance(source["fields"], list)
            
            # Check specific sources
            events_source = next(s for s in data if s["name"] == "events")
            assert "event_type" in events_source["fields"]
            assert "timestamp" in events_source["fields"]
    
    @pytest.mark.asyncio
    async def test_health_check(self, client, app):
        """Test reports service health check."""
        response = await client.get("/api/v1/reports/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "custom_reports"
        assert "timestamp" in data


class TestReportModels:
    """Test cases for request/response models."""
    
    def test_report_filter_request_validation(self):
        """Test ReportFilterRequest model validation."""
        from src.api.v1.reports import ReportFilterRequest
        
        # Valid filter
        valid_filter = ReportFilterRequest(
            field="user_id",
            operator="eq",
            value="test-user-123"
        )
        assert valid_filter.field == "user_id"
        assert valid_filter.operator == "eq"
        assert valid_filter.value == "test-user-123"
    
    def test_chart_config_request_validation(self):
        """Test ChartConfigRequest model validation."""
        from src.api.v1.reports import ChartConfigRequest
        
        # Valid chart config
        valid_config = ChartConfigRequest(
            chart_type=ChartType.BAR,
            title="Test Chart",
            x_axis="category",
            y_axis="count",
            data_source="events",
            filters=[],
            group_by="event_type",
            aggregation="count",
            limit=10,
            sort_order="desc"
        )
        
        assert valid_config.chart_type == ChartType.BAR
        assert valid_config.title == "Test Chart"
        assert valid_config.limit == 10
        assert valid_config.sort_order == "desc"
    
    def test_report_definition_request_validation(self):
        """Test ReportDefinitionRequest model validation."""
        from src.api.v1.reports import ReportDefinitionRequest
        
        # Valid definition
        valid_definition = ReportDefinitionRequest(
            name="Test Report",
            description="Test description",
            report_type=ReportType.USER_ACTIVITY,
            data_sources=["events"],
            filters=[],
            date_range={"relative": "last_7d"},
            charts=[],
            format=ReportFormat.JSON,
            tags=["test"],
            is_public=False
        )
        
        assert valid_definition.name == "Test Report"
        assert valid_definition.report_type == ReportType.USER_ACTIVITY
        assert valid_definition.format == ReportFormat.JSON
        assert valid_definition.is_public is False
    
    def test_report_generation_request_validation(self):
        """Test ReportGenerationRequest model validation."""
        from src.api.v1.reports import ReportGenerationRequest
        
        # Valid generation request
        valid_request = ReportGenerationRequest(
            definition_id="report-123",
            custom_filters=[],
            override_format=ReportFormat.PDF
        )
        
        assert valid_request.definition_id == "report-123"
        assert valid_request.override_format == ReportFormat.PDF


@pytest.mark.asyncio
async def test_reports_api_error_handling(client, app, mock_current_user):
    """Test API error handling for unexpected exceptions."""
    with patch("src.api.v1.reports.get_current_user", return_value=mock_current_user), \
         patch("src.api.v1.reports.get_session"), \
         patch("src.api.v1.reports.report_generator.list_report_definitions",
               side_effect=Exception("Database connection failed")):
        
        response = await client.get("/api/v1/reports/definitions")
        
        # The API should handle the exception gracefully
        assert response.status_code == 500
        data = response.json()
        assert "Failed to list report definitions" in data["detail"]