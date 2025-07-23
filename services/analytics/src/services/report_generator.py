"""
Custom Report Generator Service

This service provides functionality to create, manage, and generate custom analytics reports
with various data sources, filters, and output formats.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import asyncio
import csv
import io
import base64

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, text
import redis.asyncio as redis
import jinja2
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import pandas as pd

from ..models.analytics import (
    Event, UserSession, AssetInteraction, SearchQuery, UserBehavior,
    UsageMetrics
)
from ..core.config import settings
from shared.tracing.python_tracing import trace_async_function
from shared.logging.python_logging import get_logger

logger = get_logger(__name__)


class ReportFormat(str, Enum):
    """Supported report output formats."""
    PDF = "pdf"
    CSV = "csv"
    JSON = "json"
    EXCEL = "excel"
    HTML = "html"


class ReportType(str, Enum):
    """Types of reports that can be generated."""
    USER_ACTIVITY = "user_activity"
    ASSET_USAGE = "asset_usage"
    SEARCH_ANALYTICS = "search_analytics"
    WORKFLOW_PERFORMANCE = "workflow_performance"
    STORAGE_UTILIZATION = "storage_utilization"
    CUSTOM_DASHBOARD = "custom_dashboard"
    ENGAGEMENT_SUMMARY = "engagement_summary"
    RETENTION_ANALYSIS = "retention_analysis"


class ChartType(str, Enum):
    """Chart types for visualizations."""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    AREA = "area"
    SCATTER = "scatter"
    HEATMAP = "heatmap"
    TABLE = "table"


@dataclass
class ReportFilter:
    """Report filter specification."""
    field: str
    operator: str  # eq, ne, gt, lt, gte, lte, in, not_in, contains
    value: Union[str, int, float, List[Any]]
    
    def to_sql_condition(self, column):
        """Convert filter to SQLAlchemy condition."""
        if self.operator == "eq":
            return column == self.value
        elif self.operator == "ne":
            return column != self.value
        elif self.operator == "gt":
            return column > self.value
        elif self.operator == "lt":
            return column < self.value
        elif self.operator == "gte":
            return column >= self.value
        elif self.operator == "lte":
            return column <= self.value
        elif self.operator == "in":
            return column.in_(self.value)
        elif self.operator == "not_in":
            return ~column.in_(self.value)
        elif self.operator == "contains":
            return column.contains(self.value)
        else:
            raise ValueError(f"Unsupported operator: {self.operator}")


@dataclass
class ChartConfig:
    """Chart configuration for report visualizations."""
    chart_type: ChartType
    title: str
    x_axis: str
    y_axis: str
    data_source: str
    filters: List[ReportFilter]
    group_by: Optional[str] = None
    aggregation: Optional[str] = None  # count, sum, avg, max, min
    limit: Optional[int] = None
    sort_order: Optional[str] = None  # asc, desc


@dataclass
class ReportDefinition:
    """Custom report definition."""
    id: str
    name: str
    description: str
    report_type: ReportType
    created_by: str
    created_at: datetime
    
    # Data configuration
    data_sources: List[str]
    filters: List[ReportFilter]
    date_range: Dict[str, Any]
    
    # Visualization configuration
    charts: List[ChartConfig]
    
    # Output configuration
    format: ReportFormat
    schedule: Optional[Dict[str, Any]] = None  # For scheduled reports
    recipients: Optional[List[str]] = None
    
    # Metadata
    tags: List[str] = None
    is_public: bool = False
    last_generated: Optional[datetime] = None


class ReportGenerator:
    """Service for generating custom analytics reports."""
    
    def __init__(self):
        self.redis_client = None
        self.report_cache = {}
        self.template_env = jinja2.Environment(
            loader=jinja2.DictLoader({
                'html_report': self._get_html_template()
            })
        )
        
        # Set up matplotlib style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
    
    async def _get_redis(self) -> redis.Redis:
        """Get Redis connection."""
        if not self.redis_client:
            self.redis_client = redis.from_url(settings.REDIS_URL)
        return self.redis_client
    
    @trace_async_function(operation_name="report.create_report_definition")
    async def create_report_definition(
        self,
        definition: ReportDefinition,
        db: AsyncSession
    ) -> str:
        """Create a new report definition."""
        try:
            # Store report definition in cache
            redis_client = await self._get_redis()
            definition_data = {
                "id": definition.id,
                "name": definition.name,
                "description": definition.description,
                "report_type": definition.report_type,
                "created_by": definition.created_by,
                "created_at": definition.created_at.isoformat(),
                "data_sources": definition.data_sources,
                "filters": [
                    {
                        "field": f.field,
                        "operator": f.operator,
                        "value": f.value
                    }
                    for f in definition.filters
                ],
                "date_range": definition.date_range,
                "charts": [
                    {
                        "chart_type": c.chart_type,
                        "title": c.title,
                        "x_axis": c.x_axis,
                        "y_axis": c.y_axis,
                        "data_source": c.data_source,
                        "filters": [
                            {
                                "field": f.field,
                                "operator": f.operator,
                                "value": f.value
                            }
                            for f in c.filters
                        ],
                        "group_by": c.group_by,
                        "aggregation": c.aggregation,
                        "limit": c.limit,
                        "sort_order": c.sort_order
                    }
                    for c in definition.charts
                ],
                "format": definition.format,
                "schedule": definition.schedule,
                "recipients": definition.recipients,
                "tags": definition.tags or [],
                "is_public": definition.is_public
            }
            
            await redis_client.hset(
                "report_definitions",
                definition.id,
                json.dumps(definition_data, default=str)
            )
            
            # Set expiration for cleanup
            await redis_client.expire(f"report_definitions", 86400 * 30)  # 30 days
            
            logger.info(f"Created report definition: {definition.id}")
            return definition.id
            
        except Exception as e:
            logger.error(f"Failed to create report definition: {e}", exc_info=True)
            raise
    
    @trace_async_function(operation_name="report.generate_report")
    async def generate_report(
        self,
        definition_id: str,
        db: AsyncSession,
        custom_filters: Optional[List[ReportFilter]] = None
    ) -> Dict[str, Any]:
        """Generate a report based on definition."""
        try:
            # Get report definition
            redis_client = await self._get_redis()
            definition_data = await redis_client.hget("report_definitions", definition_id)
            
            if not definition_data:
                raise ValueError(f"Report definition not found: {definition_id}")
            
            definition_dict = json.loads(definition_data)
            
            # Reconstruct definition object
            definition = self._reconstruct_definition(definition_dict)
            
            # Apply custom filters if provided
            if custom_filters:
                definition.filters.extend(custom_filters)
            
            # Generate report data
            report_data = await self._collect_report_data(definition, db)
            
            # Generate charts
            charts_data = await self._generate_charts(definition, report_data)
            
            # Format output
            formatted_report = await self._format_report(
                definition, report_data, charts_data
            )
            
            # Update last generated timestamp
            definition_dict["last_generated"] = datetime.utcnow().isoformat()
            await redis_client.hset(
                "report_definitions",
                definition_id,
                json.dumps(definition_dict, default=str)
            )
            
            logger.info(f"Generated report: {definition_id}")
            return formatted_report
            
        except Exception as e:
            logger.error(f"Failed to generate report: {e}", exc_info=True)
            raise
    
    async def _collect_report_data(
        self,
        definition: ReportDefinition,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Collect data for report generation."""
        data = {}
        
        # Parse date range
        start_date, end_date = self._parse_date_range(definition.date_range)
        
        # Collect data from each source
        for source in definition.data_sources:
            if source == "events":
                data["events"] = await self._collect_events_data(
                    definition.filters, start_date, end_date, db
                )
            elif source == "user_sessions":
                data["user_sessions"] = await self._collect_sessions_data(
                    definition.filters, start_date, end_date, db
                )
            elif source == "asset_interactions":
                data["asset_interactions"] = await self._collect_interactions_data(
                    definition.filters, start_date, end_date, db
                )
            elif source == "search_queries":
                data["search_queries"] = await self._collect_search_data(
                    definition.filters, start_date, end_date, db
                )
            elif source == "user_behavior":
                data["user_behavior"] = await self._collect_behavior_data(
                    definition.filters, start_date, end_date, db
                )
        
        return data
    
    async def _collect_events_data(
        self,
        filters: List[ReportFilter],
        start_date: datetime,
        end_date: datetime,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Collect events data."""
        query = select(Event).where(
            and_(
                Event.timestamp >= start_date,
                Event.timestamp <= end_date
            )
        )
        
        # Apply filters
        for filter_obj in filters:
            if hasattr(Event, filter_obj.field):
                column = getattr(Event, filter_obj.field)
                query = query.where(filter_obj.to_sql_condition(column))
        
        result = await db.execute(query.order_by(desc(Event.timestamp)))
        events = result.scalars().all()
        
        return [
            {
                "id": str(event.id),
                "event_type": event.event_type,
                "event_name": event.event_name,
                "category": event.category,
                "user_id": str(event.user_id) if event.user_id else None,
                "timestamp": event.timestamp.isoformat(),
                "properties": event.properties or {},
                "duration_ms": event.duration_ms
            }
            for event in events
        ]
    
    async def _collect_sessions_data(
        self,
        filters: List[ReportFilter],
        start_date: datetime,
        end_date: datetime,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Collect user sessions data."""
        query = select(UserSession).where(
            and_(
                UserSession.started_at >= start_date,
                UserSession.started_at <= end_date
            )
        )
        
        # Apply filters
        for filter_obj in filters:
            if hasattr(UserSession, filter_obj.field):
                column = getattr(UserSession, filter_obj.field)
                query = query.where(filter_obj.to_sql_condition(column))
        
        result = await db.execute(query.order_by(desc(UserSession.started_at)))
        sessions = result.scalars().all()
        
        return [
            {
                "id": str(session.id),
                "user_id": str(session.user_id),
                "session_id": session.session_id,
                "started_at": session.started_at.isoformat(),
                "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                "duration_seconds": session.duration_seconds,
                "device_type": session.device_type,
                "browser": session.browser,
                "os": session.os,
                "page_views": session.page_views,
                "actions_count": session.actions_count,
                "country": session.country
            }
            for session in sessions
        ]
    
    async def _collect_interactions_data(
        self,
        filters: List[ReportFilter],
        start_date: datetime,
        end_date: datetime,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Collect asset interactions data."""
        query = select(AssetInteraction).where(
            and_(
                AssetInteraction.timestamp >= start_date,
                AssetInteraction.timestamp <= end_date
            )
        )
        
        # Apply filters
        for filter_obj in filters:
            if hasattr(AssetInteraction, filter_obj.field):
                column = getattr(AssetInteraction, filter_obj.field)
                query = query.where(filter_obj.to_sql_condition(column))
        
        result = await db.execute(query.order_by(desc(AssetInteraction.timestamp)))
        interactions = result.scalars().all()
        
        return [
            {
                "id": str(interaction.id),
                "asset_id": str(interaction.asset_id),
                "user_id": str(interaction.user_id),
                "interaction_type": interaction.interaction_type,
                "timestamp": interaction.timestamp.isoformat(),
                "duration_seconds": interaction.duration_seconds,
                "asset_type": interaction.asset_type,
                "asset_size_bytes": interaction.asset_size_bytes,
                "project_id": str(interaction.project_id) if interaction.project_id else None
            }
            for interaction in interactions
        ]
    
    async def _collect_search_data(
        self,
        filters: List[ReportFilter],
        start_date: datetime,
        end_date: datetime,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Collect search queries data."""
        query = select(SearchQuery).where(
            and_(
                SearchQuery.timestamp >= start_date,
                SearchQuery.timestamp <= end_date
            )
        )
        
        # Apply filters
        for filter_obj in filters:
            if hasattr(SearchQuery, filter_obj.field):
                column = getattr(SearchQuery, filter_obj.field)
                query = query.where(filter_obj.to_sql_condition(column))
        
        result = await db.execute(query.order_by(desc(SearchQuery.timestamp)))
        queries = result.scalars().all()
        
        return [
            {
                "id": str(query.id),
                "user_id": str(query.user_id) if query.user_id else None,
                "query_text": query.query_text,
                "query_type": query.query_type,
                "timestamp": query.timestamp.isoformat(),
                "results_count": query.results_count,
                "response_time_ms": query.response_time_ms,
                "search_context": query.search_context
            }
            for query in queries
        ]
    
    async def _collect_behavior_data(
        self,
        filters: List[ReportFilter],
        start_date: datetime,
        end_date: datetime,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Collect user behavior data."""
        query = select(UserBehavior).where(
            and_(
                UserBehavior.period_start >= start_date,
                UserBehavior.period_end <= end_date
            )
        )
        
        # Apply filters
        for filter_obj in filters:
            if hasattr(UserBehavior, filter_obj.field):
                column = getattr(UserBehavior, filter_obj.field)
                query = query.where(filter_obj.to_sql_condition(column))
        
        result = await db.execute(query.order_by(desc(UserBehavior.period_start)))
        behaviors = result.scalars().all()
        
        return [
            {
                "id": str(behavior.id),
                "user_id": str(behavior.user_id),
                "period_start": behavior.period_start.isoformat(),
                "period_end": behavior.period_end.isoformat(),
                "period_type": behavior.period_type,
                "sessions_count": behavior.sessions_count,
                "total_time_minutes": behavior.total_time_minutes,
                "page_views": behavior.page_views,
                "actions_count": behavior.actions_count,
                "assets_viewed": behavior.assets_viewed,
                "assets_uploaded": behavior.assets_uploaded,
                "searches_performed": behavior.searches_performed,
                "user_segment": behavior.user_segment,
                "activity_level": behavior.activity_level
            }
            for behavior in behaviors
        ]
    
    async def _generate_charts(
        self,
        definition: ReportDefinition,
        report_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate charts for the report."""
        charts = []
        
        for chart_config in definition.charts:
            try:
                chart_data = await self._generate_single_chart(chart_config, report_data)
                charts.append(chart_data)
            except Exception as e:
                logger.error(f"Failed to generate chart {chart_config.title}: {e}")
                # Add error chart placeholder
                charts.append({
                    "title": chart_config.title,
                    "type": chart_config.chart_type,
                    "error": str(e),
                    "data": None
                })
        
        return charts
    
    async def _generate_single_chart(
        self,
        config: ChartConfig,
        report_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a single chart."""
        data_source = report_data.get(config.data_source, [])
        
        if not data_source:
            return {
                "title": config.title,
                "type": config.chart_type,
                "data": None,
                "message": f"No data available for {config.data_source}"
            }
        
        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame(data_source)
        
        # Apply chart-specific filters
        for filter_obj in config.filters:
            if filter_obj.field in df.columns:
                df = self._apply_dataframe_filter(df, filter_obj)
        
        # Generate chart based on type
        if config.chart_type == ChartType.LINE:
            chart_data = await self._generate_line_chart(config, df)
        elif config.chart_type == ChartType.BAR:
            chart_data = await self._generate_bar_chart(config, df)
        elif config.chart_type == ChartType.PIE:
            chart_data = await self._generate_pie_chart(config, df)
        elif config.chart_type == ChartType.TABLE:
            chart_data = await self._generate_table_chart(config, df)
        else:
            chart_data = {
                "title": config.title,
                "type": config.chart_type,
                "data": None,
                "message": f"Chart type {config.chart_type} not implemented"
            }
        
        return chart_data
    
    async def _generate_line_chart(
        self,
        config: ChartConfig,
        df: pd.DataFrame
    ) -> Dict[str, Any]:
        """Generate line chart data."""
        if config.x_axis not in df.columns or config.y_axis not in df.columns:
            return {
                "title": config.title,
                "type": config.chart_type,
                "data": None,
                "error": f"Required columns not found: {config.x_axis}, {config.y_axis}"
            }
        
        # Group and aggregate if specified
        if config.group_by and config.aggregation:
            if config.group_by in df.columns:
                grouped = df.groupby(config.group_by)
                if config.aggregation == "count":
                    aggregated = grouped.size().reset_index(name=config.y_axis)
                elif config.aggregation == "sum":
                    aggregated = grouped[config.y_axis].sum().reset_index()
                elif config.aggregation == "avg":
                    aggregated = grouped[config.y_axis].mean().reset_index()
                else:
                    aggregated = df
                df = aggregated
        
        # Sort if specified
        if config.sort_order:
            ascending = config.sort_order == "asc"
            df = df.sort_values(config.x_axis, ascending=ascending)
        
        # Limit if specified
        if config.limit:
            df = df.head(config.limit)
        
        # Prepare chart data
        chart_data = {
            "title": config.title,
            "type": config.chart_type,
            "x_axis": config.x_axis,
            "y_axis": config.y_axis,
            "data": {
                "labels": df[config.x_axis].tolist(),
                "values": df[config.y_axis].tolist()
            }
        }
        
        return chart_data
    
    async def _generate_bar_chart(
        self,
        config: ChartConfig,
        df: pd.DataFrame
    ) -> Dict[str, Any]:
        """Generate bar chart data."""
        return await self._generate_line_chart(config, df)  # Same structure
    
    async def _generate_pie_chart(
        self,
        config: ChartConfig,
        df: pd.DataFrame
    ) -> Dict[str, Any]:
        """Generate pie chart data."""
        if config.group_by not in df.columns:
            return {
                "title": config.title,
                "type": config.chart_type,
                "data": None,
                "error": f"Group by column not found: {config.group_by}"
            }
        
        # Count occurrences or sum values
        if config.aggregation == "count":
            grouped = df[config.group_by].value_counts()
        elif config.aggregation == "sum" and config.y_axis in df.columns:
            grouped = df.groupby(config.group_by)[config.y_axis].sum()
        else:
            grouped = df[config.group_by].value_counts()
        
        # Limit if specified
        if config.limit:
            grouped = grouped.head(config.limit)
        
        chart_data = {
            "title": config.title,
            "type": config.chart_type,
            "data": {
                "labels": grouped.index.tolist(),
                "values": grouped.values.tolist()
            }
        }
        
        return chart_data
    
    async def _generate_table_chart(
        self,
        config: ChartConfig,
        df: pd.DataFrame
    ) -> Dict[str, Any]:
        """Generate table data."""
        # Apply grouping and aggregation if specified
        if config.group_by and config.aggregation:
            if config.group_by in df.columns:
                grouped = df.groupby(config.group_by)
                if config.aggregation == "count":
                    df = grouped.size().reset_index(name="count")
                elif config.aggregation == "sum" and config.y_axis in df.columns:
                    df = grouped[config.y_axis].sum().reset_index()
                elif config.aggregation == "avg" and config.y_axis in df.columns:
                    df = grouped[config.y_axis].mean().reset_index()
        
        # Sort if specified
        if config.sort_order and config.y_axis in df.columns:
            ascending = config.sort_order == "asc"
            df = df.sort_values(config.y_axis, ascending=ascending)
        
        # Limit if specified
        if config.limit:
            df = df.head(config.limit)
        
        chart_data = {
            "title": config.title,
            "type": config.chart_type,
            "data": {
                "columns": df.columns.tolist(),
                "rows": df.values.tolist()
            }
        }
        
        return chart_data
    
    def _apply_dataframe_filter(
        self,
        df: pd.DataFrame,
        filter_obj: ReportFilter
    ) -> pd.DataFrame:
        """Apply filter to DataFrame."""
        if filter_obj.field not in df.columns:
            return df
        
        column = df[filter_obj.field]
        
        if filter_obj.operator == "eq":
            return df[column == filter_obj.value]
        elif filter_obj.operator == "ne":
            return df[column != filter_obj.value]
        elif filter_obj.operator == "gt":
            return df[column > filter_obj.value]
        elif filter_obj.operator == "lt":
            return df[column < filter_obj.value]
        elif filter_obj.operator == "gte":
            return df[column >= filter_obj.value]
        elif filter_obj.operator == "lte":
            return df[column <= filter_obj.value]
        elif filter_obj.operator == "in":
            return df[column.isin(filter_obj.value)]
        elif filter_obj.operator == "not_in":
            return df[~column.isin(filter_obj.value)]
        elif filter_obj.operator == "contains":
            return df[column.str.contains(str(filter_obj.value), na=False)]
        
        return df
    
    async def _format_report(
        self,
        definition: ReportDefinition,
        report_data: Dict[str, Any],
        charts_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Format the final report output."""
        if definition.format == ReportFormat.JSON:
            return {
                "report_id": definition.id,
                "name": definition.name,
                "description": definition.description,
                "generated_at": datetime.utcnow().isoformat(),
                "data": report_data,
                "charts": charts_data,
                "metadata": {
                    "total_records": sum(len(data) for data in report_data.values()),
                    "data_sources": definition.data_sources,
                    "filters_applied": len(definition.filters)
                }
            }
        elif definition.format == ReportFormat.CSV:
            return await self._format_csv_report(report_data, charts_data)
        elif definition.format == ReportFormat.HTML:
            return await self._format_html_report(definition, report_data, charts_data)
        elif definition.format == ReportFormat.PDF:
            return await self._format_pdf_report(definition, report_data, charts_data)
        else:
            return {
                "error": f"Unsupported format: {definition.format}",
                "data": report_data,
                "charts": charts_data
            }
    
    async def _format_csv_report(
        self,
        report_data: Dict[str, Any],
        charts_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Format report as CSV."""
        csv_files = {}
        
        # Create CSV for each data source
        for source, data in report_data.items():
            if data:
                output = io.StringIO()
                df = pd.DataFrame(data)
                df.to_csv(output, index=False)
                csv_files[f"{source}.csv"] = output.getvalue()
        
        # Create summary CSV for charts
        if charts_data:
            summary_data = []
            for chart in charts_data:
                if chart.get("data"):
                    summary_data.append({
                        "chart_title": chart["title"],
                        "chart_type": chart["type"],
                        "data_points": len(chart["data"].get("labels", [])) if isinstance(chart["data"], dict) else 0
                    })
            
            if summary_data:
                output = io.StringIO()
                df = pd.DataFrame(summary_data)
                df.to_csv(output, index=False)
                csv_files["charts_summary.csv"] = output.getvalue()
        
        return {
            "format": "csv",
            "files": csv_files
        }
    
    async def _format_html_report(
        self,
        definition: ReportDefinition,
        report_data: Dict[str, Any],
        charts_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Format report as HTML."""
        template = self.template_env.get_template('html_report')
        
        html_content = template.render(
            report_name=definition.name,
            description=definition.description,
            generated_at=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            charts=charts_data,
            data_sources=definition.data_sources,
            total_records=sum(len(data) for data in report_data.values())
        )
        
        return {
            "format": "html",
            "content": html_content
        }
    
    async def _format_pdf_report(
        self,
        definition: ReportDefinition,
        report_data: Dict[str, Any],
        charts_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Format report as PDF."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1  # Center
        )
        story.append(Paragraph(definition.name, title_style))
        story.append(Spacer(1, 12))
        
        # Description
        if definition.description:
            story.append(Paragraph(definition.description, styles['Normal']))
            story.append(Spacer(1, 12))
        
        # Generated timestamp
        story.append(Paragraph(
            f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
            styles['Normal']
        ))
        story.append(Spacer(1, 20))
        
        # Summary
        summary_data = [
            ['Data Sources', ', '.join(definition.data_sources)],
            ['Total Records', str(sum(len(data) for data in report_data.values()))],
            ['Charts Generated', str(len(charts_data))],
            ['Filters Applied', str(len(definition.filters))]
        ]
        
        summary_table = Table(summary_data, colWidths=[2*inch, 4*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 20))
        
        # Charts summaries
        for chart in charts_data:
            story.append(Paragraph(f"Chart: {chart['title']}", styles['Heading2']))
            story.append(Paragraph(f"Type: {chart['type']}", styles['Normal']))
            
            if chart.get('data'):
                # Add chart data as table if it's tabular
                if chart['type'] == 'table' and isinstance(chart['data'], dict):
                    chart_data = chart['data']
                    if 'columns' in chart_data and 'rows' in chart_data:
                        table_data = [chart_data['columns']] + chart_data['rows'][:10]  # Limit to 10 rows
                        chart_table = Table(table_data)
                        chart_table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, 0), 10),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black)
                        ]))
                        story.append(chart_table)
            
            story.append(Spacer(1, 12))
        
        # Build PDF
        doc.build(story)
        pdf_content = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return {
            "format": "pdf",
            "content": pdf_content,
            "filename": f"{definition.name.replace(' ', '_')}_report.pdf"
        }
    
    def _parse_date_range(self, date_range: Dict[str, Any]) -> tuple:
        """Parse date range configuration."""
        if "start" in date_range and "end" in date_range:
            start_date = datetime.fromisoformat(date_range["start"])
            end_date = datetime.fromisoformat(date_range["end"])
        elif "relative" in date_range:
            end_date = datetime.utcnow()
            relative = date_range["relative"]
            
            if relative == "last_24h":
                start_date = end_date - timedelta(days=1)
            elif relative == "last_7d":
                start_date = end_date - timedelta(days=7)
            elif relative == "last_30d":
                start_date = end_date - timedelta(days=30)
            elif relative == "last_90d":
                start_date = end_date - timedelta(days=90)
            else:
                # Default to last 7 days
                start_date = end_date - timedelta(days=7)
        else:
            # Default to last 7 days
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=7)
        
        return start_date, end_date
    
    def _reconstruct_definition(self, definition_dict: Dict[str, Any]) -> ReportDefinition:
        """Reconstruct ReportDefinition from dictionary."""
        filters = [
            ReportFilter(
                field=f["field"],
                operator=f["operator"],
                value=f["value"]
            )
            for f in definition_dict.get("filters", [])
        ]
        
        charts = [
            ChartConfig(
                chart_type=ChartType(c["chart_type"]),
                title=c["title"],
                x_axis=c["x_axis"],
                y_axis=c["y_axis"],
                data_source=c["data_source"],
                filters=[
                    ReportFilter(
                        field=f["field"],
                        operator=f["operator"],
                        value=f["value"]
                    )
                    for f in c.get("filters", [])
                ],
                group_by=c.get("group_by"),
                aggregation=c.get("aggregation"),
                limit=c.get("limit"),
                sort_order=c.get("sort_order")
            )
            for c in definition_dict.get("charts", [])
        ]
        
        return ReportDefinition(
            id=definition_dict["id"],
            name=definition_dict["name"],
            description=definition_dict["description"],
            report_type=ReportType(definition_dict["report_type"]),
            created_by=definition_dict["created_by"],
            created_at=datetime.fromisoformat(definition_dict["created_at"]),
            data_sources=definition_dict["data_sources"],
            filters=filters,
            date_range=definition_dict["date_range"],
            charts=charts,
            format=ReportFormat(definition_dict["format"]),
            schedule=definition_dict.get("schedule"),
            recipients=definition_dict.get("recipients"),
            tags=definition_dict.get("tags", []),
            is_public=definition_dict.get("is_public", False)
        )
    
    def _get_html_template(self) -> str:
        """Get HTML template for reports."""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>{{ report_name }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .header { text-align: center; margin-bottom: 30px; }
        .chart { margin: 20px 0; padding: 20px; border: 1px solid #ddd; }
        .summary { background-color: #f5f5f5; padding: 15px; margin-bottom: 20px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ report_name }}</h1>
        <p>{{ description }}</p>
        <p><em>Generated: {{ generated_at }}</em></p>
    </div>
    
    <div class="summary">
        <h3>Report Summary</h3>
        <p><strong>Data Sources:</strong> {{ data_sources|join(', ') }}</p>
        <p><strong>Total Records:</strong> {{ total_records }}</p>
        <p><strong>Charts:</strong> {{ charts|length }}</p>
    </div>
    
    {% for chart in charts %}
    <div class="chart">
        <h3>{{ chart.title }}</h3>
        <p><strong>Type:</strong> {{ chart.type }}</p>
        
        {% if chart.data and chart.type == 'table' %}
        <table>
            <thead>
                <tr>
                {% for col in chart.data.columns %}
                    <th>{{ col }}</th>
                {% endfor %}
                </tr>
            </thead>
            <tbody>
                {% for row in chart.data.rows %}
                <tr>
                    {% for cell in row %}
                    <td>{{ cell }}</td>
                    {% endfor %}
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% elif chart.error %}
        <p style="color: red;">Error: {{ chart.error }}</p>
        {% elif not chart.data %}
        <p>No data available for this chart.</p>
        {% endif %}
    </div>
    {% endfor %}
</body>
</html>
        """
    
    async def list_report_definitions(
        self,
        created_by: Optional[str] = None,
        is_public: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """List available report definitions."""
        try:
            redis_client = await self._get_redis()
            all_definitions = await redis_client.hgetall("report_definitions")
            
            definitions = []
            for definition_id, definition_data in all_definitions.items():
                definition_dict = json.loads(definition_data)
                
                # Apply filters
                if created_by and definition_dict.get("created_by") != created_by:
                    continue
                
                if is_public is not None and definition_dict.get("is_public") != is_public:
                    continue
                
                definitions.append({
                    "id": definition_dict["id"],
                    "name": definition_dict["name"],
                    "description": definition_dict["description"],
                    "report_type": definition_dict["report_type"],
                    "created_by": definition_dict["created_by"],
                    "created_at": definition_dict["created_at"],
                    "format": definition_dict["format"],
                    "is_public": definition_dict.get("is_public", False),
                    "last_generated": definition_dict.get("last_generated"),
                    "tags": definition_dict.get("tags", [])
                })
            
            return sorted(definitions, key=lambda x: x["created_at"], reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to list report definitions: {e}", exc_info=True)
            return []
    
    async def delete_report_definition(self, definition_id: str) -> bool:
        """Delete a report definition."""
        try:
            redis_client = await self._get_redis()
            result = await redis_client.hdel("report_definitions", definition_id)
            
            if result:
                logger.info(f"Deleted report definition: {definition_id}")
                return True
            else:
                logger.warning(f"Report definition not found: {definition_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete report definition: {e}", exc_info=True)
            return False
    
    async def generate_periodic_reports(self):
        """Generate scheduled reports."""
        try:
            # This would implement scheduled report generation
            # For now, this is a placeholder
            logger.debug("Periodic report generation not yet implemented")
            
        except Exception as e:
            logger.error(f"Failed to generate periodic reports: {e}", exc_info=True)
    
    async def close(self):
        """Clean up resources."""
        if self.redis_client:
            await self.redis_client.close()