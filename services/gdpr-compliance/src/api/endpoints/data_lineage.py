"""Data Lineage API endpoints"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from ...db.base import get_db
from ...core.exceptions import NotFoundError, ValidationError
from ...api.dependencies import get_current_user
from ...models.schemas import (
    DataLineageNodeCreate, DataLineageNodeUpdate, DataLineageNodeResponse,
    DataLineageEdgeCreate, DataLineageEdgeResponse,
    DataTransformationCreate, DataTransformationResponse,
    DataFlowSessionCreate, DataFlowSessionResponse,
    DataLineageGraphResponse, DataLineageMetricsResponse,
    DataImpactAnalysisRequest, DataImpactAnalysisResponse,
    LineageDirection, NodeType, User
)
from ...services.data_lineage_service import DataLineageService

router = APIRouter(prefix="/api/v1/data-lineage", tags=["data-lineage"])


# Node Management Endpoints

@router.post("/nodes", response_model=DataLineageNodeResponse, status_code=status.HTTP_201_CREATED)
async def create_lineage_node(
    node_data: DataLineageNodeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new data lineage node"""
    try:
        service = DataLineageService(db)
        return await service.create_node(node_data, str(current_user.id))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create lineage node")


@router.get("/nodes/{node_id}", response_model=DataLineageNodeResponse)
async def get_lineage_node(
    node_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get data lineage node by ID"""
    try:
        service = DataLineageService(db)
        return await service.get_node(node_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve lineage node")


@router.patch("/nodes/{node_id}", response_model=DataLineageNodeResponse)
async def update_lineage_node(
    node_id: str,
    update_data: DataLineageNodeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update data lineage node"""
    try:
        service = DataLineageService(db)
        return await service.update_node(node_id, update_data)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to update lineage node")


@router.get("/nodes", response_model=List[DataLineageNodeResponse])
async def list_lineage_nodes(
    node_type: Optional[NodeType] = Query(None, description="Filter by node type"),
    schema_name: Optional[str] = Query(None, description="Filter by schema name"),
    is_sensitive: Optional[bool] = Query(None, description="Filter by sensitivity"),
    classification_level: Optional[str] = Query(None, description="Filter by classification level"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of nodes to return"),
    offset: int = Query(0, ge=0, description="Number of nodes to skip"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List data lineage nodes with filtering"""
    try:
        service = DataLineageService(db)
        return await service.list_nodes(
            node_type=node_type,
            schema_name=schema_name,
            is_sensitive=is_sensitive,
            classification_level=classification_level,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve lineage nodes")


# Edge Management Endpoints

@router.post("/edges", response_model=DataLineageEdgeResponse, status_code=status.HTTP_201_CREATED)
async def create_lineage_edge(
    edge_data: DataLineageEdgeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a data lineage edge (relationship)"""
    try:
        service = DataLineageService(db)
        return await service.create_edge(edge_data, str(current_user.id))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create lineage edge")


# Transformation Tracking Endpoints

@router.post("/transformations", response_model=DataTransformationResponse, status_code=status.HTTP_201_CREATED)
async def record_transformation(
    transformation_data: DataTransformationCreate,
    session_id: Optional[str] = Query(None, description="Data flow session ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Record a data transformation"""
    try:
        service = DataLineageService(db)
        return await service.record_transformation(
            transformation_data, 
            session_id, 
            str(current_user.id)
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to record transformation")


# Flow Session Management Endpoints

@router.post("/sessions", response_model=DataFlowSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_flow_session(
    session_data: DataFlowSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a data flow session"""
    try:
        service = DataLineageService(db)
        return await service.create_flow_session(session_data, str(current_user.id))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create flow session")


@router.patch("/sessions/{session_id}/end", response_model=DataFlowSessionResponse)
async def end_flow_session(
    session_id: str,
    success: bool = Query(True, description="Whether the session completed successfully"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """End a data flow session"""
    try:
        service = DataLineageService(db)
        return await service.end_flow_session(session_id, success)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to end flow session")


# Lineage Querying Endpoints

@router.get("/nodes/{node_id}/lineage", response_model=DataLineageGraphResponse)
async def get_lineage_graph(
    node_id: str,
    direction: LineageDirection = Query(LineageDirection.BOTH, description="Lineage direction"),
    max_depth: int = Query(5, ge=1, le=10, description="Maximum traversal depth"),
    include_transformations: bool = Query(True, description="Include transformation details"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get data lineage graph for a node"""
    try:
        service = DataLineageService(db)
        return await service.get_lineage_graph(
            node_id, direction, max_depth, include_transformations
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve lineage graph")


@router.get("/nodes/{node_id}/upstream", response_model=DataLineageGraphResponse)
async def get_upstream_lineage(
    node_id: str,
    max_depth: int = Query(5, ge=1, le=10, description="Maximum traversal depth"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get upstream data lineage (sources)"""
    try:
        service = DataLineageService(db)
        return await service.get_upstream_lineage(node_id, max_depth)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve upstream lineage")


@router.get("/nodes/{node_id}/downstream", response_model=DataLineageGraphResponse)
async def get_downstream_lineage(
    node_id: str,
    max_depth: int = Query(5, ge=1, le=10, description="Maximum traversal depth"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get downstream data lineage (targets)"""
    try:
        service = DataLineageService(db)
        return await service.get_downstream_lineage(node_id, max_depth)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve downstream lineage")


# Impact Analysis Endpoints

@router.post("/impact-analysis", response_model=DataImpactAnalysisResponse, status_code=status.HTTP_201_CREATED)
async def analyze_impact(
    request: DataImpactAnalysisRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Analyze impact of changes to data nodes"""
    try:
        service = DataLineageService(db)
        return await service.analyze_impact(request)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to analyze impact")


# Metrics and Analytics Endpoints

@router.get("/metrics", response_model=DataLineageMetricsResponse)
async def get_lineage_metrics(
    start_date: Optional[datetime] = Query(None, description="Start date for metrics"),
    end_date: Optional[datetime] = Query(None, description="End date for metrics"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get data lineage metrics"""
    try:
        service = DataLineageService(db)
        return await service.get_lineage_metrics(start_date, end_date)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve lineage metrics")


# Health Check Endpoint

@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db)
):
    """Health check for data lineage service"""
    try:
        # Test database connection
        await db.execute("SELECT 1")
        return {
            "status": "healthy",
            "service": "data-lineage",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )