"""
Metrics Service for Workflow Engine

Provides Prometheus metrics for monitoring workflow execution
"""

from prometheus_client import Counter, Histogram, Gauge, Info
import time
from functools import wraps
from typing import Dict, Any

# Workflow metrics
workflow_created_total = Counter(
    'workflow_created_total',
    'Total number of workflows created',
    ['workflow_id', 'trigger_type']
)

workflow_executed_total = Counter(
    'workflow_executed_total', 
    'Total number of workflows executed',
    ['workflow_id', 'status']
)

workflow_duration_seconds = Histogram(
    'workflow_duration_seconds',
    'Workflow execution duration in seconds',
    ['workflow_id'],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600)
)

workflow_active_count = Gauge(
    'workflow_active_count',
    'Number of currently active workflows'
)

workflow_queue_size = Gauge(
    'workflow_queue_size',
    'Number of workflows in queue',
    ['priority']
)

# Task metrics
task_executed_total = Counter(
    'task_executed_total',
    'Total number of tasks executed',
    ['task_type', 'status']
)

task_duration_seconds = Histogram(
    'task_duration_seconds',
    'Task execution duration in seconds', 
    ['task_type'],
    buckets=(0.1, 0.5, 1, 2, 5, 10, 30, 60, 120, 300)
)

task_retry_total = Counter(
    'task_retry_total',
    'Total number of task retries',
    ['task_type']
)

# Approval metrics
approval_created_total = Counter(
    'approval_created_total',
    'Total number of approval requests created'
)

approval_decision_total = Counter(
    'approval_decision_total',
    'Total number of approval decisions',
    ['decision']
)

approval_response_time_seconds = Histogram(
    'approval_response_time_seconds',
    'Time taken to respond to approval requests',
    buckets=(3600, 7200, 14400, 28800, 86400, 172800, 604800)  # 1h to 7d
)

# Queue metrics
rabbitmq_queue_size = Gauge(
    'rabbitmq_queue_size',
    'RabbitMQ queue size',
    ['queue_name']
)

rabbitmq_messages_published_total = Counter(
    'rabbitmq_messages_published_total',
    'Total messages published to RabbitMQ',
    ['routing_key']
)

rabbitmq_messages_consumed_total = Counter(
    'rabbitmq_messages_consumed_total',
    'Total messages consumed from RabbitMQ',
    ['task_type', 'status']
)

# System info
system_info = Info(
    'workflow_engine_info',
    'Workflow engine system information'
)

# Initialize system info
system_info.info({
    'version': '1.0.0',
    'service': 'workflow-engine'
})


def track_workflow_execution(workflow_id: str):
    """
    Decorator to track workflow execution metrics
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            workflow_active_count.inc()
            
            try:
                result = await func(*args, **kwargs)
                status = result.status.value if hasattr(result, 'status') else 'unknown'
                workflow_executed_total.labels(
                    workflow_id=workflow_id,
                    status=status
                ).inc()
                return result
                
            except Exception as e:
                workflow_executed_total.labels(
                    workflow_id=workflow_id,
                    status='failed'
                ).inc()
                raise
                
            finally:
                duration = time.time() - start_time
                workflow_duration_seconds.labels(workflow_id=workflow_id).observe(duration)
                workflow_active_count.dec()
                
        return wrapper
    return decorator


def track_task_execution(task_type: str):
    """
    Decorator to track task execution metrics
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                task_executed_total.labels(
                    task_type=task_type,
                    status='success'
                ).inc()
                return result
                
            except Exception as e:
                task_executed_total.labels(
                    task_type=task_type,
                    status='failed'
                ).inc()
                raise
                
            finally:
                duration = time.time() - start_time
                task_duration_seconds.labels(task_type=task_type).observe(duration)
                
        return wrapper
    return decorator


class MetricsService:
    """
    Service for managing workflow metrics
    """
    
    @staticmethod
    def record_workflow_created(workflow_id: str, trigger_type: str):
        """Record workflow creation"""
        workflow_created_total.labels(
            workflow_id=workflow_id,
            trigger_type=trigger_type
        ).inc()
    
    @staticmethod
    def record_task_retry(task_type: str):
        """Record task retry"""
        task_retry_total.labels(task_type=task_type).inc()
    
    @staticmethod
    def record_approval_created():
        """Record approval request creation"""
        approval_created_total.inc()
    
    @staticmethod
    def record_approval_decision(decision: str):
        """Record approval decision"""
        approval_decision_total.labels(decision=decision).inc()
    
    @staticmethod
    def record_approval_response_time(seconds: float):
        """Record approval response time"""
        approval_response_time_seconds.observe(seconds)
    
    @staticmethod
    def update_queue_metrics(stats: Dict[str, Any]):
        """Update queue metrics"""
        if 'task_queue' in stats:
            rabbitmq_queue_size.labels(
                queue_name=stats['task_queue']['name']
            ).set(stats['task_queue']['messages'])
        
        if 'dead_letter_queue' in stats:
            rabbitmq_queue_size.labels(
                queue_name=stats['dead_letter_queue']['name']
            ).set(stats['dead_letter_queue']['messages'])
    
    @staticmethod
    def record_message_published(routing_key: str):
        """Record message published to RabbitMQ"""
        rabbitmq_messages_published_total.labels(routing_key=routing_key).inc()
    
    @staticmethod
    def record_message_consumed(task_type: str, success: bool = True):
        """Record message consumed from RabbitMQ"""
        status = 'success' if success else 'failed'
        rabbitmq_messages_consumed_total.labels(
            task_type=task_type,
            status=status
        ).inc()
    
    @staticmethod
    def update_workflow_queue_size(priority: str, size: int):
        """Update workflow queue size by priority"""
        workflow_queue_size.labels(priority=priority).set(size)