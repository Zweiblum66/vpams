"""
Comprehensive performance monitoring service for MAMS.

Tracks application performance, user experience metrics,
system health, and provides real-time alerting.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
from dataclasses import dataclass, asdict
from enum import Enum
import statistics
import psutil
import aioredis
from sqlalchemy.ext.asyncio import AsyncSession
from prometheus_client import (
    Counter, Histogram, Gauge, CollectorRegistry,
    generate_latest, CONTENT_TYPE_LATEST
)
import httpx

logger = logging.getLogger(__name__)


class MetricType(Enum):
    COUNTER = "counter"
    HISTOGRAM = "histogram" 
    GAUGE = "gauge"
    SUMMARY = "summary"


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class PerformanceMetric:
    """Individual performance metric data point."""
    name: str
    value: float
    timestamp: datetime
    labels: Dict[str, str] = None
    metric_type: MetricType = MetricType.GAUGE
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'labels': self.labels or {},
            'type': self.metric_type.value
        }


@dataclass
class Alert:
    """Performance alert."""
    id: str
    title: str
    description: str
    severity: AlertSeverity
    metric_name: str
    threshold_value: float
    current_value: float
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'severity': self.severity.value,
            'metric_name': self.metric_name,
            'threshold_value': self.threshold_value,
            'current_value': self.current_value,
            'timestamp': self.timestamp.isoformat(),
            'resolved': self.resolved,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }


class MetricsCollector:
    """Collects and manages performance metrics."""
    
    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client
        self.registry = CollectorRegistry()
        self.metrics = {}
        self._setup_metrics()
        
    def _setup_metrics(self):
        """Initialize Prometheus metrics."""
        # Request metrics
        self.request_count = Counter(
            'mams_requests_total',
            'Total number of requests',
            ['service', 'endpoint', 'method', 'status'],
            registry=self.registry
        )
        
        self.request_duration = Histogram(
            'mams_request_duration_seconds',
            'Request duration in seconds',
            ['service', 'endpoint', 'method'],
            registry=self.registry
        )
        
        # Database metrics
        self.db_query_duration = Histogram(
            'mams_db_query_duration_seconds',
            'Database query duration in seconds',
            ['service', 'query_type'],
            registry=self.registry
        )
        
        self.db_connection_pool = Gauge(
            'mams_db_connections',
            'Database connection pool status',
            ['service', 'pool_name', 'status'],
            registry=self.registry
        )
        
        # Cache metrics
        self.cache_hits = Counter(
            'mams_cache_hits_total',
            'Cache hits',
            ['service', 'cache_type'],
            registry=self.registry
        )
        
        self.cache_misses = Counter(
            'mams_cache_misses_total',
            'Cache misses',
            ['service', 'cache_type'],
            registry=self.registry
        )
        
        # System metrics
        self.cpu_usage = Gauge(
            'mams_cpu_usage_percent',
            'CPU usage percentage',
            ['service'],
            registry=self.registry
        )
        
        self.memory_usage = Gauge(
            'mams_memory_usage_bytes',
            'Memory usage in bytes',
            ['service', 'type'],
            registry=self.registry
        )
        
        self.disk_usage = Gauge(
            'mams_disk_usage_bytes',
            'Disk usage in bytes',
            ['service', 'mount_point', 'type'],
            registry=self.registry
        )
        
        # Application metrics
        self.active_users = Gauge(
            'mams_active_users',
            'Number of active users',
            ['service'],
            registry=self.registry
        )
        
        self.upload_queue = Gauge(
            'mams_upload_queue_size',
            'Upload queue size',
            ['service'],
            registry=self.registry
        )
        
        self.processing_queue = Gauge(
            'mams_processing_queue_size',
            'Processing queue size',
            ['service', 'queue_type'],
            registry=self.registry
        )
        
        # Error metrics
        self.error_count = Counter(
            'mams_errors_total',
            'Total number of errors',
            ['service', 'error_type', 'severity'],
            registry=self.registry
        )
        
        # Business metrics
        self.assets_uploaded = Counter(
            'mams_assets_uploaded_total',
            'Total assets uploaded',
            ['service', 'asset_type'],
            registry=self.registry
        )
        
        self.storage_used = Gauge(
            'mams_storage_used_bytes',
            'Storage used in bytes',
            ['service', 'storage_type'],
            registry=self.registry
        )
        
    async def record_request(
        self,
        service: str,
        endpoint: str,
        method: str,
        status_code: int,
        duration: float
    ):
        """Record HTTP request metrics."""
        self.request_count.labels(
            service=service,
            endpoint=endpoint,
            method=method,
            status=str(status_code)
        ).inc()
        
        self.request_duration.labels(
            service=service,
            endpoint=endpoint,
            method=method
        ).observe(duration)
        
        # Store in Redis for real-time monitoring
        await self.redis.lpush(
            f'metrics:requests:{service}',
            json.dumps({
                'endpoint': endpoint,
                'method': method,
                'status': status_code,
                'duration': duration,
                'timestamp': datetime.utcnow().isoformat()
            })
        )
        await self.redis.ltrim(f'metrics:requests:{service}', 0, 999)  # Keep last 1000
        
    async def record_db_query(
        self,
        service: str,
        query_type: str,
        duration: float
    ):
        """Record database query metrics."""
        self.db_query_duration.labels(
            service=service,
            query_type=query_type
        ).observe(duration)
        
    async def record_cache_hit(self, service: str, cache_type: str):
        """Record cache hit."""
        self.cache_hits.labels(
            service=service,
            cache_type=cache_type
        ).inc()
        
    async def record_cache_miss(self, service: str, cache_type: str):
        """Record cache miss."""
        self.cache_misses.labels(
            service=service,
            cache_type=cache_type
        ).inc()
        
    async def update_system_metrics(self, service: str):
        """Update system resource metrics."""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        self.cpu_usage.labels(service=service).set(cpu_percent)
        
        # Memory usage
        memory = psutil.virtual_memory()
        self.memory_usage.labels(service=service, type='used').set(memory.used)
        self.memory_usage.labels(service=service, type='available').set(memory.available)
        
        # Disk usage
        for disk in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(disk.mountpoint)
                self.disk_usage.labels(
                    service=service,
                    mount_point=disk.mountpoint,
                    type='used'
                ).set(usage.used)
                self.disk_usage.labels(
                    service=service,
                    mount_point=disk.mountpoint,
                    type='free'
                ).set(usage.free)
            except (OSError, PermissionError):
                continue
                
    async def record_error(
        self,
        service: str,
        error_type: str,
        severity: str,
        details: Optional[Dict] = None
    ):
        """Record application error."""
        self.error_count.labels(
            service=service,
            error_type=error_type,
            severity=severity
        ).inc()
        
        # Store error details in Redis
        error_data = {
            'service': service,
            'error_type': error_type,
            'severity': severity,
            'details': details or {},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await self.redis.lpush(
            f'errors:{service}',
            json.dumps(error_data)
        )
        await self.redis.ltrim(f'errors:{service}', 0, 499)  # Keep last 500
        
    def get_prometheus_metrics(self) -> str:
        """Get metrics in Prometheus format."""
        return generate_latest(self.registry)


class PerformanceMonitor:
    """Main performance monitoring service."""
    
    def __init__(
        self,
        redis_url: str,
        alert_webhook_url: Optional[str] = None,
        check_interval: int = 30
    ):
        self.redis_url = redis_url
        self.alert_webhook_url = alert_webhook_url
        self.check_interval = check_interval
        self.redis: Optional[aioredis.Redis] = None
        self.metrics_collector: Optional[MetricsCollector] = None
        self.alerts: Dict[str, Alert] = {}
        self.thresholds = self._default_thresholds()
        self.running = False
        
    def _default_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Default performance thresholds."""
        return {
            'response_time': {
                'warning': 1.0,    # 1 second
                'critical': 5.0    # 5 seconds
            },
            'error_rate': {
                'warning': 0.05,   # 5%
                'critical': 0.10   # 10%
            },
            'cpu_usage': {
                'warning': 80.0,   # 80%
                'critical': 95.0   # 95%
            },
            'memory_usage': {
                'warning': 80.0,   # 80%
                'critical': 95.0   # 95%
            },
            'disk_usage': {
                'warning': 85.0,   # 85%
                'critical': 95.0   # 95%
            },
            'queue_size': {
                'warning': 1000,   # 1000 items
                'critical': 5000   # 5000 items
            }
        }
        
    async def start(self):
        """Start the performance monitoring service."""
        self.redis = aioredis.from_url(self.redis_url)
        self.metrics_collector = MetricsCollector(self.redis)
        self.running = True
        
        # Start monitoring tasks
        asyncio.create_task(self._monitoring_loop())
        asyncio.create_task(self._alert_check_loop())
        
        logger.info("Performance monitoring started")
        
    async def stop(self):
        """Stop the performance monitoring service."""
        self.running = False
        if self.redis:
            await self.redis.close()
        logger.info("Performance monitoring stopped")
        
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                await self._collect_system_metrics()
                await self._collect_application_metrics()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)
                
    async def _alert_check_loop(self):
        """Alert checking loop."""
        while self.running:
            try:
                await self._check_thresholds()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in alert check loop: {e}")
                await asyncio.sleep(5)
                
    async def _collect_system_metrics(self):
        """Collect system-level metrics."""
        service_name = "system"
        
        if self.metrics_collector:
            await self.metrics_collector.update_system_metrics(service_name)
            
    async def _collect_application_metrics(self):
        """Collect application-specific metrics."""
        # This would typically query each service for metrics
        services = ['api-gateway', 'asset-management', 'user-management']
        
        for service in services:
            try:
                # Query service health endpoint
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"http://{service}:8000/health",
                        timeout=5.0
                    )
                    
                    if response.status_code == 200:
                        health_data = response.json()
                        await self._process_health_data(service, health_data)
                    else:
                        await self.metrics_collector.record_error(
                            service, "health_check_failed", "warning"
                        )
                        
            except Exception as e:
                logger.warning(f"Failed to collect metrics from {service}: {e}")
                
    async def _process_health_data(self, service: str, health_data: Dict):
        """Process health data from a service."""
        if not self.metrics_collector:
            return
            
        # Update metrics based on health data
        if 'active_connections' in health_data:
            await self.redis.set(
                f'metrics:{service}:connections',
                health_data['active_connections']
            )
            
        if 'queue_sizes' in health_data:
            for queue_name, size in health_data['queue_sizes'].items():
                self.metrics_collector.processing_queue.labels(
                    service=service,
                    queue_type=queue_name
                ).set(size)
                
        if 'cache_stats' in health_data:
            stats = health_data['cache_stats']
            if 'hit_rate' in stats:
                await self.redis.set(
                    f'metrics:{service}:cache_hit_rate',
                    stats['hit_rate']
                )
                
    async def _check_thresholds(self):
        """Check metrics against thresholds and generate alerts."""
        # Check response time
        await self._check_response_time_threshold()
        
        # Check error rate
        await self._check_error_rate_threshold()
        
        # Check system resources
        await self._check_system_resource_thresholds()
        
        # Check queue sizes
        await self._check_queue_size_thresholds()
        
    async def _check_response_time_threshold(self):
        """Check response time thresholds."""
        services = await self.redis.keys('metrics:requests:*')
        
        for service_key in services:
            service_name = service_key.decode().split(':')[-1]
            requests = await self.redis.lrange(service_key, 0, 99)  # Last 100 requests
            
            if not requests:
                continue
                
            durations = []
            for request_json in requests:
                request_data = json.loads(request_json)
                durations.append(request_data['duration'])
                
            if durations:
                avg_duration = statistics.mean(durations)
                p95_duration = statistics.quantiles(durations, n=20)[18]  # 95th percentile
                
                await self._check_threshold(
                    f"{service_name}_response_time",
                    "Response Time",
                    p95_duration,
                    self.thresholds['response_time'],
                    f"95th percentile response time for {service_name}"
                )
                
    async def _check_error_rate_threshold(self):
        """Check error rate thresholds."""
        services = await self.redis.keys('metrics:requests:*')
        
        for service_key in services:
            service_name = service_key.decode().split(':')[-1]
            requests = await self.redis.lrange(service_key, 0, 999)  # Last 1000 requests
            
            if len(requests) < 10:  # Need minimum requests for meaningful rate
                continue
                
            error_count = 0
            total_count = len(requests)
            
            for request_json in requests:
                request_data = json.loads(request_json)
                if request_data['status'] >= 400:
                    error_count += 1
                    
            error_rate = error_count / total_count
            
            await self._check_threshold(
                f"{service_name}_error_rate",
                "Error Rate",
                error_rate,
                self.thresholds['error_rate'],
                f"Error rate for {service_name}"
            )
            
    async def _check_system_resource_thresholds(self):
        """Check system resource thresholds."""
        # CPU usage
        cpu_percent = psutil.cpu_percent()
        await self._check_threshold(
            "system_cpu_usage",
            "CPU Usage",
            cpu_percent,
            self.thresholds['cpu_usage'],
            "System CPU usage"
        )
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        await self._check_threshold(
            "system_memory_usage",
            "Memory Usage",
            memory_percent,
            self.thresholds['memory_usage'],
            "System memory usage"
        )
        
        # Disk usage
        for disk in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(disk.mountpoint)
                disk_percent = (usage.used / usage.total) * 100
                await self._check_threshold(
                    f"disk_usage_{disk.mountpoint.replace('/', '_')}",
                    f"Disk Usage ({disk.mountpoint})",
                    disk_percent,
                    self.thresholds['disk_usage'],
                    f"Disk usage for {disk.mountpoint}"
                )
            except (OSError, PermissionError):
                continue
                
    async def _check_queue_size_thresholds(self):
        """Check queue size thresholds."""
        queue_keys = await self.redis.keys('queue:*')
        
        for queue_key in queue_keys:
            queue_size = await self.redis.llen(queue_key)
            queue_name = queue_key.decode().split(':')[-1]
            
            await self._check_threshold(
                f"queue_size_{queue_name}",
                f"Queue Size ({queue_name})",
                queue_size,
                self.thresholds['queue_size'],
                f"Queue size for {queue_name}"
            )
            
    async def _check_threshold(
        self,
        metric_id: str,
        metric_name: str,
        current_value: float,
        thresholds: Dict[str, float],
        description: str
    ):
        """Check a metric against its thresholds."""
        severity = None
        
        if current_value >= thresholds['critical']:
            severity = AlertSeverity.CRITICAL
        elif current_value >= thresholds['warning']:
            severity = AlertSeverity.WARNING
            
        if severity:
            # Create or update alert
            alert_id = f"{metric_id}_{severity.value}"
            
            if alert_id not in self.alerts:
                alert = Alert(
                    id=alert_id,
                    title=f"{metric_name} {severity.value.title()}",
                    description=f"{description}: {current_value:.2f}",
                    severity=severity,
                    metric_name=metric_name,
                    threshold_value=thresholds[severity.value],
                    current_value=current_value,
                    timestamp=datetime.utcnow()
                )
                
                self.alerts[alert_id] = alert
                await self._send_alert(alert)
                
        else:
            # Check if we can resolve existing alerts
            for alert_id in list(self.alerts.keys()):
                if alert_id.startswith(metric_id) and not self.alerts[alert_id].resolved:
                    alert = self.alerts[alert_id]
                    alert.resolved = True
                    alert.resolved_at = datetime.utcnow()
                    await self._send_alert_resolution(alert)
                    
    async def _send_alert(self, alert: Alert):
        """Send alert notification."""
        logger.warning(f"ALERT: {alert.title} - {alert.description}")
        
        # Store alert in Redis
        await self.redis.lpush(
            'alerts:active',
            json.dumps(alert.to_dict())
        )
        
        # Send webhook notification
        if self.alert_webhook_url:
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        self.alert_webhook_url,
                        json=alert.to_dict(),
                        timeout=10.0
                    )
            except Exception as e:
                logger.error(f"Failed to send alert webhook: {e}")
                
    async def _send_alert_resolution(self, alert: Alert):
        """Send alert resolution notification."""
        logger.info(f"RESOLVED: {alert.title}")
        
        # Update alert in Redis
        await self.redis.lpush(
            'alerts:resolved',
            json.dumps(alert.to_dict())
        )
        
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for monitoring dashboard."""
        # Get recent metrics
        dashboard_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'services': {},
            'system': {},
            'alerts': [],
            'summary': {}
        }
        
        # System metrics
        dashboard_data['system'] = {
            'cpu_usage': psutil.cpu_percent(),
            'memory_usage': psutil.virtual_memory().percent,
            'disk_usage': {
                disk.mountpoint: (psutil.disk_usage(disk.mountpoint).used / 
                                psutil.disk_usage(disk.mountpoint).total * 100)
                for disk in psutil.disk_partitions()
                if disk.fstype and not disk.mountpoint.startswith('/sys')
            }
        }
        
        # Service metrics
        services = ['api-gateway', 'asset-management', 'user-management']
        for service in services:
            service_data = {}
            
            # Response times
            requests_key = f'metrics:requests:{service}'
            requests = await self.redis.lrange(requests_key, 0, 99)
            if requests:
                durations = [json.loads(r)['duration'] for r in requests]
                service_data['avg_response_time'] = statistics.mean(durations)
                service_data['p95_response_time'] = statistics.quantiles(durations, n=20)[18]
                
                # Error rate
                errors = sum(1 for r in requests if json.loads(r)['status'] >= 400)
                service_data['error_rate'] = errors / len(requests)
                
            # Cache hit rate
            cache_hit_rate = await self.redis.get(f'metrics:{service}:cache_hit_rate')
            if cache_hit_rate:
                service_data['cache_hit_rate'] = float(cache_hit_rate)
                
            dashboard_data['services'][service] = service_data
            
        # Active alerts
        active_alerts = await self.redis.lrange('alerts:active', 0, 49)
        dashboard_data['alerts'] = [
            json.loads(alert) for alert in active_alerts
        ]
        
        # Summary statistics
        dashboard_data['summary'] = {
            'total_requests_last_hour': await self._count_recent_requests(3600),
            'active_alerts': len(dashboard_data['alerts']),
            'services_healthy': len([
                s for s in dashboard_data['services'].values()
                if s.get('error_rate', 0) < 0.05
            ]),
            'avg_response_time': statistics.mean([
                s.get('avg_response_time', 0)
                for s in dashboard_data['services'].values()
                if 'avg_response_time' in s
            ]) if dashboard_data['services'] else 0
        }
        
        return dashboard_data
        
    async def _count_recent_requests(self, seconds: int) -> int:
        """Count requests in the last N seconds."""
        cutoff_time = datetime.utcnow() - timedelta(seconds=seconds)
        total_requests = 0
        
        services = await self.redis.keys('metrics:requests:*')
        for service_key in services:
            requests = await self.redis.lrange(service_key, 0, -1)
            for request_json in requests:
                request_data = json.loads(request_json)
                request_time = datetime.fromisoformat(request_data['timestamp'])
                if request_time > cutoff_time:
                    total_requests += 1
                    
        return total_requests


# Example usage and integration
async def main():
    """Example of how to use the performance monitor."""
    monitor = PerformanceMonitor(
        redis_url="redis://localhost:6379",
        alert_webhook_url="https://hooks.slack.com/your-webhook-url",
        check_interval=30
    )
    
    await monitor.start()
    
    try:
        # Keep running
        while True:
            await asyncio.sleep(60)
            dashboard_data = await monitor.get_dashboard_data()
            print(f"Dashboard update: {dashboard_data['summary']}")
    except KeyboardInterrupt:
        pass
    finally:
        await monitor.stop()


if __name__ == "__main__":
    asyncio.run(main())