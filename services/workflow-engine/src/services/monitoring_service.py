"""
Workflow Monitoring Service

This module provides monitoring and metrics for workflow execution, including:
- Execution metrics
- Performance tracking
- Health monitoring
- Alerting
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
import structlog
import aioredis

from ..models.schemas import WorkflowStatus, TaskStatus
from ..db.models import (
    WorkflowInstance as WorkflowInstanceDB,
    TaskInstance as TaskInstanceDB,
    WorkflowEvent as WorkflowEventDB
)
from ..core.config import settings

logger = structlog.get_logger()


class MonitoringService:
    """
    Service for monitoring workflow execution
    """
    
    def __init__(self, db_session: AsyncSession, redis_client: aioredis.Redis = None):
        self.db = db_session
        self.redis = redis_client
        self.metrics_prefix = "workflow:metrics:"
        self.alerts_channel = "workflow:alerts"
        
    async def start(self):
        """
        Start monitoring service
        """
        logger.info("Starting monitoring service")
        
        # Start periodic metrics collection
        asyncio.create_task(self._collect_metrics_periodically())
        
        # Start health checks
        asyncio.create_task(self._health_check_periodically())
        
        logger.info("Monitoring service started")
    
    async def _collect_metrics_periodically(self):
        """
        Collect metrics periodically
        """
        while True:
            try:
                await asyncio.sleep(60)  # Collect every minute
                await self.collect_metrics()
            except Exception as e:
                logger.error("Failed to collect metrics", error=str(e))
    
    async def _health_check_periodically(self):
        """
        Perform health checks periodically
        """
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                await self.check_health()
            except Exception as e:
                logger.error("Failed to perform health check", error=str(e))
    
    async def collect_metrics(self):
        """
        Collect current metrics
        """
        now = datetime.utcnow()
        
        # Workflow metrics
        workflow_metrics = await self._collect_workflow_metrics(now)
        
        # Task metrics
        task_metrics = await self._collect_task_metrics(now)
        
        # Performance metrics
        performance_metrics = await self._collect_performance_metrics(now)
        
        # Store metrics in Redis
        if self.redis:
            metrics = {
                "timestamp": now.isoformat(),
                "workflows": workflow_metrics,
                "tasks": task_metrics,
                "performance": performance_metrics
            }
            
            key = f"{self.metrics_prefix}{now.strftime('%Y%m%d%H%M')}"
            await self.redis.setex(key, 86400, json.dumps(metrics))  # Keep for 24 hours
        
        # Check for alerts
        await self._check_alerts(workflow_metrics, task_metrics, performance_metrics)
        
        logger.debug(
            "Metrics collected",
            workflows=workflow_metrics,
            tasks=task_metrics,
            performance=performance_metrics
        )
    
    async def _collect_workflow_metrics(self, now: datetime) -> Dict[str, Any]:
        """
        Collect workflow execution metrics
        """
        # Get counts by status
        status_counts = {}
        for status in WorkflowStatus:
            count = (await self.db.execute(
                select(func.count()).select_from(WorkflowInstanceDB)
                .where(WorkflowInstanceDB.status == status)
            )).scalar()
            status_counts[status.value] = count
        
        # Get execution rate (last hour)
        hour_ago = now - timedelta(hours=1)
        executions_last_hour = (await self.db.execute(
            select(func.count()).select_from(WorkflowInstanceDB)
            .where(WorkflowInstanceDB.created_at >= hour_ago)
        )).scalar()
        
        # Get average duration for completed workflows
        avg_duration_result = await self.db.execute(
            select(func.avg(
                func.extract('epoch', WorkflowInstanceDB.completed_at) -
                func.extract('epoch', WorkflowInstanceDB.started_at)
            )).where(
                WorkflowInstanceDB.status == WorkflowStatus.COMPLETED,
                WorkflowInstanceDB.completed_at.isnot(None),
                WorkflowInstanceDB.started_at.isnot(None)
            )
        )
        avg_duration = avg_duration_result.scalar() or 0
        
        # Get failure rate
        total_completed = status_counts.get(WorkflowStatus.COMPLETED.value, 0) + \
                         status_counts.get(WorkflowStatus.FAILED.value, 0)
        failure_rate = 0
        if total_completed > 0:
            failure_rate = status_counts.get(WorkflowStatus.FAILED.value, 0) / total_completed
        
        return {
            "status_counts": status_counts,
            "executions_per_hour": executions_last_hour,
            "average_duration_seconds": avg_duration,
            "failure_rate": failure_rate,
            "currently_running": status_counts.get(WorkflowStatus.RUNNING.value, 0),
            "queued": status_counts.get(WorkflowStatus.PENDING.value, 0) + 
                     status_counts.get(WorkflowStatus.SCHEDULED.value, 0)
        }
    
    async def _collect_task_metrics(self, now: datetime) -> Dict[str, Any]:
        """
        Collect task execution metrics
        """
        # Get counts by status
        task_status_counts = {}
        for status in TaskStatus:
            count = (await self.db.execute(
                select(func.count()).select_from(TaskInstanceDB)
                .where(TaskInstanceDB.status == status)
            )).scalar()
            task_status_counts[status.value] = count
        
        # Get task type distribution
        task_type_result = await self.db.execute(
            select(
                TaskInstanceDB.task_type,
                func.count().label("count")
            ).group_by(TaskInstanceDB.task_type)
        )
        task_type_counts = {
            row.task_type.value: row.count
            for row in task_type_result
        }
        
        # Get average task duration by type
        avg_duration_by_type = {}
        for task_type in task_type_counts.keys():
            avg_result = await self.db.execute(
                select(func.avg(TaskInstanceDB.duration_seconds))
                .where(
                    TaskInstanceDB.task_type == task_type,
                    TaskInstanceDB.status == TaskStatus.COMPLETED,
                    TaskInstanceDB.duration_seconds.isnot(None)
                )
            )
            avg_duration_by_type[task_type] = avg_result.scalar() or 0
        
        return {
            "status_counts": task_status_counts,
            "type_distribution": task_type_counts,
            "average_duration_by_type": avg_duration_by_type,
            "currently_executing": task_status_counts.get(TaskStatus.RUNNING.value, 0),
            "failed_tasks": task_status_counts.get(TaskStatus.FAILED.value, 0)
        }
    
    async def _collect_performance_metrics(self, now: datetime) -> Dict[str, Any]:
        """
        Collect performance metrics
        """
        # Get long-running workflows
        long_running_threshold = 3600  # 1 hour
        long_running_count = (await self.db.execute(
            select(func.count()).select_from(WorkflowInstanceDB)
            .where(
                WorkflowInstanceDB.status == WorkflowStatus.RUNNING,
                WorkflowInstanceDB.started_at < now - timedelta(seconds=long_running_threshold)
            )
        )).scalar()
        
        # Get stuck workflows (pending for too long)
        stuck_threshold = 1800  # 30 minutes
        stuck_count = (await self.db.execute(
            select(func.count()).select_from(WorkflowInstanceDB)
            .where(
                WorkflowInstanceDB.status == WorkflowStatus.PENDING,
                WorkflowInstanceDB.created_at < now - timedelta(seconds=stuck_threshold)
            )
        )).scalar()
        
        # Get retry rates
        total_tasks = (await self.db.execute(
            select(func.count()).select_from(TaskInstanceDB)
        )).scalar()
        
        retried_tasks = (await self.db.execute(
            select(func.count()).select_from(TaskInstanceDB)
            .where(TaskInstanceDB.retry_count > 0)
        )).scalar()
        
        retry_rate = 0
        if total_tasks > 0:
            retry_rate = retried_tasks / total_tasks
        
        return {
            "long_running_workflows": long_running_count,
            "stuck_workflows": stuck_count,
            "task_retry_rate": retry_rate,
            "total_retried_tasks": retried_tasks
        }
    
    async def _check_alerts(
        self,
        workflow_metrics: Dict[str, Any],
        task_metrics: Dict[str, Any],
        performance_metrics: Dict[str, Any]
    ):
        """
        Check for alert conditions
        """
        alerts = []
        
        # High failure rate alert
        if workflow_metrics["failure_rate"] > 0.2:  # 20% failure rate
            alerts.append({
                "level": "warning",
                "type": "high_failure_rate",
                "message": f"High workflow failure rate: {workflow_metrics['failure_rate']:.2%}",
                "value": workflow_metrics["failure_rate"]
            })
        
        # Too many queued workflows
        if workflow_metrics["queued"] > 100:
            alerts.append({
                "level": "warning",
                "type": "high_queue_size",
                "message": f"High number of queued workflows: {workflow_metrics['queued']}",
                "value": workflow_metrics["queued"]
            })
        
        # Long-running workflows
        if performance_metrics["long_running_workflows"] > 10:
            alerts.append({
                "level": "warning",
                "type": "long_running_workflows",
                "message": f"Multiple long-running workflows: {performance_metrics['long_running_workflows']}",
                "value": performance_metrics["long_running_workflows"]
            })
        
        # Stuck workflows
        if performance_metrics["stuck_workflows"] > 0:
            alerts.append({
                "level": "error",
                "type": "stuck_workflows",
                "message": f"Workflows stuck in pending state: {performance_metrics['stuck_workflows']}",
                "value": performance_metrics["stuck_workflows"]
            })
        
        # Send alerts
        if alerts and self.redis:
            for alert in alerts:
                await self.redis.publish(
                    self.alerts_channel,
                    json.dumps({
                        "timestamp": datetime.utcnow().isoformat(),
                        **alert
                    })
                )
                
                logger.warning(
                    "Alert triggered",
                    alert_type=alert["type"],
                    message=alert["message"]
                )
    
    async def check_health(self) -> Dict[str, Any]:
        """
        Perform health checks
        """
        health_status = {
            "status": "healthy",
            "checks": {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Check database connectivity
        try:
            await self.db.execute(select(1))
            health_status["checks"]["database"] = "healthy"
        except Exception as e:
            health_status["checks"]["database"] = "unhealthy"
            health_status["status"] = "unhealthy"
            logger.error("Database health check failed", error=str(e))
        
        # Check Redis connectivity
        if self.redis:
            try:
                await self.redis.ping()
                health_status["checks"]["redis"] = "healthy"
            except Exception as e:
                health_status["checks"]["redis"] = "unhealthy"
                health_status["status"] = "degraded"
                logger.error("Redis health check failed", error=str(e))
        
        # Check for stuck workflows
        stuck_count = (await self.db.execute(
            select(func.count()).select_from(WorkflowInstanceDB)
            .where(
                WorkflowInstanceDB.status == WorkflowStatus.PENDING,
                WorkflowInstanceDB.created_at < datetime.utcnow() - timedelta(minutes=30)
            )
        )).scalar()
        
        if stuck_count > 0:
            health_status["checks"]["workflow_processing"] = "degraded"
            health_status["status"] = "degraded"
        else:
            health_status["checks"]["workflow_processing"] = "healthy"
        
        return health_status
    
    async def get_dashboard_metrics(self) -> Dict[str, Any]:
        """
        Get metrics for dashboard display
        """
        now = datetime.utcnow()
        
        # Collect all metrics
        workflow_metrics = await self._collect_workflow_metrics(now)
        task_metrics = await self._collect_task_metrics(now)
        performance_metrics = await self._collect_performance_metrics(now)
        
        # Get recent events
        recent_events = await self._get_recent_events(limit=10)
        
        # Get trending workflows
        trending_workflows = await self._get_trending_workflows()
        
        return {
            "summary": {
                "total_workflows": sum(workflow_metrics["status_counts"].values()),
                "running_workflows": workflow_metrics["currently_running"],
                "queued_workflows": workflow_metrics["queued"],
                "failed_workflows": workflow_metrics["status_counts"].get(WorkflowStatus.FAILED.value, 0),
                "success_rate": 1 - workflow_metrics["failure_rate"],
                "average_duration": workflow_metrics["average_duration_seconds"]
            },
            "workflows": workflow_metrics,
            "tasks": task_metrics,
            "performance": performance_metrics,
            "recent_events": recent_events,
            "trending_workflows": trending_workflows,
            "timestamp": now.isoformat()
        }
    
    async def _get_recent_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent workflow events
        """
        result = await self.db.execute(
            select(WorkflowEventDB)
            .order_by(WorkflowEventDB.occurred_at.desc())
            .limit(limit)
        )
        events = result.scalars().all()
        
        return [
            {
                "workflow_instance_id": event.workflow_instance_id,
                "event_type": event.event_type,
                "event_data": event.event_data,
                "occurred_at": event.occurred_at.isoformat()
            }
            for event in events
        ]
    
    async def _get_trending_workflows(self) -> List[Dict[str, Any]]:
        """
        Get most frequently executed workflows
        """
        result = await self.db.execute(
            select(
                WorkflowInstanceDB.workflow_id,
                WorkflowInstanceDB.workflow_name,
                func.count().label("execution_count")
            )
            .where(
                WorkflowInstanceDB.created_at >= datetime.utcnow() - timedelta(days=7)
            )
            .group_by(
                WorkflowInstanceDB.workflow_id,
                WorkflowInstanceDB.workflow_name
            )
            .order_by(func.count().desc())
            .limit(5)
        )
        
        return [
            {
                "workflow_id": row.workflow_id,
                "workflow_name": row.workflow_name,
                "execution_count": row.execution_count
            }
            for row in result
        ]
    
    async def get_workflow_metrics(
        self,
        workflow_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get metrics for a specific workflow
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Get execution count
        execution_count = (await self.db.execute(
            select(func.count()).select_from(WorkflowInstanceDB)
            .where(
                WorkflowInstanceDB.workflow_id == workflow_id,
                WorkflowInstanceDB.created_at >= start_date,
                WorkflowInstanceDB.created_at <= end_date
            )
        )).scalar()
        
        # Get status distribution
        status_result = await self.db.execute(
            select(
                WorkflowInstanceDB.status,
                func.count().label("count")
            )
            .where(
                WorkflowInstanceDB.workflow_id == workflow_id,
                WorkflowInstanceDB.created_at >= start_date,
                WorkflowInstanceDB.created_at <= end_date
            )
            .group_by(WorkflowInstanceDB.status)
        )
        status_distribution = {
            row.status.value: row.count
            for row in status_result
        }
        
        # Get average duration
        avg_duration_result = await self.db.execute(
            select(func.avg(
                func.extract('epoch', WorkflowInstanceDB.completed_at) -
                func.extract('epoch', WorkflowInstanceDB.started_at)
            )).where(
                WorkflowInstanceDB.workflow_id == workflow_id,
                WorkflowInstanceDB.status == WorkflowStatus.COMPLETED,
                WorkflowInstanceDB.created_at >= start_date,
                WorkflowInstanceDB.created_at <= end_date
            )
        )
        avg_duration = avg_duration_result.scalar() or 0
        
        # Calculate success rate
        completed = status_distribution.get(WorkflowStatus.COMPLETED.value, 0)
        failed = status_distribution.get(WorkflowStatus.FAILED.value, 0)
        total_finished = completed + failed
        success_rate = completed / total_finished if total_finished > 0 else 0
        
        return {
            "workflow_id": workflow_id,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "execution_count": execution_count,
            "status_distribution": status_distribution,
            "average_duration_seconds": avg_duration,
            "success_rate": success_rate
        }


# Import json at the top of the file
import json