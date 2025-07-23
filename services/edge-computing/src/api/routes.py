"""
API routes for Edge Computing Service
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timedelta

from ..core.deps import (
    get_db, get_edge_manager, get_task_processor,
    get_cache_manager, get_current_user, verify_api_key
)
from ..models.schemas import (
    EdgeNode, EdgeNodeCreate, EdgeNodeUpdate, NodeHeartbeat,
    ProcessingTask, TaskCreate, TaskUpdate, TaskAssignment,
    CacheEntry, CacheStats, ClusterStatus, EdgeAlert,
    LoadBalanceStrategy, TaskDistribution, EdgeMetrics,
    TranscodeParameters, ImageProcessingParameters, AIAnalysisParameters
)
from ..db.models import (
    EdgeNodeModel, ProcessingTaskModel, CacheEntryModel,
    EdgeAlertModel, EdgeMetricsModel
)
from ..services.edge_manager import EdgeManager
from ..services.task_processor import TaskProcessor
from ..services.cache_manager import CacheManager


router = APIRouter(prefix="/api/v1/edge", tags=["edge-computing"])


# Node Management
@router.post("/nodes/register", response_model=EdgeNode)
async def register_node(
    node: EdgeNodeCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_api_key)
):
    """Register a new edge node"""
    # Check if node already exists
    existing = await db.get(EdgeNodeModel, node.node_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Node {node.node_id} already registered"
        )
    
    # Create node
    db_node = EdgeNodeModel(**node.dict())
    db.add(db_node)
    await db.commit()
    await db.refresh(db_node)
    
    return EdgeNode.from_orm(db_node)


@router.get("/nodes", response_model=List[EdgeNode])
async def list_nodes(
    status: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List all edge nodes"""
    query = select(EdgeNodeModel)
    
    if status:
        query = query.where(EdgeNodeModel.status == status)
    if location:
        query = query.where(EdgeNodeModel.location == location)
    
    result = await db.execute(query)
    nodes = result.scalars().all()
    
    return [EdgeNode.from_orm(node) for node in nodes]


@router.get("/nodes/{node_id}", response_model=EdgeNode)
async def get_node(
    node_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get specific edge node"""
    node = await db.get(EdgeNodeModel, node_id)
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node {node_id} not found"
        )
    
    return EdgeNode.from_orm(node)


@router.patch("/nodes/{node_id}", response_model=EdgeNode)
async def update_node(
    node_id: str,
    update: EdgeNodeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update edge node"""
    node = await db.get(EdgeNodeModel, node_id)
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node {node_id} not found"
        )
    
    # Update fields
    update_data = update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(node, field, value)
    
    node.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(node)
    
    return EdgeNode.from_orm(node)


@router.delete("/nodes/{node_id}")
async def delete_node(
    node_id: str,
    db: AsyncSession = Depends(get_db),
    edge_manager: EdgeManager = Depends(get_edge_manager),
    current_user = Depends(get_current_user)
):
    """Delete edge node"""
    node = await db.get(EdgeNodeModel, node_id)
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node {node_id} not found"
        )
    
    # Reassign tasks if node has active tasks
    await edge_manager._reassign_node_tasks(node_id)
    
    # Delete node
    await db.delete(node)
    await db.commit()
    
    return {"message": f"Node {node_id} deleted"}


# Heartbeat
@router.post("/heartbeat")
async def node_heartbeat(
    heartbeat: NodeHeartbeat,
    edge_manager: EdgeManager = Depends(get_edge_manager),
    _: bool = Depends(verify_api_key)
):
    """Receive node heartbeat"""
    # Store heartbeat in Redis
    await edge_manager.redis.setex(
        f"edge:heartbeat:{heartbeat.node_id}",
        60,  # 1 minute TTL
        heartbeat.json()
    )
    
    # Update node in database
    await edge_manager._update_node_heartbeat(heartbeat)
    
    return {"status": "ok"}


# Task Management
@router.post("/tasks", response_model=ProcessingTask)
async def create_task(
    task: TaskCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    edge_manager: EdgeManager = Depends(get_edge_manager),
    current_user = Depends(get_current_user)
):
    """Create a new processing task"""
    # Create task
    db_task = ProcessingTaskModel(
        task_type=task.task_type,
        asset_id=task.asset_id,
        parameters=task.parameters,
        priority=task.priority,
        metadata=task.metadata or {}
    )
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    
    # Schedule task if master node
    if edge_manager.is_master:
        # Task will be picked up by scheduler
        pass
    
    return ProcessingTask.from_orm(db_task)


@router.get("/tasks", response_model=List[ProcessingTask])
async def list_tasks(
    status: Optional[str] = Query(None),
    node_id: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List processing tasks"""
    query = select(ProcessingTaskModel).limit(limit)
    
    if status:
        query = query.where(ProcessingTaskModel.status == status)
    if node_id:
        query = query.where(ProcessingTaskModel.assigned_node == node_id)
    
    result = await db.execute(query.order_by(ProcessingTaskModel.created_at.desc()))
    tasks = result.scalars().all()
    
    return [ProcessingTask.from_orm(task) for task in tasks]


@router.get("/tasks/{task_id}", response_model=ProcessingTask)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get specific task"""
    task = await db.get(ProcessingTaskModel, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    
    return ProcessingTask.from_orm(task)


@router.patch("/tasks/{task_id}", response_model=ProcessingTask)
async def update_task(
    task_id: str,
    update: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update task status"""
    task = await db.get(ProcessingTaskModel, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    
    # Update fields
    update_data = update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    
    task.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(task)
    
    return ProcessingTask.from_orm(task)


@router.post("/tasks/{task_id}/execute")
async def execute_task(
    task_id: str,
    background_tasks: BackgroundTasks,
    task_processor: TaskProcessor = Depends(get_task_processor),
    _: bool = Depends(verify_api_key)
):
    """Execute a task on this node"""
    # Execute task in background
    background_tasks.add_task(task_processor.execute_task, task_id)
    
    return {"message": f"Task {task_id} execution started"}


@router.get("/tasks/{task_id}/progress")
async def get_task_progress(
    task_id: str,
    task_processor: TaskProcessor = Depends(get_task_processor),
    current_user = Depends(get_current_user)
):
    """Get task progress"""
    progress = await task_processor.get_task_progress(task_id)
    
    return {"task_id": task_id, "progress": progress}


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    task_processor: TaskProcessor = Depends(get_task_processor),
    current_user = Depends(get_current_user)
):
    """Cancel a running task"""
    await task_processor.cancel_task(task_id)
    
    return {"message": f"Task {task_id} cancelled"}


# Cache Management
@router.get("/cache/{cache_key}")
async def get_cached_item(
    cache_key: str,
    cache_manager: CacheManager = Depends(get_cache_manager),
    current_user = Depends(get_current_user)
):
    """Get item from cache"""
    file_path = await cache_manager.get(cache_key)
    
    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cache key not found"
        )
    
    return {"cache_key": cache_key, "file_path": str(file_path)}


@router.delete("/cache/{cache_key}")
async def delete_cached_item(
    cache_key: str,
    cache_manager: CacheManager = Depends(get_cache_manager),
    current_user = Depends(get_current_user)
):
    """Delete item from cache"""
    success = await cache_manager.delete(cache_key)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cache key not found"
        )
    
    return {"message": f"Cache key {cache_key} deleted"}


@router.get("/cache/stats", response_model=CacheStats)
async def get_cache_stats(
    cache_manager: CacheManager = Depends(get_cache_manager),
    current_user = Depends(get_current_user)
):
    """Get cache statistics"""
    return await cache_manager.get_stats()


@router.post("/cache/clear")
async def clear_cache(
    cache_manager: CacheManager = Depends(get_cache_manager),
    current_user = Depends(get_current_user)
):
    """Clear entire cache"""
    await cache_manager.clear()
    return {"message": "Cache cleared"}


# Cluster Management
@router.get("/cluster/status", response_model=ClusterStatus)
async def get_cluster_status(
    edge_manager: EdgeManager = Depends(get_edge_manager),
    current_user = Depends(get_current_user)
):
    """Get cluster status"""
    return await edge_manager.get_cluster_status()


@router.post("/cluster/distribution")
async def create_task_distribution(
    tasks: List[str],
    strategy: LoadBalanceStrategy = LoadBalanceStrategy.CAPABILITY_BASED,
    edge_manager: EdgeManager = Depends(get_edge_manager),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create task distribution plan"""
    # Get tasks
    result = await db.execute(
        select(ProcessingTaskModel)
        .where(ProcessingTaskModel.task_id.in_(tasks))
    )
    task_models = result.scalars().all()
    processing_tasks = [ProcessingTask.from_orm(t) for t in task_models]
    
    # Get available nodes
    available_nodes = await edge_manager._get_available_nodes()
    
    # Create distribution
    distribution = await edge_manager._create_task_distribution(
        processing_tasks,
        available_nodes,
        strategy
    )
    
    return distribution


# Alerts
@router.get("/alerts", response_model=List[EdgeAlert])
async def list_alerts(
    resolved: Optional[bool] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List alerts"""
    query = select(EdgeAlertModel).limit(limit)
    
    if resolved is not None:
        query = query.where(EdgeAlertModel.resolved == resolved)
    if severity:
        query = query.where(EdgeAlertModel.severity == severity)
    
    result = await db.execute(query.order_by(EdgeAlertModel.created_at.desc()))
    alerts = result.scalars().all()
    
    return [EdgeAlert.from_orm(alert) for alert in alerts]


@router.patch("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Resolve an alert"""
    alert = await db.get(EdgeAlertModel, alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found"
        )
    
    alert.resolved = True
    alert.resolved_at = datetime.utcnow()
    
    await db.commit()
    
    return {"message": f"Alert {alert_id} resolved"}


# Metrics
@router.get("/metrics/{node_id}")
async def get_node_metrics(
    node_id: str,
    hours: int = Query(24, le=168),  # Max 7 days
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get node metrics"""
    since = datetime.utcnow() - timedelta(hours=hours)
    
    result = await db.execute(
        select(EdgeMetricsModel)
        .where(
            and_(
                EdgeMetricsModel.node_id == node_id,
                EdgeMetricsModel.timestamp >= since
            )
        )
        .order_by(EdgeMetricsModel.timestamp)
    )
    
    metrics = result.scalars().all()
    
    return [
        {
            "timestamp": m.timestamp,
            "tasks_processed": m.tasks_processed,
            "tasks_failed": m.tasks_failed,
            "avg_processing_time": m.avg_processing_time,
            "cache_hit_rate": m.cache_hit_rate,
            "cpu_utilization": m.cpu_utilization,
            "memory_utilization": m.memory_utilization,
            "gpu_utilization": m.gpu_utilization
        }
        for m in metrics
    ]


# Health Check
@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db)
):
    """Health check endpoint"""
    try:
        # Check database
        await db.execute("SELECT 1")
        
        return {
            "status": "healthy",
            "service": "edge-computing",
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "edge-computing",
            "error": str(e),
            "timestamp": datetime.utcnow()
        }