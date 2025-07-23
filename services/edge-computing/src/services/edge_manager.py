"""
Edge Manager Service

Manages edge nodes, task distribution, and cluster coordination.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from aioredis import Redis
import structlog
import httpx
from collections import defaultdict

from ..core.config import settings
from ..models.schemas import (
    EdgeNode, NodeStatus, NodeType, ProcessingTask, TaskStatus,
    TaskPriority, LoadBalanceStrategy, TaskDistribution,
    NodeHeartbeat, ClusterStatus, EdgeAlert, AlertType
)
from ..db.models import EdgeNodeModel, ProcessingTaskModel
from ..utils.metrics import edge_metrics


logger = structlog.get_logger()


class EdgeManager:
    """Manages edge computing cluster"""
    
    def __init__(self, db: AsyncSession, redis: Redis):
        self.db = db
        self.redis = redis
        self.node_id = settings.NODE_ID
        self.is_master = settings.IS_MASTER_NODE
        self.location = settings.NODE_LOCATION
        
        # Node tracking
        self.active_nodes: Dict[str, EdgeNode] = {}
        self.node_health: Dict[str, NodeHeartbeat] = {}
        self.node_capabilities: Dict[str, Set[str]] = defaultdict(set)
        
        # Task management
        self.pending_tasks: List[ProcessingTask] = []
        self.task_assignments: Dict[str, str] = {}  # task_id -> node_id
        
        # Background tasks
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._monitor_task: Optional[asyncio.Task] = None
        self._scheduler_task: Optional[asyncio.Task] = None
        
        # HTTP client for inter-node communication
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def initialize(self):
        """Initialize edge manager"""
        logger.info("Initializing edge manager", node_id=self.node_id, is_master=self.is_master)
        
        # Register this node
        await self._register_node()
        
        # Start background tasks
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        if self.is_master:
            self._monitor_task = asyncio.create_task(self._monitor_nodes())
            self._scheduler_task = asyncio.create_task(self._task_scheduler())
        
        # Load existing nodes from database
        await self._load_nodes()
    
    async def shutdown(self):
        """Shutdown edge manager"""
        logger.info("Shutting down edge manager")
        
        # Cancel background tasks
        for task in [self._heartbeat_task, self._monitor_task, self._scheduler_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Mark node as offline
        await self._update_node_status(self.node_id, NodeStatus.OFFLINE)
        
        # Close HTTP client
        await self.http_client.aclose()
    
    async def _register_node(self):
        """Register this node in the cluster"""
        node_data = {
            "node_id": self.node_id,
            "node_type": NodeType(settings.NODE_TYPE),
            "location": self.location,
            "status": NodeStatus.ONLINE,
            "capabilities": settings.NODE_CAPABILITIES,
            "resources": await self._get_node_resources(),
            "last_heartbeat": datetime.utcnow()
        }
        
        # Save to database
        db_node = await self.db.get(EdgeNodeModel, self.node_id)
        if db_node:
            for key, value in node_data.items():
                setattr(db_node, key, value)
        else:
            db_node = EdgeNodeModel(**node_data)
            self.db.add(db_node)
        
        await self.db.commit()
        
        # Notify master node if we're not the master
        if not self.is_master and settings.MASTER_NODE_URL:
            try:
                await self.http_client.post(
                    f"{settings.MASTER_NODE_URL}/api/v1/edge/nodes/register",
                    json=node_data
                )
            except Exception as e:
                logger.error("Failed to register with master node", error=str(e))
    
    async def _get_node_resources(self) -> Dict[str, Any]:
        """Get current node resources"""
        import psutil
        
        resources = {
            "cpu_count": psutil.cpu_count(),
            "cpu_freq_mhz": psutil.cpu_freq().current if psutil.cpu_freq() else 0,
            "memory_total_gb": psutil.virtual_memory().total / (1024**3),
            "memory_available_gb": psutil.virtual_memory().available / (1024**3),
            "disk_total_gb": psutil.disk_usage('/').total / (1024**3),
            "disk_available_gb": psutil.disk_usage('/').free / (1024**3),
            "gpu_available": settings.ENABLE_GPU_PROCESSING,
            "network_bandwidth_mbps": settings.BANDWIDTH_LIMIT_MBPS or 1000
        }
        
        # Check GPU availability
        if settings.ENABLE_GPU_PROCESSING:
            try:
                import torch
                resources["gpu_count"] = torch.cuda.device_count()
                resources["gpu_memory_gb"] = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            except:
                resources["gpu_available"] = False
        
        return resources
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats"""
        while True:
            try:
                await asyncio.sleep(settings.HEALTH_CHECK_INTERVAL_SECONDS)
                
                # Collect metrics
                import psutil
                heartbeat = NodeHeartbeat(
                    node_id=self.node_id,
                    status=NodeStatus.ONLINE,
                    cpu_usage=psutil.cpu_percent(interval=1),
                    memory_usage=psutil.virtual_memory().percent,
                    disk_usage=psutil.disk_usage('/').percent,
                    active_tasks=await self._get_active_task_count(),
                    cache_size_gb=await self._get_cache_size_gb()
                )
                
                # GPU usage if available
                if settings.ENABLE_GPU_PROCESSING:
                    try:
                        import torch
                        if torch.cuda.is_available():
                            heartbeat.gpu_usage = (torch.cuda.memory_allocated() / torch.cuda.get_device_properties(0).total_memory) * 100
                    except:
                        pass
                
                # Store heartbeat
                await self.redis.setex(
                    f"edge:heartbeat:{self.node_id}",
                    settings.HEALTH_CHECK_INTERVAL_SECONDS * 2,
                    heartbeat.json()
                )
                
                # Update database
                await self._update_node_heartbeat(heartbeat)
                
                # Send to master if not master
                if not self.is_master and settings.MASTER_NODE_URL:
                    try:
                        await self.http_client.post(
                            f"{settings.MASTER_NODE_URL}/api/v1/edge/heartbeat",
                            json=heartbeat.dict()
                        )
                    except Exception as e:
                        logger.error("Failed to send heartbeat to master", error=str(e))
                
            except Exception as e:
                logger.error("Error in heartbeat loop", error=str(e))
    
    async def _monitor_nodes(self):
        """Monitor node health (master only)"""
        if not self.is_master:
            return
        
        while True:
            try:
                await asyncio.sleep(settings.HEALTH_CHECK_INTERVAL_SECONDS)
                
                # Check all nodes
                nodes = await self._get_all_nodes()
                for node in nodes:
                    # Check heartbeat
                    heartbeat_key = f"edge:heartbeat:{node.node_id}"
                    heartbeat_data = await self.redis.get(heartbeat_key)
                    
                    if heartbeat_data:
                        heartbeat = NodeHeartbeat.parse_raw(heartbeat_data)
                        self.node_health[node.node_id] = heartbeat
                        
                        # Check for high resource usage
                        if heartbeat.cpu_usage > 90:
                            await self._create_alert(
                                AlertType.HIGH_LOAD,
                                f"Node {node.node_id} CPU usage at {heartbeat.cpu_usage}%",
                                node.node_id,
                                "high"
                            )
                        
                        if heartbeat.disk_usage > 90:
                            await self._create_alert(
                                AlertType.LOW_STORAGE,
                                f"Node {node.node_id} disk usage at {heartbeat.disk_usage}%",
                                node.node_id,
                                "high"
                            )
                    else:
                        # Node is offline
                        if node.status == NodeStatus.ONLINE:
                            await self._update_node_status(node.node_id, NodeStatus.OFFLINE)
                            await self._create_alert(
                                AlertType.NODE_OFFLINE,
                                f"Node {node.node_id} is offline",
                                node.node_id,
                                "critical"
                            )
                            
                            # Reassign tasks from offline node
                            await self._reassign_node_tasks(node.node_id)
                
                # Update cluster metrics
                await self._update_cluster_metrics()
                
            except Exception as e:
                logger.error("Error in node monitoring", error=str(e))
    
    async def _task_scheduler(self):
        """Schedule tasks to nodes (master only)"""
        if not self.is_master:
            return
        
        while True:
            try:
                await asyncio.sleep(5)  # Check every 5 seconds
                
                # Get pending tasks
                pending_tasks = await self._get_pending_tasks()
                if not pending_tasks:
                    continue
                
                # Get available nodes
                available_nodes = await self._get_available_nodes()
                if not available_nodes:
                    logger.warning("No available nodes for task scheduling")
                    continue
                
                # Create task distribution plan
                distribution = await self._create_task_distribution(
                    pending_tasks,
                    available_nodes,
                    LoadBalanceStrategy.CAPABILITY_BASED
                )
                
                # Assign tasks
                for node_id, task_ids in distribution.task_assignments.items():
                    for task_id in task_ids:
                        await self._assign_task_to_node(task_id, node_id)
                
                logger.info(
                    "Scheduled tasks",
                    total_tasks=len(pending_tasks),
                    assigned_tasks=sum(len(tasks) for tasks in distribution.task_assignments.values())
                )
                
            except Exception as e:
                logger.error("Error in task scheduler", error=str(e))
    
    async def _create_task_distribution(
        self,
        tasks: List[ProcessingTask],
        nodes: List[EdgeNode],
        strategy: LoadBalanceStrategy
    ) -> TaskDistribution:
        """Create optimal task distribution"""
        assignments: Dict[str, List[str]] = defaultdict(list)
        
        if strategy == LoadBalanceStrategy.ROUND_ROBIN:
            # Simple round-robin
            for i, task in enumerate(tasks):
                node = nodes[i % len(nodes)]
                assignments[node.node_id].append(task.task_id)
        
        elif strategy == LoadBalanceStrategy.LEAST_LOADED:
            # Assign to least loaded nodes
            node_loads = {node.node_id: 0 for node in nodes}
            
            for task in sorted(tasks, key=lambda t: t.priority.value, reverse=True):
                # Find least loaded node
                min_load_node = min(node_loads.keys(), key=lambda n: node_loads[n])
                assignments[min_load_node].append(task.task_id)
                node_loads[min_load_node] += 1
        
        elif strategy == LoadBalanceStrategy.CAPABILITY_BASED:
            # Match tasks to node capabilities
            for task in sorted(tasks, key=lambda t: t.priority.value, reverse=True):
                # Find nodes with required capabilities
                capable_nodes = [
                    node for node in nodes
                    if task.task_type.value in node.capabilities
                ]
                
                if not capable_nodes:
                    logger.warning(f"No capable nodes for task {task.task_id}")
                    continue
                
                # Choose least loaded capable node
                node_loads = {
                    node.node_id: len(assignments.get(node.node_id, []))
                    for node in capable_nodes
                }
                min_load_node = min(node_loads.keys(), key=lambda n: node_loads[n])
                assignments[min_load_node].append(task.task_id)
        
        elif strategy == LoadBalanceStrategy.GEOGRAPHIC:
            # Assign based on geographic proximity
            # For now, prefer nodes in same location
            for task in tasks:
                local_nodes = [n for n in nodes if n.location == self.location]
                target_nodes = local_nodes if local_nodes else nodes
                
                node = target_nodes[0]  # Simple selection for now
                assignments[node.node_id].append(task.task_id)
        
        # Calculate load balance score
        if assignments:
            loads = [len(tasks) for tasks in assignments.values()]
            avg_load = sum(loads) / len(loads)
            variance = sum((load - avg_load) ** 2 for load in loads) / len(loads)
            load_balance_score = 1 - (variance ** 0.5) / avg_load if avg_load > 0 else 1
        else:
            load_balance_score = 0
        
        return TaskDistribution(
            strategy=strategy,
            task_assignments=dict(assignments),
            estimated_completion_time=datetime.utcnow() + timedelta(minutes=30),
            load_balance_score=load_balance_score
        )
    
    async def _assign_task_to_node(self, task_id: str, node_id: str):
        """Assign a task to a specific node"""
        # Update task in database
        result = await self.db.execute(
            update(ProcessingTaskModel)
            .where(ProcessingTaskModel.task_id == task_id)
            .values(
                assigned_node=node_id,
                status=TaskStatus.ASSIGNED,
                updated_at=datetime.utcnow()
            )
        )
        await self.db.commit()
        
        # Store assignment in Redis
        await self.redis.setex(
            f"edge:task:assignment:{task_id}",
            3600,  # 1 hour TTL
            node_id
        )
        
        # Notify the node
        node = await self._get_node(node_id)
        if node and node.node_id != self.node_id:
            try:
                # For remote nodes, send HTTP request
                await self.http_client.post(
                    f"http://{node_id}:8018/api/v1/edge/tasks/{task_id}/execute"
                )
            except Exception as e:
                logger.error(f"Failed to notify node {node_id} about task {task_id}", error=str(e))
        
        # Update metrics
        edge_metrics.tasks_assigned.labels(node_id=node_id).inc()
    
    async def _get_pending_tasks(self) -> List[ProcessingTask]:
        """Get pending tasks from database"""
        result = await self.db.execute(
            select(ProcessingTaskModel)
            .where(ProcessingTaskModel.status == TaskStatus.PENDING)
            .order_by(ProcessingTaskModel.priority.desc(), ProcessingTaskModel.created_at)
            .limit(100)
        )
        
        tasks = result.scalars().all()
        return [ProcessingTask.from_orm(task) for task in tasks]
    
    async def _get_available_nodes(self) -> List[EdgeNode]:
        """Get available nodes for task assignment"""
        result = await self.db.execute(
            select(EdgeNodeModel)
            .where(EdgeNodeModel.status.in_([NodeStatus.ONLINE, NodeStatus.BUSY]))
        )
        
        nodes = result.scalars().all()
        available = []
        
        for node in nodes:
            # Check if node has capacity
            heartbeat = self.node_health.get(node.node_id)
            if heartbeat and heartbeat.cpu_usage < 80 and heartbeat.memory_usage < 80:
                available.append(EdgeNode.from_orm(node))
        
        return available
    
    async def _get_node(self, node_id: str) -> Optional[EdgeNode]:
        """Get node by ID"""
        result = await self.db.get(EdgeNodeModel, node_id)
        return EdgeNode.from_orm(result) if result else None
    
    async def _get_all_nodes(self) -> List[EdgeNode]:
        """Get all nodes"""
        result = await self.db.execute(select(EdgeNodeModel))
        nodes = result.scalars().all()
        return [EdgeNode.from_orm(node) for node in nodes]
    
    async def _update_node_status(self, node_id: str, status: NodeStatus):
        """Update node status"""
        await self.db.execute(
            update(EdgeNodeModel)
            .where(EdgeNodeModel.node_id == node_id)
            .values(status=status, updated_at=datetime.utcnow())
        )
        await self.db.commit()
    
    async def _update_node_heartbeat(self, heartbeat: NodeHeartbeat):
        """Update node heartbeat in database"""
        await self.db.execute(
            update(EdgeNodeModel)
            .where(EdgeNodeModel.node_id == heartbeat.node_id)
            .values(
                last_heartbeat=heartbeat.timestamp,
                performance_metrics={
                    "cpu_usage": heartbeat.cpu_usage,
                    "memory_usage": heartbeat.memory_usage,
                    "disk_usage": heartbeat.disk_usage,
                    "gpu_usage": heartbeat.gpu_usage,
                    "active_tasks": heartbeat.active_tasks
                }
            )
        )
        await self.db.commit()
    
    async def _reassign_node_tasks(self, node_id: str):
        """Reassign tasks from a failed node"""
        # Get tasks assigned to the node
        result = await self.db.execute(
            select(ProcessingTaskModel)
            .where(
                and_(
                    ProcessingTaskModel.assigned_node == node_id,
                    ProcessingTaskModel.status.in_([TaskStatus.ASSIGNED, TaskStatus.PROCESSING])
                )
            )
        )
        
        tasks = result.scalars().all()
        
        # Reset tasks to pending
        for task in tasks:
            task.status = TaskStatus.PENDING
            task.assigned_node = None
            task.retry_count += 1
        
        await self.db.commit()
        
        logger.info(f"Reassigned {len(tasks)} tasks from failed node {node_id}")
    
    async def _create_alert(self, alert_type: AlertType, message: str, node_id: Optional[str], severity: str):
        """Create an alert"""
        alert = EdgeAlert(
            alert_type=alert_type,
            severity=severity,
            node_id=node_id,
            message=message
        )
        
        # Store in Redis for quick access
        await self.redis.lpush("edge:alerts", alert.json())
        await self.redis.ltrim("edge:alerts", 0, 999)  # Keep last 1000 alerts
        
        # Log alert
        logger.warning(f"Edge alert: {message}", alert_type=alert_type.value, severity=severity)
        
        # Update metrics
        edge_metrics.alerts_created.labels(type=alert_type.value, severity=severity).inc()
    
    async def _get_active_task_count(self) -> int:
        """Get count of active tasks on this node"""
        result = await self.db.execute(
            select(ProcessingTaskModel)
            .where(
                and_(
                    ProcessingTaskModel.assigned_node == self.node_id,
                    ProcessingTaskModel.status.in_([TaskStatus.ASSIGNED, TaskStatus.PROCESSING])
                )
            )
        )
        return len(result.scalars().all())
    
    async def _get_cache_size_gb(self) -> float:
        """Get current cache size in GB"""
        # This would interface with the cache manager
        # For now, return a placeholder
        return 0.0
    
    async def _update_cluster_metrics(self):
        """Update cluster-wide metrics"""
        nodes = await self._get_all_nodes()
        online_nodes = [n for n in nodes if n.status == NodeStatus.ONLINE]
        
        # Calculate cluster capacity
        total_cpu = sum(n.resources.get("cpu_count", 0) for n in online_nodes)
        total_memory = sum(n.resources.get("memory_total_gb", 0) for n in online_nodes)
        total_storage = sum(n.resources.get("disk_total_gb", 0) for n in online_nodes)
        
        # Update metrics
        edge_metrics.cluster_nodes.labels(status="online").set(len(online_nodes))
        edge_metrics.cluster_nodes.labels(status="total").set(len(nodes))
        edge_metrics.cluster_capacity.labels(resource="cpu").set(total_cpu)
        edge_metrics.cluster_capacity.labels(resource="memory_gb").set(total_memory)
        edge_metrics.cluster_capacity.labels(resource="storage_gb").set(total_storage)
    
    async def _load_nodes(self):
        """Load nodes from database on startup"""
        nodes = await self._get_all_nodes()
        for node in nodes:
            self.active_nodes[node.node_id] = node
            self.node_capabilities[node.node_id] = set(node.capabilities)
    
    async def get_cluster_status(self) -> ClusterStatus:
        """Get current cluster status"""
        nodes = await self._get_all_nodes()
        online_nodes = [n for n in nodes if n.status == NodeStatus.ONLINE]
        
        # Calculate totals
        total_capacity = {
            "cpu_cores": sum(n.resources.get("cpu_count", 0) for n in online_nodes),
            "memory_gb": sum(n.resources.get("memory_total_gb", 0) for n in online_nodes),
            "storage_gb": sum(n.resources.get("disk_total_gb", 0) for n in online_nodes),
            "gpu_count": sum(n.resources.get("gpu_count", 0) for n in online_nodes)
        }
        
        # Calculate used capacity from heartbeats
        used_capacity = {
            "cpu_percent": sum(self.node_health.get(n.node_id, NodeHeartbeat(node_id=n.node_id, status=NodeStatus.ONLINE, cpu_usage=0, memory_usage=0, disk_usage=0, active_tasks=0, cache_size_gb=0)).cpu_usage for n in online_nodes) / len(online_nodes) if online_nodes else 0,
            "memory_percent": sum(self.node_health.get(n.node_id, NodeHeartbeat(node_id=n.node_id, status=NodeStatus.ONLINE, cpu_usage=0, memory_usage=0, disk_usage=0, active_tasks=0, cache_size_gb=0)).memory_usage for n in online_nodes) / len(online_nodes) if online_nodes else 0,
            "storage_percent": sum(self.node_health.get(n.node_id, NodeHeartbeat(node_id=n.node_id, status=NodeStatus.ONLINE, cpu_usage=0, memory_usage=0, disk_usage=0, active_tasks=0, cache_size_gb=0)).disk_usage for n in online_nodes) / len(online_nodes) if online_nodes else 0
        }
        
        # Get task statistics
        active_tasks_result = await self.db.execute(
            select(ProcessingTaskModel)
            .where(ProcessingTaskModel.status.in_([TaskStatus.ASSIGNED, TaskStatus.PROCESSING]))
        )
        active_tasks = len(active_tasks_result.scalars().all())
        
        # Get 24h statistics
        yesterday = datetime.utcnow() - timedelta(days=1)
        completed_result = await self.db.execute(
            select(ProcessingTaskModel)
            .where(
                and_(
                    ProcessingTaskModel.status == TaskStatus.COMPLETED,
                    ProcessingTaskModel.completed_at >= yesterday
                )
            )
        )
        completed_tasks = len(completed_result.scalars().all())
        
        failed_result = await self.db.execute(
            select(ProcessingTaskModel)
            .where(
                and_(
                    ProcessingTaskModel.status == TaskStatus.FAILED,
                    ProcessingTaskModel.updated_at >= yesterday
                )
            )
        )
        failed_tasks = len(failed_result.scalars().all())
        
        return ClusterStatus(
            total_nodes=len(nodes),
            online_nodes=len(online_nodes),
            total_capacity=total_capacity,
            used_capacity=used_capacity,
            active_tasks=active_tasks,
            completed_tasks_24h=completed_tasks,
            failed_tasks_24h=failed_tasks,
            average_task_duration=0.0,  # TODO: Calculate from completed tasks
            nodes=nodes
        )