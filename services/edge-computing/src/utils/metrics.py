"""
Metrics collection for edge computing service
"""

from prometheus_client import Counter, Histogram, Gauge, Summary


# Task metrics
tasks_assigned = Counter(
    'edge_tasks_assigned_total',
    'Total number of tasks assigned',
    ['node_id']
)

tasks_completed = Counter(
    'edge_tasks_completed_total',
    'Total number of tasks completed',
    ['node_id', 'task_type']
)

tasks_failed = Counter(
    'edge_tasks_failed_total',
    'Total number of tasks failed',
    ['node_id', 'task_type']
)

task_processing_time = Histogram(
    'edge_task_processing_seconds',
    'Task processing time in seconds',
    ['node_id', 'task_type'],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600]
)

# Cache metrics
cache_hits = Counter(
    'edge_cache_hits_total',
    'Total number of cache hits',
    ['node_id']
)

cache_misses = Counter(
    'edge_cache_misses_total',
    'Total number of cache misses',
    ['node_id']
)

cache_puts = Counter(
    'edge_cache_puts_total',
    'Total number of cache puts',
    ['node_id']
)

cache_evictions = Counter(
    'edge_cache_evictions_total',
    'Total number of cache evictions',
    ['node_id', 'reason']
)

cache_size_bytes = Gauge(
    'edge_cache_size_bytes',
    'Current cache size in bytes',
    ['node_id']
)

# Node metrics
node_cpu_usage = Gauge(
    'edge_node_cpu_usage_percent',
    'Node CPU usage percentage',
    ['node_id']
)

node_memory_usage = Gauge(
    'edge_node_memory_usage_percent',
    'Node memory usage percentage',
    ['node_id']
)

node_disk_usage = Gauge(
    'edge_node_disk_usage_percent',
    'Node disk usage percentage',
    ['node_id']
)

node_gpu_usage = Gauge(
    'edge_node_gpu_usage_percent',
    'Node GPU usage percentage',
    ['node_id']
)

active_tasks = Gauge(
    'edge_active_tasks',
    'Number of active tasks',
    ['node_id']
)

# Cluster metrics
cluster_nodes = Gauge(
    'edge_cluster_nodes',
    'Number of nodes in cluster',
    ['status']
)

cluster_capacity = Gauge(
    'edge_cluster_capacity',
    'Cluster resource capacity',
    ['resource']
)

# Alert metrics
alerts_created = Counter(
    'edge_alerts_created_total',
    'Total number of alerts created',
    ['type', 'severity']
)

# Network metrics
p2p_transfers = Counter(
    'edge_p2p_transfers_total',
    'Total P2P transfers between nodes',
    ['from_node', 'to_node']
)

p2p_bytes_transferred = Counter(
    'edge_p2p_bytes_transferred_total',
    'Total bytes transferred via P2P',
    ['from_node', 'to_node']
)

# Processing metrics
video_transcodes = Counter(
    'edge_video_transcodes_total',
    'Total video transcodes',
    ['node_id', 'preset']
)

image_processes = Counter(
    'edge_image_processes_total',
    'Total image processing operations',
    ['node_id', 'operation']
)

ai_analyses = Counter(
    'edge_ai_analyses_total',
    'Total AI analyses performed',
    ['node_id', 'model']
)

# Summary metrics
request_latency = Summary(
    'edge_request_latency_seconds',
    'Request latency in seconds',
    ['endpoint', 'method']
)

# Helper class to organize metrics
class EdgeMetrics:
    """Container for all edge computing metrics"""
    
    def __init__(self):
        # Task metrics
        self.tasks_assigned = tasks_assigned
        self.tasks_completed = tasks_completed
        self.tasks_failed = tasks_failed
        self.task_processing_time = task_processing_time
        
        # Cache metrics
        self.cache_hits = cache_hits
        self.cache_misses = cache_misses
        self.cache_puts = cache_puts
        self.cache_evictions = cache_evictions
        self.cache_size_bytes = cache_size_bytes
        
        # Node metrics
        self.node_cpu_usage = node_cpu_usage
        self.node_memory_usage = node_memory_usage
        self.node_disk_usage = node_disk_usage
        self.node_gpu_usage = node_gpu_usage
        self.active_tasks = active_tasks
        
        # Cluster metrics
        self.cluster_nodes = cluster_nodes
        self.cluster_capacity = cluster_capacity
        
        # Alert metrics
        self.alerts_created = alerts_created
        
        # Network metrics
        self.p2p_transfers = p2p_transfers
        self.p2p_bytes_transferred = p2p_bytes_transferred
        
        # Processing metrics
        self.video_transcodes = video_transcodes
        self.image_processes = image_processes
        self.ai_analyses = ai_analyses
        
        # Summary metrics
        self.request_latency = request_latency


# Global metrics instance
edge_metrics = EdgeMetrics()