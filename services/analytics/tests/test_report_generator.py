"""
Tests for Custom Report Generator Service

This module contains comprehensive tests for the report generation functionality.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.report_generator import (
    ReportGenerator, ReportDefinition, ReportType, ReportFormat,
    ChartType, ChartConfig, ReportFilter
)


@pytest.fixture
def report_generator():
    """Create a report generator instance for testing."""
    return ReportGenerator()


@pytest.fixture
async def mock_db():
    """Create a mock database session."""
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    return db


@pytest.fixture
def sample_report_definition():
    """Create a sample report definition."""
    return ReportDefinition(
        id="test-report-123",
        name="Test Report",
        description="Test report for unit testing",
        report_type=ReportType.USER_ACTIVITY,
        created_by="test-user-456",
        created_at=datetime.utcnow(),
        data_sources=["events", "user_sessions"],
        filters=[
            ReportFilter(field="event_type", operator="eq", value="user_action")
        ],
        date_range={"relative": "last_7d"},
        charts=[
            ChartConfig(
                chart_type=ChartType.LINE,
                title="Daily User Activity",
                x_axis="timestamp",
                y_axis="user_count",
                data_source="events",
                filters=[],
                group_by="date",
                aggregation="count"
            )
        ],
        format=ReportFormat.JSON,
        tags=["test", "user_activity"],
        is_public=False
    )


class TestReportFilter:
    """Test cases for ReportFilter class."""
    
    def test_report_filter_creation(self):
        """Test ReportFilter creation."""
        filter_obj = ReportFilter(
            field="user_id",
            operator="eq",
            value="test-user-123"
        )
        
        assert filter_obj.field == "user_id"
        assert filter_obj.operator == "eq"
        assert filter_obj.value == "test-user-123"
    
    def test_to_sql_condition_eq(self):
        """Test SQL condition generation for equality."""
        filter_obj = ReportFilter(field="status", operator="eq", value="active")
        mock_column = MagicMock()
        
        condition = filter_obj.to_sql_condition(mock_column)
        mock_column.__eq__.assert_called_once_with("active")
    
    def test_to_sql_condition_in(self):
        """Test SQL condition generation for 'in' operator."""
        filter_obj = ReportFilter(field="type", operator="in", value=["video", "image"])
        mock_column = MagicMock()
        
        condition = filter_obj.to_sql_condition(mock_column)
        mock_column.in_.assert_called_once_with(["video", "image"])
    
    def test_to_sql_condition_contains(self):
        """Test SQL condition generation for 'contains' operator."""
        filter_obj = ReportFilter(field="description", operator="contains", value="test")
        mock_column = MagicMock()
        
        condition = filter_obj.to_sql_condition(mock_column)
        mock_column.contains.assert_called_once_with("test")
    
    def test_to_sql_condition_unsupported_operator(self):
        """Test error handling for unsupported operators."""
        filter_obj = ReportFilter(field="field", operator="unsupported", value="value")
        mock_column = MagicMock()
        
        with pytest.raises(ValueError, match="Unsupported operator"):
            filter_obj.to_sql_condition(mock_column)


class TestChartConfig:
    """Test cases for ChartConfig class."""
    
    def test_chart_config_creation(self):
        """Test ChartConfig creation."""
        config = ChartConfig(
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
        
        assert config.chart_type == ChartType.BAR
        assert config.title == "Test Chart"
        assert config.x_axis == "category"
        assert config.y_axis == "count"
        assert config.data_source == "events"
        assert config.group_by == "event_type"
        assert config.aggregation == "count"
        assert config.limit == 10
        assert config.sort_order == "desc"


class TestReportDefinition:
    """Test cases for ReportDefinition class."""
    
    def test_report_definition_creation(self, sample_report_definition):
        """Test ReportDefinition creation."""
        definition = sample_report_definition
        
        assert definition.id == "test-report-123"
        assert definition.name == "Test Report"
        assert definition.report_type == ReportType.USER_ACTIVITY
        assert definition.created_by == "test-user-456"
        assert len(definition.data_sources) == 2
        assert len(definition.filters) == 1
        assert len(definition.charts) == 1
        assert definition.format == ReportFormat.JSON
        assert definition.is_public is False


class TestReportGenerator:
    """Test cases for ReportGenerator class."""
    
    @pytest.mark.asyncio
    async def test_create_report_definition(self, report_generator, mock_db, sample_report_definition):
        """Test creating a report definition."""
        with patch.object(report_generator, '_get_redis') as mock_redis_getter:
            mock_redis = AsyncMock()
            mock_redis_getter.return_value = mock_redis
            
            definition_id = await report_generator.create_report_definition(
                sample_report_definition, mock_db
            )
            
            assert definition_id == sample_report_definition.id
            mock_redis.hset.assert_called_once()
            mock_redis.expire.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_parse_date_range_relative(self, report_generator):
        """Test parsing relative date ranges."""
        date_range = {"relative": "last_7d"}
        start_date, end_date = report_generator._parse_date_range(date_range)
        
        assert isinstance(start_date, datetime)
        assert isinstance(end_date, datetime)
        assert end_date > start_date
        assert (end_date - start_date).days == 7
    
    @pytest.mark.asyncio
    async def test_parse_date_range_absolute(self, report_generator):
        """Test parsing absolute date ranges."""
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        
        date_range = {
            "start": week_ago.isoformat(),
            "end": now.isoformat()
        }
        
        start_date, end_date = report_generator._parse_date_range(date_range)
        
        assert start_date.date() == week_ago.date()
        assert end_date.date() == now.date()
    
    @pytest.mark.asyncio
    async def test_parse_date_range_default(self, report_generator):
        """Test parsing with default date range."""
        date_range = {}
        start_date, end_date = report_generator._parse_date_range(date_range)
        
        assert isinstance(start_date, datetime)
        assert isinstance(end_date, datetime)
        assert (end_date - start_date).days == 7
    
    @pytest.mark.asyncio
    async def test_collect_events_data(self, report_generator, mock_db):
        """Test collecting events data."""
        # Mock database result
        mock_events = [
            MagicMock(
                id="event-1",
                event_type="user_action",
                event_name="login",
                category="auth",
                user_id="user-123",
                timestamp=datetime.utcnow(),
                properties={"source": "web"},
                duration_ms=100
            )
        ]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_events
        mock_db.execute.return_value = mock_result
        
        filters = [ReportFilter(field="event_type", operator="eq", value="user_action")]
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()
        
        events_data = await report_generator._collect_events_data(
            filters, start_date, end_date, mock_db
        )
        
        assert len(events_data) == 1
        assert events_data[0]["event_name"] == "login"
        assert events_data[0]["category"] == "auth"
        assert events_data[0]["properties"] == {"source": "web"}
    
    @pytest.mark.asyncio
    async def test_collect_sessions_data(self, report_generator, mock_db):
        """Test collecting user sessions data."""
        # Mock database result
        mock_sessions = [
            MagicMock(
                id="session-1",
                user_id="user-123",
                session_id="sess-456",
                started_at=datetime.utcnow(),
                ended_at=datetime.utcnow() + timedelta(minutes=30),
                duration_seconds=1800,
                device_type="desktop",
                browser="Chrome",
                os="Windows",
                page_views=10,
                actions_count=5,
                country="US"
            )
        ]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_sessions
        mock_db.execute.return_value = mock_result
        
        filters = []
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()
        
        sessions_data = await report_generator._collect_sessions_data(
            filters, start_date, end_date, mock_db
        )
        
        assert len(sessions_data) == 1
        assert sessions_data[0]["device_type"] == "desktop"
        assert sessions_data[0]["browser"] == "Chrome"
        assert sessions_data[0]["page_views"] == 10
    
    @pytest.mark.asyncio
    async def test_generate_line_chart(self, report_generator):
        """Test generating line chart data."""
        import pandas as pd
        
        config = ChartConfig(
            chart_type=ChartType.LINE,
            title="Daily Users",
            x_axis="date",
            y_axis="user_count",
            data_source="events",
            filters=[],
            group_by="date",
            aggregation="count"
        )
        
        # Sample DataFrame
        df = pd.DataFrame({
            "date": ["2025-01-01", "2025-01-02", "2025-01-03"],
            "user_count": [10, 15, 12]
        })
        
        chart_data = await report_generator._generate_line_chart(config, df)
        
        assert chart_data["title"] == "Daily Users"
        assert chart_data["type"] == ChartType.LINE
        assert chart_data["data"]["labels"] == ["2025-01-01", "2025-01-02", "2025-01-03"]
        assert chart_data["data"]["values"] == [10, 15, 12]
    
    @pytest.mark.asyncio
    async def test_generate_line_chart_missing_columns(self, report_generator):
        """Test line chart generation with missing columns."""
        import pandas as pd
        
        config = ChartConfig(
            chart_type=ChartType.LINE,
            title="Test Chart",
            x_axis="missing_column",
            y_axis="user_count",
            data_source="events",
            filters=[]
        )
        
        df = pd.DataFrame({"user_count": [10, 15, 12]})
        
        chart_data = await report_generator._generate_line_chart(config, df)
        
        assert chart_data["data"] is None
        assert "Required columns not found" in chart_data["error"]
    
    @pytest.mark.asyncio
    async def test_generate_pie_chart(self, report_generator):
        """Test generating pie chart data."""
        import pandas as pd
        
        config = ChartConfig(
            chart_type=ChartType.PIE,
            title="User Segments",
            x_axis="",
            y_axis="",
            data_source="user_behavior",
            filters=[],
            group_by="user_segment",
            aggregation="count"
        )
        
        # Sample DataFrame
        df = pd.DataFrame({
            "user_segment": ["power_user", "casual_user", "power_user", "new_user"]
        })
        
        chart_data = await report_generator._generate_pie_chart(config, df)
        
        assert chart_data["title"] == "User Segments"
        assert chart_data["type"] == ChartType.PIE
        assert len(chart_data["data"]["labels"]) == 3  # power_user, casual_user, new_user
        assert chart_data["data"]["values"][0] == 2  # power_user appears twice
    
    @pytest.mark.asyncio
    async def test_generate_table_chart(self, report_generator):
        """Test generating table chart data."""
        import pandas as pd
        
        config = ChartConfig(
            chart_type=ChartType.TABLE,
            title="Top Users",
            x_axis="user_id",
            y_axis="action_count",
            data_source="events",
            filters=[],
            group_by="user_id",
            aggregation="count",
            limit=5,
            sort_order="desc"
        )
        
        # Sample DataFrame
        df = pd.DataFrame({
            "user_id": ["user1", "user2", "user1", "user3"],
            "action": ["login", "upload", "download", "search"]
        })
        
        chart_data = await report_generator._generate_table_chart(config, df)
        
        assert chart_data["title"] == "Top Users"
        assert chart_data["type"] == ChartType.TABLE
        assert "columns" in chart_data["data"]
        assert "rows" in chart_data["data"]
    
    @pytest.mark.asyncio
    async def test_apply_dataframe_filter(self, report_generator):
        """Test applying filters to DataFrame."""
        import pandas as pd
        
        df = pd.DataFrame({
            "status": ["active", "inactive", "active"],
            "count": [10, 5, 15]
        })
        
        # Test equality filter
        filter_obj = ReportFilter(field="status", operator="eq", value="active")
        filtered_df = report_generator._apply_dataframe_filter(df, filter_obj)
        assert len(filtered_df) == 2
        assert all(filtered_df["status"] == "active")
        
        # Test greater than filter
        filter_obj = ReportFilter(field="count", operator="gt", value=8)
        filtered_df = report_generator._apply_dataframe_filter(df, filter_obj)
        assert len(filtered_df) == 2
        assert all(filtered_df["count"] > 8)
        
        # Test 'in' filter
        filter_obj = ReportFilter(field="status", operator="in", value=["active"])
        filtered_df = report_generator._apply_dataframe_filter(df, filter_obj)
        assert len(filtered_df) == 2
    
    @pytest.mark.asyncio
    async def test_format_csv_report(self, report_generator):
        """Test formatting report as CSV."""
        report_data = {
            "events": [
                {"event_name": "login", "user_id": "user1", "timestamp": "2025-01-01T10:00:00"},
                {"event_name": "upload", "user_id": "user2", "timestamp": "2025-01-01T10:30:00"}
            ]
        }
        
        charts_data = [
            {
                "title": "Test Chart",
                "type": "line",
                "data": {"labels": ["A", "B"], "values": [1, 2]}
            }
        ]
        
        formatted = await report_generator._format_csv_report(report_data, charts_data)
        
        assert formatted["format"] == "csv"
        assert "events.csv" in formatted["files"]
        assert "charts_summary.csv" in formatted["files"]
        assert "event_name,user_id,timestamp" in formatted["files"]["events.csv"]
    
    @pytest.mark.asyncio
    async def test_format_html_report(self, report_generator, sample_report_definition):
        """Test formatting report as HTML."""
        report_data = {"events": []}
        charts_data = []
        
        formatted = await report_generator._format_html_report(
            sample_report_definition, report_data, charts_data
        )
        
        assert formatted["format"] == "html"
        assert "Test Report" in formatted["content"]
        assert "Generated:" in formatted["content"]
    
    @pytest.mark.asyncio
    async def test_list_report_definitions(self, report_generator):
        """Test listing report definitions."""
        with patch.object(report_generator, '_get_redis') as mock_redis_getter:
            mock_redis = AsyncMock()
            mock_redis_getter.return_value = mock_redis
            
            # Mock Redis response
            definition_data = {
                "report-1": json.dumps({
                    "id": "report-1",
                    "name": "Test Report 1",
                    "description": "First test report",
                    "report_type": "user_activity",
                    "created_by": "user-123",
                    "created_at": "2025-01-01T10:00:00",
                    "format": "json",
                    "is_public": True,
                    "tags": ["test"]
                }),
                "report-2": json.dumps({
                    "id": "report-2",
                    "name": "Test Report 2",
                    "description": "Second test report",
                    "report_type": "asset_usage",
                    "created_by": "user-456",
                    "created_at": "2025-01-02T10:00:00",
                    "format": "pdf",
                    "is_public": False,
                    "tags": ["asset"]
                })
            }
            
            mock_redis.hgetall.return_value = definition_data
            
            # Test listing all definitions
            definitions = await report_generator.list_report_definitions()
            assert len(definitions) == 2
            assert definitions[0]["name"] == "Test Report 2"  # Sorted by created_at desc
            assert definitions[1]["name"] == "Test Report 1"
            
            # Test filtering by creator
            definitions = await report_generator.list_report_definitions(created_by="user-123")
            assert len(definitions) == 1
            assert definitions[0]["name"] == "Test Report 1"
            
            # Test filtering by public status
            definitions = await report_generator.list_report_definitions(is_public=True)
            assert len(definitions) == 1
            assert definitions[0]["name"] == "Test Report 1"
    
    @pytest.mark.asyncio
    async def test_delete_report_definition(self, report_generator):
        """Test deleting a report definition."""
        with patch.object(report_generator, '_get_redis') as mock_redis_getter:
            mock_redis = AsyncMock()
            mock_redis_getter.return_value = mock_redis
            
            # Test successful deletion
            mock_redis.hdel.return_value = 1
            result = await report_generator.delete_report_definition("report-123")
            assert result is True
            mock_redis.hdel.assert_called_once_with("report_definitions", "report-123")
            
            # Test deletion of non-existent definition
            mock_redis.hdel.return_value = 0
            result = await report_generator.delete_report_definition("nonexistent")
            assert result is False
    
    @pytest.mark.asyncio
    async def test_reconstruct_definition(self, report_generator):
        """Test reconstructing ReportDefinition from dictionary."""
        definition_dict = {
            "id": "report-123",
            "name": "Test Report",
            "description": "Test description",
            "report_type": "user_activity",
            "created_by": "user-456",
            "created_at": "2025-01-01T10:00:00",
            "data_sources": ["events"],
            "filters": [
                {"field": "event_type", "operator": "eq", "value": "user_action"}
            ],
            "date_range": {"relative": "last_7d"},
            "charts": [
                {
                    "chart_type": "line",
                    "title": "Test Chart",
                    "x_axis": "date",
                    "y_axis": "count",
                    "data_source": "events",
                    "filters": []
                }
            ],
            "format": "json",
            "schedule": None,
            "recipients": None,
            "tags": ["test"],
            "is_public": False
        }
        
        definition = report_generator._reconstruct_definition(definition_dict)
        
        assert definition.id == "report-123"
        assert definition.name == "Test Report"
        assert definition.report_type == ReportType.USER_ACTIVITY
        assert len(definition.filters) == 1
        assert definition.filters[0].field == "event_type"
        assert len(definition.charts) == 1
        assert definition.charts[0].chart_type == ChartType.LINE


@pytest.mark.asyncio
async def test_report_generator_error_handling(report_generator, mock_db):
    """Test error handling in report generator."""
    with patch.object(report_generator, '_get_redis', side_effect=Exception("Redis connection failed")):
        sample_definition = ReportDefinition(
            id="test-report",
            name="Test",
            description="Test",
            report_type=ReportType.USER_ACTIVITY,
            created_by="user-123",
            created_at=datetime.utcnow(),
            data_sources=["events"],
            filters=[],
            date_range={"relative": "last_7d"},
            charts=[],
            format=ReportFormat.JSON
        )
        
        with pytest.raises(Exception):
            await report_generator.create_report_definition(sample_definition, mock_db)


@pytest.mark.asyncio
async def test_report_generator_cleanup():
    """Test report generator cleanup."""
    generator = ReportGenerator()
    mock_redis = AsyncMock()
    generator.redis_client = mock_redis
    
    await generator.close()
    mock_redis.close.assert_awaited_once()