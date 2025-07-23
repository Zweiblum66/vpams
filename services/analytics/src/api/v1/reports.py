"""
Custom Reports API

This module provides REST API endpoints for creating, managing, and generating
custom analytics reports.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from shared.auth.dependencies import get_current_user
from shared.db.postgres import get_session
from shared.tracing.python_tracing import trace_async_function

from ...services.report_generator import (
    ReportGenerator, ReportDefinition, ReportType, ReportFormat,
    ChartType, ChartConfig, ReportFilter
)

router = APIRouter()

# Initialize report generator
report_generator = ReportGenerator()


class ReportFilterRequest(BaseModel):
    """Request model for report filters."""
    field: str = Field(..., description="Field to filter on")
    operator: str = Field(..., description="Filter operator (eq, ne, gt, lt, gte, lte, in, not_in, contains)")
    value: Any = Field(..., description="Filter value")


class ChartConfigRequest(BaseModel):
    """Request model for chart configuration."""
    chart_type: ChartType = Field(..., description="Chart type")
    title: str = Field(..., description="Chart title")
    x_axis: str = Field(..., description="X-axis field")
    y_axis: str = Field(..., description="Y-axis field")
    data_source: str = Field(..., description="Data source name")
    filters: List[ReportFilterRequest] = Field(default=[], description="Chart-specific filters")
    group_by: Optional[str] = Field(None, description="Group by field")
    aggregation: Optional[str] = Field(None, description="Aggregation method (count, sum, avg, max, min)")
    limit: Optional[int] = Field(None, ge=1, le=1000, description="Result limit")
    sort_order: Optional[str] = Field(None, description="Sort order (asc, desc)")


class ReportDefinitionRequest(BaseModel):
    """Request model for creating report definitions."""
    name: str = Field(..., min_length=1, max_length=255, description="Report name")
    description: str = Field("", max_length=1000, description="Report description")
    report_type: ReportType = Field(..., description="Report type")
    data_sources: List[str] = Field(..., min_items=1, description="Data sources to include")
    filters: List[ReportFilterRequest] = Field(default=[], description="Global filters")
    date_range: Dict[str, Any] = Field(..., description="Date range configuration")
    charts: List[ChartConfigRequest] = Field(default=[], description="Chart configurations")
    format: ReportFormat = Field(ReportFormat.JSON, description="Output format")
    schedule: Optional[Dict[str, Any]] = Field(None, description="Schedule configuration")
    recipients: Optional[List[str]] = Field(None, description="Report recipients")
    tags: List[str] = Field(default=[], description="Report tags")
    is_public: bool = Field(False, description="Whether report is public")


class ReportDefinitionResponse(BaseModel):
    """Response model for report definitions."""
    id: str
    name: str
    description: str
    report_type: str
    created_by: str
    created_at: str
    format: str
    is_public: bool
    last_generated: Optional[str]
    tags: List[str]


class ReportGenerationRequest(BaseModel):
    """Request model for generating reports."""
    definition_id: str = Field(..., description="Report definition ID")
    custom_filters: List[ReportFilterRequest] = Field(default=[], description="Additional filters")
    override_format: Optional[ReportFormat] = Field(None, description="Override output format")


@router.post("/definitions", response_model=dict)
async def create_report_definition(
    request: ReportDefinitionRequest,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Create a new report definition."""
    
    if not current_user.has_permission("analytics.create_reports"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Convert request to domain objects
        filters = [
            ReportFilter(
                field=f.field,
                operator=f.operator,
                value=f.value
            )
            for f in request.filters
        ]
        
        charts = [
            ChartConfig(
                chart_type=c.chart_type,
                title=c.title,
                x_axis=c.x_axis,
                y_axis=c.y_axis,
                data_source=c.data_source,
                filters=[
                    ReportFilter(
                        field=f.field,
                        operator=f.operator,
                        value=f.value
                    )
                    for f in c.filters
                ],
                group_by=c.group_by,
                aggregation=c.aggregation,
                limit=c.limit,
                sort_order=c.sort_order
            )
            for c in request.charts
        ]
        
        # Create report definition
        definition = ReportDefinition(
            id=str(uuid.uuid4()),
            name=request.name,
            description=request.description,
            report_type=request.report_type,
            created_by=str(current_user.id),
            created_at=datetime.utcnow(),
            data_sources=request.data_sources,
            filters=filters,
            date_range=request.date_range,
            charts=charts,
            format=request.format,
            schedule=request.schedule,
            recipients=request.recipients,
            tags=request.tags,
            is_public=request.is_public
        )
        
        # Save definition
        definition_id = await report_generator.create_report_definition(definition, db)
        
        return {
            "id": definition_id,
            "message": "Report definition created successfully",
            "created_at": definition.created_at.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create report definition: {str(e)}")


@router.get("/definitions", response_model=List[ReportDefinitionResponse])
async def list_report_definitions(
    created_by: Optional[str] = Query(None, description="Filter by creator"),
    is_public: Optional[bool] = Query(None, description="Filter by public status"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """List available report definitions."""
    
    if not current_user.has_permission("analytics.view_reports"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Apply user-based filtering
        filter_created_by = created_by
        if not current_user.has_permission("analytics.view_all_reports"):
            # Non-admin users can only see their own reports or public ones
            filter_created_by = str(current_user.id)
        
        definitions = await report_generator.list_report_definitions(
            created_by=filter_created_by,
            is_public=is_public
        )
        
        # Apply tag filtering if specified
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",")]
            definitions = [
                d for d in definitions
                if any(tag in d.get("tags", []) for tag in tag_list)
            ]
        
        return [
            ReportDefinitionResponse(
                id=d["id"],
                name=d["name"],
                description=d["description"],
                report_type=d["report_type"],
                created_by=d["created_by"],
                created_at=d["created_at"],
                format=d["format"],
                is_public=d["is_public"],
                last_generated=d.get("last_generated"),
                tags=d.get("tags", [])
            )
            for d in definitions
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list report definitions: {str(e)}")


@router.get("/definitions/{definition_id}")
async def get_report_definition(
    definition_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Get a specific report definition."""
    
    if not current_user.has_permission("analytics.view_reports"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Get definition from cache
        definitions = await report_generator.list_report_definitions()
        definition = next((d for d in definitions if d["id"] == definition_id), None)
        
        if not definition:
            raise HTTPException(status_code=404, detail="Report definition not found")
        
        # Check permissions
        if (definition["created_by"] != str(current_user.id) and 
            not definition["is_public"] and 
            not current_user.has_permission("analytics.view_all_reports")):
            raise HTTPException(status_code=403, detail="Access denied")
        
        return definition
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get report definition: {str(e)}")


@router.put("/definitions/{definition_id}")
async def update_report_definition(
    definition_id: str,
    request: ReportDefinitionRequest,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Update a report definition."""
    
    if not current_user.has_permission("analytics.create_reports"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Check if definition exists and user has permission
        definitions = await report_generator.list_report_definitions()
        existing = next((d for d in definitions if d["id"] == definition_id), None)
        
        if not existing:
            raise HTTPException(status_code=404, detail="Report definition not found")
        
        if (existing["created_by"] != str(current_user.id) and 
            not current_user.has_permission("analytics.admin")):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Convert request to domain objects (same as create)
        filters = [
            ReportFilter(
                field=f.field,
                operator=f.operator,
                value=f.value
            )
            for f in request.filters
        ]
        
        charts = [
            ChartConfig(
                chart_type=c.chart_type,
                title=c.title,
                x_axis=c.x_axis,
                y_axis=c.y_axis,
                data_source=c.data_source,
                filters=[
                    ReportFilter(
                        field=f.field,
                        operator=f.operator,
                        value=f.value
                    )
                    for f in c.filters
                ],
                group_by=c.group_by,
                aggregation=c.aggregation,
                limit=c.limit,
                sort_order=c.sort_order
            )
            for c in request.charts
        ]
        
        # Create updated definition
        definition = ReportDefinition(
            id=definition_id,
            name=request.name,
            description=request.description,
            report_type=request.report_type,
            created_by=existing["created_by"],  # Keep original creator
            created_at=datetime.fromisoformat(existing["created_at"]),  # Keep original date
            data_sources=request.data_sources,
            filters=filters,
            date_range=request.date_range,
            charts=charts,
            format=request.format,
            schedule=request.schedule,
            recipients=request.recipients,
            tags=request.tags,
            is_public=request.is_public
        )
        
        # Save updated definition
        await report_generator.create_report_definition(definition, db)
        
        return {
            "id": definition_id,
            "message": "Report definition updated successfully",
            "updated_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update report definition: {str(e)}")


@router.delete("/definitions/{definition_id}")
async def delete_report_definition(
    definition_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Delete a report definition."""
    
    if not current_user.has_permission("analytics.create_reports"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Check if definition exists and user has permission
        definitions = await report_generator.list_report_definitions()
        existing = next((d for d in definitions if d["id"] == definition_id), None)
        
        if not existing:
            raise HTTPException(status_code=404, detail="Report definition not found")
        
        if (existing["created_by"] != str(current_user.id) and 
            not current_user.has_permission("analytics.admin")):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Delete definition
        success = await report_generator.delete_report_definition(definition_id)
        
        if success:
            return {
                "message": "Report definition deleted successfully",
                "deleted_at": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to delete report definition")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete report definition: {str(e)}")


@router.post("/generate")
async def generate_report(
    request: ReportGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Generate a report based on definition."""
    
    if not current_user.has_permission("analytics.generate_reports"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Check if definition exists and user has permission
        definitions = await report_generator.list_report_definitions()
        definition = next((d for d in definitions if d["id"] == request.definition_id), None)
        
        if not definition:
            raise HTTPException(status_code=404, detail="Report definition not found")
        
        if (definition["created_by"] != str(current_user.id) and 
            not definition["is_public"] and 
            not current_user.has_permission("analytics.view_all_reports")):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Convert custom filters
        custom_filters = [
            ReportFilter(
                field=f.field,
                operator=f.operator,
                value=f.value
            )
            for f in request.custom_filters
        ]
        
        # Generate report
        report = await report_generator.generate_report(
            request.definition_id,
            db,
            custom_filters=custom_filters
        )
        
        return {
            "status": "completed",
            "generated_at": datetime.utcnow().isoformat(),
            "report": report
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


@router.post("/generate-async/{definition_id}")
async def generate_report_async(
    definition_id: str,
    background_tasks: BackgroundTasks,
    custom_filters: List[ReportFilterRequest] = [],
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Generate a report asynchronously (for large reports)."""
    
    if not current_user.has_permission("analytics.generate_reports"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Check if definition exists and user has permission
        definitions = await report_generator.list_report_definitions()
        definition = next((d for d in definitions if d["id"] == definition_id), None)
        
        if not definition:
            raise HTTPException(status_code=404, detail="Report definition not found")
        
        if (definition["created_by"] != str(current_user.id) and 
            not definition["is_public"] and 
            not current_user.has_permission("analytics.view_all_reports")):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Convert custom filters
        filters = [
            ReportFilter(
                field=f.field,
                operator=f.operator,
                value=f.value
            )
            for f in custom_filters
        ]
        
        # Add report generation to background tasks
        background_tasks.add_task(
            _generate_report_background,
            definition_id,
            str(current_user.id),
            filters,
            db
        )
        
        return {
            "status": "queued",
            "message": "Report generation started in background",
            "queued_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue report generation: {str(e)}")


async def _generate_report_background(
    definition_id: str,
    user_id: str,
    custom_filters: List[ReportFilter],
    db: AsyncSession
):
    """Background task for report generation."""
    try:
        report = await report_generator.generate_report(
            definition_id,
            db,
            custom_filters=custom_filters
        )
        
        # Store result in cache for later retrieval
        redis_client = await report_generator._get_redis()
        await redis_client.setex(
            f"report_result:{definition_id}:{user_id}",
            3600,  # 1 hour expiration
            json.dumps(report, default=str)
        )
        
    except Exception as e:
        # Store error in cache
        redis_client = await report_generator._get_redis()
        await redis_client.setex(
            f"report_result:{definition_id}:{user_id}",
            3600,  # 1 hour expiration
            json.dumps({"error": str(e)})
        )


@router.get("/result/{definition_id}")
async def get_report_result(
    definition_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Get the result of an asynchronous report generation."""
    
    if not current_user.has_permission("analytics.generate_reports"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        redis_client = await report_generator._get_redis()
        result = await redis_client.get(f"report_result:{definition_id}:{current_user.id}")
        
        if not result:
            return {
                "status": "not_found",
                "message": "No report result found. Report may still be generating or has expired."
            }
        
        report_data = json.loads(result)
        
        if "error" in report_data:
            return {
                "status": "error",
                "error": report_data["error"]
            }
        
        return {
            "status": "completed",
            "report": report_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get report result: {str(e)}")


@router.get("/templates")
async def get_report_templates(
    current_user = Depends(get_current_user)
):
    """Get available report templates."""
    
    if not current_user.has_permission("analytics.view_reports"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    templates = [
        {
            "id": "user_activity_summary",
            "name": "User Activity Summary",
            "description": "Overview of user activity metrics",
            "report_type": ReportType.USER_ACTIVITY,
            "data_sources": ["events", "user_sessions", "user_behavior"],
            "charts": [
                {
                    "chart_type": ChartType.LINE,
                    "title": "Daily Active Users",
                    "x_axis": "date",
                    "y_axis": "user_count",
                    "data_source": "user_sessions"
                },
                {
                    "chart_type": ChartType.PIE,
                    "title": "User Segments",
                    "group_by": "user_segment",
                    "data_source": "user_behavior"
                }
            ]
        },
        {
            "id": "asset_usage_report",
            "name": "Asset Usage Report",
            "description": "Analysis of asset interactions and usage patterns",
            "report_type": ReportType.ASSET_USAGE,
            "data_sources": ["asset_interactions", "events"],
            "charts": [
                {
                    "chart_type": ChartType.BAR,
                    "title": "Top Asset Types",
                    "x_axis": "asset_type",
                    "y_axis": "interaction_count",
                    "data_source": "asset_interactions"
                },
                {
                    "chart_type": ChartType.TABLE,
                    "title": "Most Downloaded Assets",
                    "data_source": "asset_interactions"
                }
            ]
        },
        {
            "id": "search_analytics",
            "name": "Search Analytics",
            "description": "Search query patterns and performance metrics",
            "report_type": ReportType.SEARCH_ANALYTICS,
            "data_sources": ["search_queries"],
            "charts": [
                {
                    "chart_type": ChartType.LINE,
                    "title": "Search Volume Over Time",
                    "x_axis": "timestamp",
                    "y_axis": "query_count",
                    "data_source": "search_queries"
                },
                {
                    "chart_type": ChartType.TABLE,
                    "title": "Top Search Terms",
                    "data_source": "search_queries"
                }
            ]
        }
    ]
    
    return templates


@router.get("/data-sources")
async def get_available_data_sources(
    current_user = Depends(get_current_user)
):
    """Get available data sources for reports."""
    
    if not current_user.has_permission("analytics.view_reports"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    data_sources = [
        {
            "name": "events",
            "description": "All user events and actions",
            "fields": [
                "event_type", "event_name", "category", "user_id", 
                "timestamp", "properties", "duration_ms"
            ]
        },
        {
            "name": "user_sessions",
            "description": "User session data",
            "fields": [
                "user_id", "session_id", "started_at", "ended_at", 
                "duration_seconds", "device_type", "browser", "os", 
                "page_views", "actions_count", "country"
            ]
        },
        {
            "name": "asset_interactions",
            "description": "Asset interaction tracking",
            "fields": [
                "asset_id", "user_id", "interaction_type", "timestamp", 
                "duration_seconds", "asset_type", "asset_size_bytes", "project_id"
            ]
        },
        {
            "name": "search_queries",
            "description": "Search query logs",
            "fields": [
                "user_id", "query_text", "query_type", "timestamp", 
                "results_count", "response_time_ms", "search_context"
            ]
        },
        {
            "name": "user_behavior",
            "description": "Aggregated user behavior patterns",
            "fields": [
                "user_id", "period_start", "period_end", "period_type", 
                "sessions_count", "total_time_minutes", "page_views", 
                "actions_count", "assets_viewed", "assets_uploaded", 
                "user_segment", "activity_level"
            ]
        }
    ]
    
    return data_sources


@router.get("/health")
async def health_check():
    """Health check for reports service."""
    return {
        "status": "healthy",
        "service": "custom_reports",
        "timestamp": datetime.utcnow().isoformat()
    }