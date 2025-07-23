# Edge Cache Service

The Edge Cache Service provides distributed caching at edge locations to improve content delivery performance and reduce latency for MAMS users worldwide.

## Features

- **Multi-tier Caching**: Memory, disk, and Redis-based storage backends
- **Intelligent Routing**: Automatic selection of nearest edge location
- **Content Optimization**: Compression, range requests, and conditional requests
- **Cache Strategies**: LRU, LFU, FIFO, TTL-based, and adaptive eviction
- **Origin Shield**: Protects origin servers from thundering herd
- **Real-time Invalidation**: Instant cache purging with pattern support
- **Monitoring**: Comprehensive metrics and health checks
- **Security**: Geo-blocking and authentication caching

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   End Users     │────▶│  Edge Cache     │────▶│  Origin Server  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │  Cache Storage  │
                        │  - Memory       │
                        │  - Disk         │
                        │  - Redis        │
                        └─────────────────┘
```

## Quick Start

### Development

```bash
# Start the service
docker-compose up -d

# View logs
docker-compose logs -f edge-cache

# Run tests
docker-compose run edge-cache pytest
```

### Configuration

Key environment variables:

```bash
# Cache Configuration
EDGE_CACHE_CACHE_STRATEGY=lru          # lru, lfu, fifo, ttl, adaptive
EDGE_CACHE_CACHE_SIZE_MB=1024         # Total cache size
EDGE_CACHE_STORAGE_BACKEND=hybrid      # memory, redis, disk, hybrid

# Edge Location
EDGE_CACHE_EDGE_LOCATION=us-east-1    # Edge location identifier
EDGE_CACHE_EDGE_REGION=us-east        # Edge region

# Origin Configuration
EDGE_CACHE_ORIGIN_URL=http://api-gateway:8000
EDGE_CACHE_ORIGIN_TIMEOUT=30
```

## API Endpoints

### Content Delivery

#### Cached Proxy
```http
GET /{path}
```
Main endpoint that serves cached content or fetches from origin.

**Headers:**
- `Cache-Control`: Standard cache control directives
- `If-None-Match`: ETag for conditional requests
- `If-Modified-Since`: Last modified date for conditional requests
- `Range`: Byte range for partial content

**Response Headers:**
- `X-Edge-Cache`: HIT, MISS, or VALIDATED
- `X-Edge-Location`: Serving edge location
- `X-Edge-Response-Time`: Total response time

### Cache Management

#### Get Cache Statistics
```http
GET /api/v1/cache/stats

Response:
{
  "hits": 1000,
  "misses": 200,
  "hit_rate": 0.833,
  "evictions": 50,
  "total_size": 104857600,
  "entry_count": 500,
  "location": "us-east-1",
  "region": "us-east"
}
```

#### Clear Cache
```http
DELETE /api/v1/cache?pattern=asset:*

Response:
{
  "cleared": 150,
  "pattern": "asset:*"
}
```

#### Invalidate Cache
```http
POST /api/v1/cache/invalidate
Content-Type: application/json

{
  "type": "asset",
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "cascade": true
}
```

#### List Cache Keys
```http
GET /api/v1/cache/keys?pattern=*&limit=100

Response:
{
  "pattern": "*",
  "total": 250,
  "keys": ["asset:123", "metadata:456", ...]
}
```

#### Prefetch Content
```http
POST /api/v1/cache/prefetch
Content-Type: application/json

{
  "urls": ["/assets/video1.mp4", "/assets/image1.jpg"],
  "priority": 7
}
```

### Edge Locations

#### Get Available Locations
```http
GET /api/v1/edge/locations

Response:
{
  "current_location": "us-east-1",
  "current_region": "us-east",
  "regions": {
    "us-east": ["us-east-1", "us-east-2"],
    "us-west": ["us-west-1", "us-west-2"],
    "eu-west": ["eu-west-1", "eu-west-2"],
    ...
  }
}
```

#### Get Nearest Edge
```http
GET /api/v1/edge/nearest/{user_location}

Response:
{
  "user_location": "us",
  "nearest_edge": "us-east-1"
}
```

## Cache Strategies

### LRU (Least Recently Used)
Evicts the least recently accessed items first. Best for general use cases.

### LFU (Least Frequently Used)
Evicts items with the lowest access frequency. Good for stable access patterns.

### FIFO (First In First Out)
Evicts oldest items first. Simple and predictable.

### TTL (Time To Live)
Items expire after a fixed time period. Good for time-sensitive content.

### Adaptive
Combines multiple factors (recency, frequency, size, priority) for intelligent eviction.

## Storage Backends

### Memory
- **Pros**: Fastest access, no I/O latency
- **Cons**: Limited size, volatile
- **Use case**: Hot content, small files

### Redis
- **Pros**: Distributed, persistent, fast
- **Cons**: Network latency, memory limited
- **Use case**: Shared cache across instances

### Disk
- **Pros**: Large capacity, persistent
- **Cons**: Slower than memory, I/O bottleneck
- **Use case**: Large files, cold content

### Hybrid (Memory + Disk)
- **Pros**: Best of both worlds
- **Cons**: Complex management
- **Use case**: Mixed workloads (recommended)

## Cache Key Patterns

Cache keys follow predictable patterns for easy management:

```
edge:{location}:asset:{asset_id}:{variant}
edge:{location}:metadata:{asset_id}
edge:{location}:search:{query_hash}
edge:{location}:thumb:{asset_id}:{size}
edge:{location}:proxy:{asset_id}:{quality}
```

## Content Priority

Content is cached with different priorities:

1. **Thumbnails** (Priority: 10) - Small, frequently accessed
2. **Metadata** (Priority: 9) - Critical for UI
3. **Low-quality proxies** (Priority: 8) - Preview content
4. **Search results** (Priority: 7) - Dynamic but cacheable
5. **Medium-quality proxies** (Priority: 6) - Standard viewing
6. **User data** (Priority: 5) - Personalized content
7. **Project data** (Priority: 4) - Collaborative content
8. **High-quality proxies** (Priority: 3) - Professional use
9. **Original assets** (Priority: 2) - Large files
10. **Analytics** (Priority: 1) - Low priority

## Performance Tuning

### Memory Optimization
```bash
# Increase memory cache for hot content
EDGE_CACHE_MEMORY_CACHE_SIZE_MB=512

# Reduce for disk-heavy workloads
EDGE_CACHE_MEMORY_CACHE_SIZE_MB=128
```

### Network Optimization
```bash
# Increase concurrent requests
EDGE_CACHE_MAX_CONCURRENT_REQUESTS=2000

# Adjust timeouts
EDGE_CACHE_ORIGIN_TIMEOUT=60
EDGE_CACHE_REQUEST_TIMEOUT=120
```

### Cache Optimization
```bash
# Longer TTL for stable content
EDGE_CACHE_CACHE_TTL_SECONDS=7200

# Larger objects for video
EDGE_CACHE_MAX_OBJECT_SIZE_MB=500

# More aggressive eviction
EDGE_CACHE_CACHE_STRATEGY=adaptive
```

## Monitoring

### Prometheus Metrics
Available at `/metrics`:

- `edge_cache_hits_total`: Total cache hits
- `edge_cache_misses_total`: Total cache misses
- `edge_cache_evictions_total`: Total evictions
- `edge_cache_size_bytes`: Current cache size
- `edge_cache_entries`: Number of cached entries
- `edge_cache_response_time_seconds`: Response time histogram

### Health Check
```http
GET /health

Response:
{
  "status": "healthy",
  "service": "edge-cache",
  "timestamp": "2024-01-20T10:30:00Z",
  "location": "us-east-1"
}
```

## Deployment

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: edge-cache
spec:
  replicas: 3
  selector:
    matchLabels:
      app: edge-cache
  template:
    metadata:
      labels:
        app: edge-cache
    spec:
      containers:
      - name: edge-cache
        image: mams/edge-cache:latest
        ports:
        - containerPort: 8000
        env:
        - name: EDGE_CACHE_EDGE_LOCATION
          valueFrom:
            fieldRef:
              fieldPath: metadata.annotations['topology.kubernetes.io/zone']
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
```

### Docker Swarm

```yaml
version: '3.8'
services:
  edge-cache:
    image: mams/edge-cache:latest
    deploy:
      replicas: 3
      placement:
        constraints:
          - node.labels.region == us-east
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
```

## Security

### Geo-blocking
```bash
# Enable geo-blocking
EDGE_CACHE_ENABLE_GEO_BLOCKING=true
EDGE_CACHE_ALLOWED_COUNTRIES=US,CA,GB,DE,FR
EDGE_CACHE_BLOCKED_COUNTRIES=XX,YY
```

### Authentication Caching
```bash
# Cache authentication results
EDGE_CACHE_ENABLE_AUTH_CACHING=true
EDGE_CACHE_AUTH_CACHE_TTL=300  # 5 minutes
```

## Troubleshooting

### High Cache Misses
1. Check cache size configuration
2. Verify TTL settings
3. Review eviction strategy
4. Check origin response headers

### Slow Performance
1. Monitor origin response times
2. Check network connectivity
3. Review cache hit rates
4. Optimize storage backend

### Cache Invalidation Issues
1. Verify invalidation patterns
2. Check Redis connectivity
3. Review cascade settings
4. Monitor invalidation delays

## Development

### Running Tests
```bash
# All tests
pytest

# Specific test file
pytest tests/test_cache_manager.py

# With coverage
pytest --cov=src --cov-report=html
```

### Code Style
```bash
# Format code
black src/ tests/

# Lint
ruff src/ tests/

# Type check
mypy src/
```

## License

Copyright (c) 2024 MAMS Project. All rights reserved.