"""
Prometheus metrics configuration for MAMS monitoring
"""

from prometheus_client import (
    Counter, Histogram, Gauge, Summary, Info,
    CollectorRegistry, generate_latest
)
from functools import wraps
import time
from typing import Callable, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Create a custom registry for MAMS metrics
REGISTRY = CollectorRegistry()

# System-wide metrics
system_info = Info(
    'mams_system_info',
    'MAMS system information',
    ['service', 'version', 'environment'],
    registry=REGISTRY
)

# Service health metrics
service_health = Gauge(
    'mams_service_health',
    'Service health status (1=healthy, 0=unhealthy)',
    ['service'],
    registry=REGISTRY
)

service_uptime = Gauge(
    'mams_service_uptime_seconds',
    'Service uptime in seconds',
    ['service'],
    registry=REGISTRY
)

# Request metrics
http_requests_total = Counter(
    'mams_http_requests_total',
    'Total HTTP requests',
    ['service', 'method', 'endpoint', 'status'],
    registry=REGISTRY
)

http_request_duration = Histogram(
    'mams_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['service', 'method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=REGISTRY
)

http_request_size = Summary(
    'mams_http_request_size_bytes',
    'HTTP request size in bytes',
    ['service', 'method', 'endpoint'],
    registry=REGISTRY
)

http_response_size = Summary(
    'mams_http_response_size_bytes',
    'HTTP response size in bytes',
    ['service', 'method', 'endpoint'],
    registry=REGISTRY
)

# Asset management metrics
assets_total = Gauge(
    'mams_assets_total',
    'Total number of assets',
    ['type', 'status'],
    registry=REGISTRY
)

asset_uploads_total = Counter(
    'mams_asset_uploads_total',
    'Total asset uploads',
    ['service', 'type', 'status'],
    registry=REGISTRY
)

asset_upload_duration = Histogram(
    'mams_asset_upload_duration_seconds',
    'Asset upload duration in seconds',
    ['service', 'type'],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0, 1200.0),
    registry=REGISTRY
)

asset_storage_bytes = Gauge(
    'mams_asset_storage_bytes',
    'Total storage used in bytes',
    ['storage_tier', 'storage_type'],
    registry=REGISTRY
)

# Processing metrics
processing_queue_size = Gauge(
    'mams_processing_queue_size',
    'Number of items in processing queue',
    ['queue_name', 'priority'],
    registry=REGISTRY
)

processing_tasks_total = Counter(
    'mams_processing_tasks_total',
    'Total processing tasks',
    ['service', 'task_type', 'status'],
    registry=REGISTRY
)

processing_duration = Histogram(
    'mams_processing_duration_seconds',
    'Processing task duration in seconds',
    ['service', 'task_type'],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0, 1800.0, 3600.0),
    registry=REGISTRY
)

# Search metrics
search_queries_total = Counter(
    'mams_search_queries_total',
    'Total search queries',
    ['search_type', 'index'],
    registry=REGISTRY
)

search_query_duration = Histogram(
    'mams_search_query_duration_seconds',
    'Search query duration in seconds',
    ['search_type', 'index'],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    registry=REGISTRY
)

search_results_count = Histogram(
    'mams_search_results_count',
    'Number of search results returned',
    ['search_type', 'index'],
    buckets=(0, 1, 5, 10, 25, 50, 100, 250, 500, 1000),
    registry=REGISTRY
)

# Workflow metrics
workflow_executions_total = Counter(
    'mams_workflow_executions_total',
    'Total workflow executions',
    ['workflow_type', 'status'],
    registry=REGISTRY
)

workflow_execution_duration = Histogram(
    'mams_workflow_execution_duration_seconds',
    'Workflow execution duration in seconds',
    ['workflow_type'],
    buckets=(1.0, 10.0, 60.0, 300.0, 600.0, 1800.0, 3600.0, 7200.0),
    registry=REGISTRY
)

workflow_active_instances = Gauge(
    'mams_workflow_active_instances',
    'Number of active workflow instances',
    ['workflow_type'],
    registry=REGISTRY
)

# Database metrics
db_connections_active = Gauge(
    'mams_db_connections_active',
    'Active database connections',
    ['service', 'database'],
    registry=REGISTRY
)

db_query_duration = Histogram(
    'mams_db_query_duration_seconds',
    'Database query duration in seconds',
    ['service', 'database', 'operation'],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0),
    registry=REGISTRY
)

db_transaction_total = Counter(
    'mams_db_transaction_total',
    'Total database transactions',
    ['service', 'database', 'status'],
    registry=REGISTRY
)

# Cache metrics
cache_hits_total = Counter(
    'mams_cache_hits_total',
    'Total cache hits',
    ['service', 'cache_name'],
    registry=REGISTRY
)

cache_misses_total = Counter(
    'mams_cache_misses_total',
    'Total cache misses',
    ['service', 'cache_name'],
    registry=REGISTRY
)

cache_evictions_total = Counter(
    'mams_cache_evictions_total',
    'Total cache evictions',
    ['service', 'cache_name', 'reason'],
    registry=REGISTRY
)

cache_size_bytes = Gauge(
    'mams_cache_size_bytes',
    'Cache size in bytes',
    ['service', 'cache_name'],
    registry=REGISTRY
)

# Authentication metrics
auth_attempts_total = Counter(
    'mams_auth_attempts_total',
    'Total authentication attempts',
    ['method', 'status'],
    registry=REGISTRY
)

auth_token_generations_total = Counter(
    'mams_auth_token_generations_total',
    'Total auth token generations',
    ['token_type'],
    registry=REGISTRY
)

active_sessions = Gauge(
    'mams_active_sessions',
    'Number of active user sessions',
    ['session_type'],
    registry=REGISTRY
)

# Error metrics
errors_total = Counter(
    'mams_errors_total',
    'Total errors',
    ['service', 'error_type', 'severity'],
    registry=REGISTRY
)

# Business metrics
users_total = Gauge(
    'mams_users_total',
    'Total number of users',
    ['status', 'type'],
    registry=REGISTRY
)

projects_total = Gauge(
    'mams_projects_total',
    'Total number of projects',
    ['status'],
    registry=REGISTRY
)

storage_quota_usage = Gauge(
    'mams_storage_quota_usage_ratio',
    'Storage quota usage ratio (0-1)',
    ['user_id', 'project_id'],
    registry=REGISTRY
)


class MetricsCollector:
    """Metrics collector for services"""
    
    def __init__(self, service_name: str, version: str = "1.0.0", environment: str = "production"):
        self.service_name = service_name
        self.version = version
        self.environment = environment
        self.start_time = time.time()
        
        # Set system info
        system_info.labels(
            service=service_name,
            version=version,
            environment=environment
        ).info({
            'service': service_name,
            'version': version,
            'environment': environment
        })
        
        # Initialize service health
        service_health.labels(service=service_name).set(1)
    
    def track_request(self, method: str, endpoint: str, status: int, duration: float, 
                     request_size: int = 0, response_size: int = 0):
        """Track HTTP request metrics"""
        http_requests_total.labels(
            service=self.service_name,
            method=method,
            endpoint=endpoint,
            status=str(status)
        ).inc()
        
        http_request_duration.labels(
            service=self.service_name,
            method=method,
            endpoint=endpoint
        ).observe(duration)
        
        if request_size > 0:
            http_request_size.labels(
                service=self.service_name,
                method=method,
                endpoint=endpoint
            ).observe(request_size)
        
        if response_size > 0:
            http_response_size.labels(
                service=self.service_name,
                method=method,
                endpoint=endpoint
            ).observe(response_size)
    
    def track_asset_upload(self, asset_type: str, status: str, duration: float):
        """Track asset upload metrics"""
        asset_uploads_total.labels(
            service=self.service_name,
            type=asset_type,
            status=status
        ).inc()
        
        if status == "success":
            asset_upload_duration.labels(
                service=self.service_name,
                type=asset_type
            ).observe(duration)
    
    def track_processing_task(self, task_type: str, status: str, duration: float = None):
        """Track processing task metrics"""
        processing_tasks_total.labels(
            service=self.service_name,
            task_type=task_type,
            status=status
        ).inc()
        
        if duration and status == "success":
            processing_duration.labels(
                service=self.service_name,
                task_type=task_type
            ).observe(duration)
    
    def track_search_query(self, search_type: str, index: str, duration: float, result_count: int):
        """Track search query metrics"""
        search_queries_total.labels(
            search_type=search_type,
            index=index
        ).inc()
        
        search_query_duration.labels(
            search_type=search_type,
            index=index
        ).observe(duration)
        
        search_results_count.labels(
            search_type=search_type,
            index=index
        ).observe(result_count)
    
    def track_workflow_execution(self, workflow_type: str, status: str, duration: float = None):
        """Track workflow execution metrics"""
        workflow_executions_total.labels(
            workflow_type=workflow_type,
            status=status
        ).inc()
        
        if duration and status in ["completed", "failed"]:
            workflow_execution_duration.labels(
                workflow_type=workflow_type
            ).observe(duration)
    
    def track_db_query(self, database: str, operation: str, duration: float):
        """Track database query metrics"""
        db_query_duration.labels(
            service=self.service_name,
            database=database,
            operation=operation
        ).observe(duration)
    
    def track_cache_operation(self, cache_name: str, hit: bool):
        """Track cache operation metrics"""
        if hit:
            cache_hits_total.labels(
                service=self.service_name,
                cache_name=cache_name
            ).inc()
        else:
            cache_misses_total.labels(
                service=self.service_name,
                cache_name=cache_name
            ).inc()
    
    def track_auth_attempt(self, method: str, success: bool):
        """Track authentication attempt"""
        auth_attempts_total.labels(
            method=method,
            status="success" if success else "failure"
        ).inc()
    
    def track_error(self, error_type: str, severity: str = "error"):
        """Track error occurrence"""
        errors_total.labels(
            service=self.service_name,
            error_type=error_type,
            severity=severity
        ).inc()
    
    def update_service_health(self, is_healthy: bool):
        """Update service health status"""
        service_health.labels(service=self.service_name).set(1 if is_healthy else 0)
    
    def update_uptime(self):
        """Update service uptime"""
        uptime = time.time() - self.start_time
        service_uptime.labels(service=self.service_name).set(uptime)
    
    def set_queue_size(self, queue_name: str, size: int, priority: str = "normal"):
        """Set processing queue size"""
        processing_queue_size.labels(
            queue_name=queue_name,
            priority=priority
        ).set(size)
    
    def set_active_workflows(self, workflow_type: str, count: int):
        """Set active workflow instances"""
        workflow_active_instances.labels(
            workflow_type=workflow_type
        ).set(count)
    
    def set_db_connections(self, database: str, count: int):
        """Set active database connections"""
        db_connections_active.labels(
            service=self.service_name,
            database=database
        ).set(count)
    
    def set_cache_size(self, cache_name: str, size_bytes: int):
        """Set cache size in bytes"""
        cache_size_bytes.labels(
            service=self.service_name,
            cache_name=cache_name
        ).set(size_bytes)
    
    def set_active_sessions(self, session_type: str, count: int):
        """Set active user sessions"""
        active_sessions.labels(
            session_type=session_type
        ).set(count)


def track_time(metric_func: Callable) -> Callable:
    """Decorator to track function execution time"""
    @wraps(metric_func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = metric_func(*args, **kwargs)
            duration = time.time() - start_time
            # Log success
            logger.debug(f"{metric_func.__name__} completed in {duration:.3f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            # Log failure
            logger.error(f"{metric_func.__name__} failed after {duration:.3f}s: {e}")
            raise
    return wrapper


def get_metrics() -> bytes:
    """Get current metrics in Prometheus format"""
    return generate_latest(REGISTRY)