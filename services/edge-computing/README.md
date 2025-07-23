# Edge Computing Service

Distributed compute capabilities at edge locations for real-time processing of media assets.

## Overview

The Edge Computing service provides a distributed processing framework that enables compute tasks to be executed at edge locations closer to where data is generated or consumed. This reduces latency, bandwidth usage, and enables real-time processing of media assets.

## Features

### Distributed Processing
- **Multi-Node Cluster**: Support for multiple edge nodes working together
- **Task Distribution**: Intelligent task routing based on capabilities and load
- **Load Balancing**: Multiple strategies (round-robin, least-loaded, capability-based)
- **Automatic Failover**: Reassign tasks from failed nodes automatically

### Processing Capabilities
- **Video Transcoding**: Hardware-accelerated video encoding/decoding
- **Image Processing**: Resize, crop, format conversion, optimization
- **Thumbnail Generation**: Extract frames from videos
- **AI/ML Processing**: Face detection, object detection, scene analysis
- **Audio Processing**: Normalization, extraction, format conversion
- **Metadata Extraction**: Extract technical and descriptive metadata

### Edge Cache
- **Local Caching**: Store frequently accessed content at edge locations
- **Eviction Policies**: LRU, LFU, FIFO, TTL-based eviction
- **Cache Statistics**: Hit rate, size, most accessed items
- **P2P Transfer**: Share cached content between edge nodes

### Monitoring & Health
- **Node Health Monitoring**: CPU, memory, disk, GPU usage tracking
- **Task Metrics**: Processing time, success/failure rates
- **Alert System**: Automatic alerts for node failures, high load
- **Cluster Dashboard**: Real-time view of cluster status

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Master Node   │────▶│   Edge Node 1   │────▶│   Edge Node 2   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                        │
         ├── Coordination        ├── Processing          ├── Processing
         ├── Scheduling          ├── Local Cache         ├── Local Cache
         └── Monitoring          └── Health Report       └── Health Report
```

## API Endpoints

### Node Management
- `POST /api/v1/edge/nodes/register` - Register new edge node
- `GET /api/v1/edge/nodes` - List all nodes
- `GET /api/v1/edge/nodes/{node_id}` - Get node details
- `PATCH /api/v1/edge/nodes/{node_id}` - Update node
- `DELETE /api/v1/edge/nodes/{node_id}` - Remove node

### Task Management
- `POST /api/v1/edge/tasks` - Create processing task
- `GET /api/v1/edge/tasks` - List tasks
- `GET /api/v1/edge/tasks/{task_id}` - Get task details
- `PATCH /api/v1/edge/tasks/{task_id}` - Update task
- `POST /api/v1/edge/tasks/{task_id}/execute` - Execute task
- `GET /api/v1/edge/tasks/{task_id}/progress` - Get progress
- `POST /api/v1/edge/tasks/{task_id}/cancel` - Cancel task

### Cache Management
- `GET /api/v1/edge/cache/{cache_key}` - Get cached item
- `DELETE /api/v1/edge/cache/{cache_key}` - Delete cached item
- `GET /api/v1/edge/cache/stats` - Get cache statistics
- `POST /api/v1/edge/cache/clear` - Clear cache

### Cluster Management
- `GET /api/v1/edge/cluster/status` - Get cluster status
- `POST /api/v1/edge/cluster/distribution` - Create task distribution

### Monitoring
- `GET /api/v1/edge/alerts` - List alerts
- `PATCH /api/v1/edge/alerts/{alert_id}/resolve` - Resolve alert
- `GET /api/v1/edge/metrics/{node_id}` - Get node metrics

## Configuration

### Environment Variables

```env
# Node Configuration
NODE_ID=edge-node-001
NODE_LOCATION=us-west-2
NODE_TYPE=standard  # standard, gpu, specialized
NODE_CAPABILITIES=["transcode", "thumbnail", "analyze", "cache"]

# Cluster Configuration
MASTER_NODE_URL=http://edge-master:8018
IS_MASTER_NODE=false

# Processing Configuration
MAX_CONCURRENT_JOBS=10
JOB_TIMEOUT_SECONDS=3600
ENABLE_GPU_PROCESSING=false
GPU_DEVICE_ID=0

# Cache Configuration
ENABLE_LOCAL_CACHE=true
CACHE_SIZE_GB=100
CACHE_EVICTION_POLICY=lru  # lru, lfu, fifo, ttl
CACHE_PATH=/var/cache/edge

# Network Configuration
BANDWIDTH_LIMIT_MBPS=1000
ENABLE_P2P_TRANSFER=true
P2P_PORT_RANGE=30000-31000

# Media Processing
VIDEO_CODEC=h264
AUDIO_CODEC=aac
ENABLE_HARDWARE_ACCELERATION=true

# AI/ML Configuration
ENABLE_AI_PROCESSING=true
MODEL_CACHE_PATH=/var/cache/models
FACE_DETECTION_MODEL=mtcnn
OBJECT_DETECTION_MODEL=yolov5
```

## Task Types

### Video Transcoding
```python
{
    "task_type": "video_transcode",
    "parameters": {
        "output_format": "mp4",
        "video_codec": "h264",
        "audio_codec": "aac",
        "resolution": "1920x1080",
        "bitrate": "5000k",
        "fps": 30,
        "preset": "medium",
        "two_pass": false,
        "hardware_acceleration": true
    }
}
```

### Image Processing
```python
{
    "task_type": "image_resize",
    "parameters": {
        "operation": "resize",  # resize, crop, rotate, filter
        "width": 1920,
        "height": 1080,
        "quality": 85,
        "format": "jpeg",
        "maintain_aspect_ratio": true
    }
}
```

### AI Analysis
```python
{
    "task_type": "face_detection",
    "parameters": {
        "models": ["mtcnn"],
        "confidence_threshold": 0.5,
        "max_results": 10,
        "return_visualization": true
    }
}
```

## Deployment

### Single Node Setup

```bash
# Start edge node
docker-compose up -d

# Register with master (if not master)
curl -X POST http://master:8018/api/v1/edge/nodes/register \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "edge-node-002",
    "node_type": "standard",
    "location": "eu-west-1",
    "capabilities": ["transcode", "thumbnail", "cache"]
  }'
```

### Multi-Node Cluster

1. **Deploy Master Node**:
```yaml
# docker-compose.master.yml
services:
  edge-master:
    environment:
      - IS_MASTER_NODE=true
      - NODE_ID=edge-master
```

2. **Deploy Worker Nodes**:
```yaml
# docker-compose.worker.yml
services:
  edge-worker:
    environment:
      - IS_MASTER_NODE=false
      - MASTER_NODE_URL=http://edge-master:8018
      - NODE_ID=edge-worker-001
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: edge-computing
spec:
  selector:
    matchLabels:
      app: edge-computing
  template:
    metadata:
      labels:
        app: edge-computing
    spec:
      containers:
      - name: edge-node
        image: mams/edge-computing:latest
        env:
        - name: NODE_ID
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
        - name: NODE_LOCATION
          value: "$(NODE_REGION)"
        resources:
          requests:
            memory: "2Gi"
            cpu: "2"
          limits:
            memory: "4Gi"
            cpu: "4"
```

## Load Balancing Strategies

### Round Robin
Distribute tasks evenly across all available nodes.

### Least Loaded
Assign tasks to nodes with the lowest current load.

### Capability Based
Match tasks to nodes with specific capabilities (GPU, specialized codecs).

### Geographic
Prefer nodes in the same geographic location to minimize latency.

### Performance Based
Route tasks based on historical performance metrics.

## Cache Eviction Policies

### LRU (Least Recently Used)
Evict items that haven't been accessed recently.

### LFU (Least Frequently Used)
Evict items with the lowest access count.

### FIFO (First In First Out)
Evict oldest items first.

### TTL (Time To Live)
Evict items that have exceeded their TTL.

## Monitoring

### Prometheus Metrics

```
# Task metrics
edge_tasks_assigned_total
edge_tasks_completed_total
edge_tasks_failed_total
edge_task_processing_seconds

# Cache metrics
edge_cache_hits_total
edge_cache_misses_total
edge_cache_size_bytes
edge_cache_evictions_total

# Node metrics
edge_node_cpu_usage_percent
edge_node_memory_usage_percent
edge_node_disk_usage_percent
edge_node_gpu_usage_percent
```

### Grafana Dashboard

Pre-built dashboard available at `dashboards/edge-computing.json`:
- Node health overview
- Task processing statistics
- Cache performance
- Alert summary

## Development

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start service
python -m src.main
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test
pytest tests/test_edge_manager.py::test_task_distribution
```

## Security

### API Authentication
- API key required for node-to-node communication
- JWT tokens for user authentication
- TLS support for encrypted communication

### Network Security
- Firewall rules for P2P ports
- VPN support for cross-region communication
- IP whitelisting for trusted nodes

## Best Practices

1. **Node Placement**
   - Deploy nodes close to data sources
   - Consider network topology and bandwidth
   - Use GPU nodes for AI/ML tasks

2. **Task Scheduling**
   - Set appropriate task priorities
   - Use task metadata for better routing
   - Monitor task queue depth

3. **Cache Management**
   - Size cache based on working set
   - Monitor hit rates
   - Use appropriate eviction policy

4. **Monitoring**
   - Set up alerts for node failures
   - Monitor resource utilization
   - Track task processing times

## Troubleshooting

### Node Not Registering
- Check network connectivity to master
- Verify API key is correct
- Check firewall rules

### Tasks Not Processing
- Verify node has required capabilities
- Check resource availability
- Review task parameters

### Cache Miss Rate High
- Increase cache size
- Review access patterns
- Consider different eviction policy

### High Processing Times
- Enable hardware acceleration
- Check for resource contention
- Consider task parallelization