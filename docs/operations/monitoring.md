# Monitoring Guide

## Overview

This guide covers monitoring MAMS in production, including metrics collection, alerting, dashboards, and troubleshooting using monitoring data.

## Monitoring Stack

### Components
- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboards
- **AlertManager**: Alert routing and management
- **Jaeger**: Distributed tracing
- **ELK Stack**: Log aggregation and analysis

## Metrics Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     MAMS Services                           │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐      │
│  │Service A│  │Service B│  │Service C│  │Service D│      │
│  │/metrics │  │/metrics │  │/metrics │  │/metrics │      │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘      │
│       │            │            │            │             │
└───────┼────────────┼────────────┼────────────┼─────────────┘
        │            │            │            │
        └────────────┴────────────┴────────────┘
                             │
                    ┌────────▼────────┐
                    │   Prometheus    │
                    │  Time Series DB │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │     Grafana     │
                    │   Dashboards    │
                    └─────────────────┘
```

## Key Metrics

### System Metrics

#### API Gateway
```yaml
# Response time
http_request_duration_seconds{service="api-gateway"}

# Request rate
rate(http_requests_total{service="api-gateway"}[5m])

# Error rate
rate(http_requests_total{service="api-gateway",status=~"5.."}[5m])

# Active connections
api_gateway_active_connections

# Rate limit hits
rate(rate_limit_exceeded_total[5m])
```

#### Asset Management
```yaml
# Upload success rate
rate(asset_uploads_total{status="success"}[5m]) / rate(asset_uploads_total[5m])

# Average upload time
rate(asset_upload_duration_seconds_sum[5m]) / rate(asset_upload_duration_seconds_count[5m])

# Storage usage by tier
storage_usage_bytes{tier="hot|warm|cold|archive"}

# Asset count by type
assets_total{type="video|image|audio|document"}
```

#### Database Metrics
```yaml
# Connection pool usage
postgres_connections_active / postgres_connections_max

# Query performance
rate(postgres_query_duration_seconds_sum[5m]) / rate(postgres_query_duration_seconds_count[5m])

# Replication lag
postgres_replication_lag_seconds

# Cache hit ratio
redis_hits_total / (redis_hits_total + redis_misses_total)
```

### Business Metrics
```yaml
# Daily active users
count(count by (user_id) (api_requests_total{timerange="24h"}))

# Assets uploaded per day
increase(assets_total[24h])

# Search queries per minute
rate(search_queries_total[1m])

# Workflow completion rate
rate(workflow_completed_total[1h]) / rate(workflow_started_total[1h])
```

## Grafana Dashboards

### System Overview Dashboard
```json
{
  "dashboard": {
    "title": "MAMS System Overview",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [{
          "expr": "sum(rate(http_requests_total[5m])) by (service)"
        }]
      },
      {
        "title": "Error Rate",
        "targets": [{
          "expr": "sum(rate(http_requests_total{status=~\"5..\"}[5m])) by (service)"
        }]
      },
      {
        "title": "Response Time P95",
        "targets": [{
          "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) by (service)"
        }]
      },
      {
        "title": "CPU Usage",
        "targets": [{
          "expr": "100 * (1 - avg(rate(container_cpu_usage_seconds_total[5m])) by (pod))"
        }]
      }
    ]
  }
}
```

### Asset Management Dashboard
```json
{
  "dashboard": {
    "title": "Asset Management",
    "panels": [
      {
        "title": "Upload Rate",
        "targets": [{
          "expr": "rate(asset_uploads_total[5m])"
        }]
      },
      {
        "title": "Storage Distribution",
        "targets": [{
          "expr": "storage_usage_bytes by (tier)"
        }]
      },
      {
        "title": "Processing Queue",
        "targets": [{
          "expr": "proxy_generation_queue_size"
        }]
      },
      {
        "title": "Asset Types",
        "targets": [{
          "expr": "assets_total by (type)"
        }]
      }
    ]
  }
}
```

## Alerting Rules

### Critical Alerts

```yaml
# prometheus-alerts.yaml
groups:
  - name: critical
    rules:
      - alert: ServiceDown
        expr: up{job="mams"} == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.instance }} is down"
          description: "{{ $labels.instance }} has been down for more than 5 minutes"

      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate on {{ $labels.service }}"
          description: "Error rate is {{ $value }}% for {{ $labels.service }}"

      - alert: DatabaseConnectionExhausted
        expr: postgres_connections_active / postgres_connections_max > 0.9
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Database connection pool almost exhausted"
          description: "{{ $value }}% of connections are in use"
```

### Warning Alerts

```yaml
  - name: warnings
    rules:
      - alert: HighCPUUsage
        expr: rate(container_cpu_usage_seconds_total[5m]) > 0.8
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage on {{ $labels.pod }}"
          description: "CPU usage is {{ $value }}% for {{ $labels.pod }}"

      - alert: HighMemoryUsage
        expr: container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.8
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage on {{ $labels.pod }}"
          description: "Memory usage is {{ $value }}% for {{ $labels.pod }}"

      - alert: SlowQueries
        expr: rate(postgres_query_duration_seconds_sum[5m]) / rate(postgres_query_duration_seconds_count[5m]) > 1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Slow database queries detected"
          description: "Average query time is {{ $value }} seconds"
```

## Logging

### Log Format
```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "service": "asset-management",
  "trace_id": "abc123def456",
  "user_id": "user-789",
  "message": "Asset uploaded successfully",
  "metadata": {
    "asset_id": "asset-123",
    "size_bytes": 52428800,
    "duration_ms": 1234
  }
}
```

### Log Aggregation

#### Filebeat Configuration
```yaml
# filebeat.yml
filebeat.inputs:
  - type: container
    paths:
      - /var/lib/docker/containers/*/*.log
    processors:
      - add_kubernetes_metadata:
          host: ${NODE_NAME}
          matchers:
          - logs_path:
              logs_path: "/var/lib/docker/containers/"
      - decode_json_fields:
          fields: ["message"]
          target: "mams"
          overwrite_keys: true

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "mams-%{[agent.version]}-%{+yyyy.MM.dd}"
```

#### Logstash Pipeline
```ruby
# logstash.conf
input {
  beats {
    port => 5044
  }
}

filter {
  if [kubernetes][labels][app] == "mams" {
    json {
      source => "message"
    }
    
    date {
      match => ["timestamp", "ISO8601"]
    }
    
    mutate {
      add_field => {
        "[@metadata][index_prefix]" => "mams-%{service}"
      }
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "%{[@metadata][index_prefix]}-%{+YYYY.MM.dd}"
  }
}
```

### Log Queries

#### Kibana Queries
```
# Find all errors for a specific service
service:"asset-management" AND level:"ERROR"

# Track a specific user's actions
user_id:"user-123" AND timestamp:[now-1h TO now]

# Find slow operations
duration_ms:>5000

# Search by trace ID
trace_id:"abc123def456"
```

## Distributed Tracing

### Jaeger Configuration

```yaml
# jaeger-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: jaeger-config
data:
  sampling-strategies.json: |
    {
      "service_strategies": [
        {
          "service": "api-gateway",
          "type": "probabilistic",
          "param": 0.1
        },
        {
          "service": "asset-management",
          "type": "probabilistic",
          "param": 0.05
        }
      ],
      "default_strategy": {
        "type": "probabilistic",
        "param": 0.01
      }
    }
```

### Instrumenting Services

```python
# Python service example
from opentelemetry import trace
from opentelemetry.exporter.jaeger import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Configure Jaeger exporter
jaeger_exporter = JaegerExporter(
    agent_host_name="jaeger-agent",
    agent_port=6831,
)

# Set up tracing
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Add span processor
span_processor = BatchSpanProcessor(jaeger_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Use in code
@tracer.start_as_current_span("upload_asset")
async def upload_asset(file_data: bytes):
    span = trace.get_current_span()
    span.set_attribute("file.size", len(file_data))
    # ... rest of function
```

## Health Checks

### Service Health Endpoints

```python
# Health check implementation
@app.get("/health")
async def health_check():
    checks = {
        "database": await check_database(),
        "redis": await check_redis(),
        "storage": await check_storage(),
    }
    
    status = "healthy" if all(checks.values()) else "unhealthy"
    
    return {
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks,
        "version": app.version
    }

@app.get("/ready")
async def readiness_check():
    # Check if service is ready to accept traffic
    return {"ready": await is_service_ready()}
```

### Kubernetes Probes

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3
```

## SLI/SLO Monitoring

### Service Level Indicators

```yaml
# Availability SLI
- record: sli:availability
  expr: |
    sum(rate(http_requests_total{status!~"5.."}[5m])) /
    sum(rate(http_requests_total[5m]))

# Latency SLI (95th percentile under 500ms)
- record: sli:latency
  expr: |
    histogram_quantile(0.95, 
      rate(http_request_duration_seconds_bucket{le="0.5"}[5m])
    ) / 
    histogram_quantile(0.95, 
      rate(http_request_duration_seconds_bucket[5m])
    )

# Error rate SLI
- record: sli:error_rate
  expr: |
    1 - (
      sum(rate(http_requests_total{status=~"5.."}[5m])) /
      sum(rate(http_requests_total[5m]))
    )
```

### Service Level Objectives

```yaml
# 99.9% availability
- alert: SLOAvailabilityBreach
  expr: sli:availability < 0.999
  for: 5m
  labels:
    severity: warning
    slo: availability
  annotations:
    summary: "Availability SLO breach"
    description: "Availability is {{ $value }}%, below 99.9% SLO"

# 95% of requests under 500ms
- alert: SLOLatencyBreach
  expr: sli:latency < 0.95
  for: 5m
  labels:
    severity: warning
    slo: latency
  annotations:
    summary: "Latency SLO breach"
    description: "Only {{ $value }}% of requests are under 500ms"
```

## Custom Metrics

### Application Metrics

```python
from prometheus_client import Counter, Histogram, Gauge, Info

# Define metrics
asset_uploads = Counter(
    'asset_uploads_total',
    'Total number of asset uploads',
    ['status', 'type']
)

upload_duration = Histogram(
    'asset_upload_duration_seconds',
    'Time spent uploading assets',
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60]
)

active_workflows = Gauge(
    'active_workflows',
    'Number of active workflows',
    ['workflow_type']
)

service_info = Info(
    'service_info',
    'Service version information'
)

# Use in code
@upload_duration.time()
async def upload_asset(file_data: bytes, asset_type: str):
    try:
        # Upload logic
        asset_uploads.labels(status='success', type=asset_type).inc()
    except Exception as e:
        asset_uploads.labels(status='failure', type=asset_type).inc()
        raise
```

## Monitoring Best Practices

### 1. Metric Naming
- Use consistent naming: `service_subsystem_unit`
- Include units in metric names
- Use labels for dimensions

### 2. Dashboard Design
- One dashboard per service
- Overview dashboard for system health
- Use consistent color schemes
- Include relevant thresholds

### 3. Alert Design
- Alert on symptoms, not causes
- Include runbook links
- Use appropriate severity levels
- Avoid alert fatigue

### 4. Log Management
- Structured logging (JSON)
- Consistent field names
- Include trace IDs
- Appropriate log levels

## Troubleshooting with Metrics

### High Latency Investigation
```promql
# Find slowest endpoints
topk(10, rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])) by (endpoint)

# Check database query times
histogram_quantile(0.99, rate(postgres_query_duration_seconds_bucket[5m])) by (query_type)

# Identify bottlenecks in trace
# Use Jaeger UI to analyze slow traces
```

### Memory Leak Detection
```promql
# Memory growth over time
rate(container_memory_usage_bytes[1h])

# Memory usage by service
sort_desc(container_memory_usage_bytes) by (pod)

# Check for increasing object counts
rate(python_gc_objects_collected_total[1h])
```

### Error Spike Analysis
```promql
# Error rate by endpoint
sum(rate(http_requests_total{status=~"5.."}[5m])) by (endpoint, status)

# Error rate trend
rate(http_requests_total{status=~"5.."}[5m])

# Correlate with deployments
# Check deployment annotations in Grafana
```

## Capacity Planning

### Resource Usage Trends
```promql
# CPU usage prediction (linear regression)
predict_linear(container_cpu_usage_seconds_total[1d], 7*24*60*60)

# Storage growth rate
deriv(storage_usage_bytes[1d])

# Database connection usage trend
max_over_time(postgres_connections_active[1w]) / postgres_connections_max
```

---

For more information:
- [Performance Tuning](./performance.md)
- [Troubleshooting Guide](./troubleshooting.md)
- [Security Best Practices](./security.md)