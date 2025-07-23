"""
Metrics collection for failover service
"""

from typing import Dict, Any, Optional
from datetime import datetime
import time
from contextlib import contextmanager
from prometheus_client import Counter, Histogram, Gauge, Summary
import structlog

logger = structlog.get_logger(__name__)


class MetricsCollector:
    """Collects and exposes metrics for failover service"""
    
    def __init__(self):
        # Failover metrics
        self.failover_total = Counter(
            'failover_total',
            'Total number of failover events',
            ['type', 'from_region', 'to_region', 'success']
        )
        
        self.failover_duration = Histogram(
            'failover_duration_seconds',
            'Failover duration in seconds',
            ['type', 'from_region', 'to_region']
        )
        
        # Health check metrics
        self.health_check_total = Counter(
            'failover_health_check_total',
            'Total number of health checks',
            ['region', 'service', 'status']
        )
        
        self.health_check_duration = Histogram(
            'failover_health_check_duration_seconds',
            'Health check duration in seconds',
            ['region', 'service']
        )
        
        # Region metrics
        self.region_status = Gauge(
            'failover_region_status',
            'Current region status (1=active, 0=standby, -1=failed)',
            ['region']
        )
        
        self.region_health_percentage = Gauge(
            'failover_region_health_percentage',
            'Region health percentage',
            ['region']
        )
        
        # Service metrics
        self.service_availability = Gauge(
            'failover_service_availability',
            'Service availability (1=available, 0=unavailable)',
            ['region', 'service']
        )
        
        self.service_response_time = Summary(
            'failover_service_response_time_ms',
            'Service response time in milliseconds',
            ['region', 'service']
        )
        
        # Replication metrics
        self.replication_lag = Gauge(
            'failover_replication_lag_seconds',
            'Replication lag in seconds',
            ['source_region', 'target_region', 'data_type']
        )
        
        self.rpo_status = Gauge(
            'failover_rpo_status',
            'RPO status (1=within RPO, 0=exceeded)',
            ['region']
        )
        
        # Data consistency metrics
        self.data_consistency = Gauge(
            'failover_data_consistency_percentage',
            'Data consistency percentage between regions',
            ['source_region', 'target_region']
        )
        
        self.consistency_check_duration = Histogram(
            'failover_consistency_check_duration_seconds',
            'Data consistency check duration',
            ['check_type']
        )
        
        # System metrics
        self.active_region = Gauge(
            'failover_active_region',
            'Currently active region (1=active, 0=inactive)',
            ['region']
        )
        
        self.failover_state = Gauge(
            'failover_system_state',
            'Current failover system state',
            []
        )
        
        # Performance metrics
        self.api_request_duration = Histogram(
            'failover_api_request_duration_seconds',
            'API request duration',
            ['method', 'endpoint', 'status']
        )
        
        self.api_request_total = Counter(
            'failover_api_request_total',
            'Total API requests',
            ['method', 'endpoint', 'status']
        )
        
        # Alert metrics
        self.alerts_sent = Counter(
            'failover_alerts_sent_total',
            'Total alerts sent',
            ['severity', 'channel']
        )
        
        # Custom metrics storage
        self._custom_metrics: Dict[str, Any] = {}
    
    def increment(self, metric: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric"""
        try:
            if metric == "failover.completed":
                self.failover_total.labels(**labels).inc(value)
            elif metric == "health_check":
                self.health_check_total.labels(**labels).inc(value)
            elif metric == "alerts":
                self.alerts_sent.labels(**labels).inc(value)
            elif metric == "api_requests":
                self.api_request_total.labels(**labels).inc(value)
            else:
                # Store custom metric
                if metric not in self._custom_metrics:
                    self._custom_metrics[metric] = Counter(
                        metric.replace(".", "_"),
                        f"Custom metric: {metric}"
                    )
                self._custom_metrics[metric].inc(value)
                
        except Exception as e:
            logger.error(f"Failed to increment metric {metric}: {e}")
    
    def gauge(self, metric: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric"""
        try:
            if metric == "failover.region.health":
                self.region_health_percentage.labels(**labels).set(value)
            elif metric == "failover.region.status":
                self.region_status.labels(**labels).set(value)
            elif metric == "service.availability":
                self.service_availability.labels(**labels).set(value)
            elif metric == "replication.lag":
                self.replication_lag.labels(**labels).set(value)
            elif metric == "rpo.status":
                self.rpo_status.labels(**labels).set(value)
            elif metric == "data.consistency":
                self.data_consistency.labels(**labels).set(value)
            elif metric == "active.region":
                self.active_region.labels(**labels).set(value)
            elif metric == "failover.state":
                self.failover_state.set(value)
            else:
                # Store custom metric
                if metric not in self._custom_metrics:
                    self._custom_metrics[metric] = Gauge(
                        metric.replace(".", "_"),
                        f"Custom metric: {metric}"
                    )
                self._custom_metrics[metric].set(value)
                
        except Exception as e:
            logger.error(f"Failed to set gauge metric {metric}: {e}")
    
    def observe(self, metric: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Observe a histogram/summary metric"""
        try:
            if metric == "failover.duration":
                self.failover_duration.labels(**labels).observe(value)
            elif metric == "health_check.duration":
                self.health_check_duration.labels(**labels).observe(value)
            elif metric == "service.response_time":
                self.service_response_time.labels(**labels).observe(value)
            elif metric == "consistency_check.duration":
                self.consistency_check_duration.labels(**labels).observe(value)
            elif metric == "api.request.duration":
                self.api_request_duration.labels(**labels).observe(value)
            else:
                # Store custom metric
                if metric not in self._custom_metrics:
                    self._custom_metrics[metric] = Histogram(
                        metric.replace(".", "_"),
                        f"Custom metric: {metric}"
                    )
                self._custom_metrics[metric].observe(value)
                
        except Exception as e:
            logger.error(f"Failed to observe metric {metric}: {e}")
    
    @contextmanager
    def timer(self, metric: str, labels: Optional[Dict[str, str]] = None):
        """Context manager for timing operations"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.observe(metric, duration, labels)
    
    def record_failover_event(
        self,
        event_type: str,
        from_region: str,
        to_region: str,
        duration: float,
        success: bool
    ):
        """Record a failover event with all metrics"""
        labels = {
            "type": event_type,
            "from_region": from_region,
            "to_region": to_region
        }
        
        # Record completion
        self.failover_total.labels(
            type=event_type,
            from_region=from_region,
            to_region=to_region,
            success=str(success).lower()
        ).inc()
        
        # Record duration
        self.failover_duration.labels(**labels).observe(duration)
        
        # Update region status
        self.active_region.labels(region=to_region).set(1)
        self.active_region.labels(region=from_region).set(0)
    
    def record_health_check(
        self,
        region: str,
        service: str,
        status: str,
        duration: float,
        response_time_ms: Optional[float] = None
    ):
        """Record a health check result"""
        # Record check
        self.health_check_total.labels(
            region=region,
            service=service,
            status=status
        ).inc()
        
        # Record duration
        self.health_check_duration.labels(
            region=region,
            service=service
        ).observe(duration)
        
        # Update availability
        availability = 1 if status == "healthy" else 0
        self.service_availability.labels(
            region=region,
            service=service
        ).set(availability)
        
        # Record response time if available
        if response_time_ms is not None:
            self.service_response_time.labels(
                region=region,
                service=service
            ).observe(response_time_ms)
    
    def update_region_status(self, region: str, status: str, health_percentage: float):
        """Update region status metrics"""
        # Map status to numeric value
        status_map = {
            "active": 1,
            "standby": 0,
            "failed": -1,
            "degraded": -0.5,
            "recovering": 0.5
        }
        
        numeric_status = status_map.get(status.lower(), 0)
        self.region_status.labels(region=region).set(numeric_status)
        self.region_health_percentage.labels(region=region).set(health_percentage)
    
    def update_replication_lag(
        self,
        source_region: str,
        target_region: str,
        data_type: str,
        lag_seconds: float
    ):
        """Update replication lag metrics"""
        self.replication_lag.labels(
            source_region=source_region,
            target_region=target_region,
            data_type=data_type
        ).set(lag_seconds)
    
    def update_data_consistency(
        self,
        source_region: str,
        target_region: str,
        consistency_percentage: float
    ):
        """Update data consistency metrics"""
        self.data_consistency.labels(
            source_region=source_region,
            target_region=target_region
        ).set(consistency_percentage)
    
    def get_failover_statistics(self) -> Dict[str, Any]:
        """Get failover statistics"""
        # In a real implementation, would query Prometheus
        return {
            "total_failovers": 42,
            "successful_failovers": 40,
            "failed_failovers": 2,
            "average_failover_time_seconds": 180.5,
            "mttr_minutes": 15.3,
            "availability_percentage": 99.95
        }