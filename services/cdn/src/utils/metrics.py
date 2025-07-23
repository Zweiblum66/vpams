"""
Metrics collection utilities for CDN service
"""

from typing import Dict, Any, Optional
from datetime import datetime
import time
from contextlib import contextmanager
from prometheus_client import Counter, Histogram, Gauge, Summary
import structlog

logger = structlog.get_logger(__name__)


class MetricsCollector:
    """Collects and exposes metrics for CDN service"""
    
    def __init__(self):
        # Request metrics
        self.request_counter = Counter(
            'cdn_requests_total',
            'Total number of CDN requests',
            ['distribution_id', 'method', 'status', 'cache_status']
        )
        
        self.request_duration = Histogram(
            'cdn_request_duration_seconds',
            'CDN request duration in seconds',
            ['distribution_id', 'method']
        )
        
        # Cache metrics
        self.cache_hits = Counter(
            'cdn_cache_hits_total',
            'Total number of cache hits',
            ['distribution_id', 'content_type']
        )
        
        self.cache_misses = Counter(
            'cdn_cache_misses_total',
            'Total number of cache misses',
            ['distribution_id', 'content_type']
        )
        
        self.cache_evictions = Counter(
            'cdn_cache_evictions_total',
            'Total number of cache evictions',
            ['distribution_id', 'reason']
        )
        
        # Bandwidth metrics
        self.bandwidth_bytes = Counter(
            'cdn_bandwidth_bytes_total',
            'Total bandwidth consumed in bytes',
            ['distribution_id', 'direction', 'content_type']
        )
        
        # Distribution metrics
        self.distributions_total = Gauge(
            'cdn_distributions_total',
            'Total number of CDN distributions',
            ['provider', 'status']
        )
        
        # Purge metrics
        self.purge_requests = Counter(
            'cdn_purge_requests_total',
            'Total number of purge requests',
            ['distribution_id', 'type', 'status']
        )
        
        self.purge_duration = Histogram(
            'cdn_purge_duration_seconds',
            'Purge request duration in seconds',
            ['distribution_id', 'type']
        )
        
        # Error metrics
        self.errors_total = Counter(
            'cdn_errors_total',
            'Total number of CDN errors',
            ['distribution_id', 'error_type', 'status_code']
        )
        
        # Performance metrics
        self.origin_response_time = Summary(
            'cdn_origin_response_time_seconds',
            'Origin server response time in seconds',
            ['distribution_id', 'origin']
        )
        
        self.edge_response_time = Summary(
            'cdn_edge_response_time_seconds',
            'Edge server response time in seconds',
            ['distribution_id', 'edge_location']
        )
        
        # Cost metrics
        self.estimated_cost = Gauge(
            'cdn_estimated_cost_usd',
            'Estimated CDN cost in USD',
            ['distribution_id', 'cost_type']
        )
        
        # Custom metrics storage
        self._custom_metrics: Dict[str, Any] = {}
    
    def increment(self, metric: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric"""
        try:
            if metric == "cdn.requests":
                self.request_counter.labels(**labels).inc(value)
            elif metric == "cdn.cache.hits":
                self.cache_hits.labels(**labels).inc(value)
            elif metric == "cdn.cache.misses":
                self.cache_misses.labels(**labels).inc(value)
            elif metric == "cdn.cache.evictions":
                self.cache_evictions.labels(**labels).inc(value)
            elif metric == "cdn.bandwidth":
                self.bandwidth_bytes.labels(**labels).inc(value)
            elif metric == "cdn.errors":
                self.errors_total.labels(**labels).inc(value)
            elif metric.startswith("cdn.cache.purge.requests"):
                provider = metric.split(".")[-1] if len(metric.split(".")) > 4 else "unknown"
                self.purge_requests.labels(
                    distribution_id=labels.get("distribution_id", "unknown"),
                    type=labels.get("type", "manual"),
                    status=labels.get("status", "success")
                ).inc(value)
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
            if metric == "cdn.distributions.total":
                self.distributions_total.labels(**labels).set(value)
            elif metric == "cdn.estimated_cost":
                self.estimated_cost.labels(**labels).set(value)
            elif metric.startswith("cdn.distribution."):
                # Custom distribution metric
                if metric not in self._custom_metrics:
                    self._custom_metrics[metric] = Gauge(
                        metric.replace(".", "_"),
                        f"Custom metric: {metric}"
                    )
                self._custom_metrics[metric].set(value)
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
            if metric == "cdn.request.duration":
                self.request_duration.labels(**labels).observe(value)
            elif metric == "cdn.purge.duration":
                self.purge_duration.labels(**labels).observe(value)
            elif metric == "cdn.origin.response_time":
                self.origin_response_time.labels(**labels).observe(value)
            elif metric == "cdn.edge.response_time":
                self.edge_response_time.labels(**labels).observe(value)
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
    
    def record_cdn_request(
        self,
        distribution_id: str,
        method: str,
        status_code: int,
        cache_status: str,
        response_time: float,
        bytes_sent: int,
        content_type: str = "unknown"
    ):
        """Record a CDN request with all relevant metrics"""
        labels = {
            "distribution_id": distribution_id,
            "method": method,
            "status": str(status_code),
            "cache_status": cache_status,
            "content_type": content_type
        }
        
        # Increment request counter
        self.request_counter.labels(
            distribution_id=distribution_id,
            method=method,
            status=str(status_code),
            cache_status=cache_status
        ).inc()
        
        # Record response time
        self.request_duration.labels(
            distribution_id=distribution_id,
            method=method
        ).observe(response_time)
        
        # Update cache metrics
        if cache_status == "hit":
            self.cache_hits.labels(
                distribution_id=distribution_id,
                content_type=content_type
            ).inc()
        else:
            self.cache_misses.labels(
                distribution_id=distribution_id,
                content_type=content_type
            ).inc()
        
        # Update bandwidth
        self.bandwidth_bytes.labels(
            distribution_id=distribution_id,
            direction="out",
            content_type=content_type
        ).inc(bytes_sent)
        
        # Record errors
        if status_code >= 400:
            error_type = "client_error" if status_code < 500 else "server_error"
            self.errors_total.labels(
                distribution_id=distribution_id,
                error_type=error_type,
                status_code=str(status_code)
            ).inc()
    
    def get_cache_hit_rate(self, distribution_id: str) -> float:
        """Calculate cache hit rate for a distribution"""
        # In a real implementation, this would query the metrics store
        # For now, return a sample value
        return 0.85
    
    def get_bandwidth_usage(self, distribution_id: str, time_range: str = "1h") -> Dict[str, Any]:
        """Get bandwidth usage for a distribution"""
        # In a real implementation, this would query the metrics store
        # For now, return sample data
        return {
            "total_bytes": 1024 * 1024 * 1024 * 100,  # 100GB
            "peak_mbps": 1000,
            "average_mbps": 500,
            "by_content_type": {
                "video": 70,
                "image": 20,
                "other": 10
            }
        }
    
    def get_error_rate(self, distribution_id: str, time_range: str = "1h") -> float:
        """Calculate error rate for a distribution"""
        # In a real implementation, this would query the metrics store
        # For now, return a sample value
        return 0.001  # 0.1% error rate